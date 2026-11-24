"""云端拆解模型：通过 OpenAI 兼容接口调用（默认 DeepSeek）。

两步调用：
1. 结构分析（JSON）：钩子、结构分段、情绪、金句、转化、标题。
2. 完整口播稿（纯文本，按 ### 角色 分段）：按视频实际时长控制字数。

API 地址、模型名、Key 都在工作台设置页填写，只保存在本机 data\\app.db。
拆解时把字幕文本发到该服务商，不发送视频文件。
"""
from __future__ import annotations

import json
import pathlib
import re
import threading
import urllib.error
import urllib.request

from . import db

DEFAULT_BASE = "https://api.deepseek.com"
DEFAULT_MODEL = "deepseek-flash"
MAX_TRANSCRIPT_CHARS = 12000
SCRIPT_CHARS_PER_MINUTE = 250

SKILLS_DIR = pathlib.Path(__file__).resolve().parent / "skills"

_lock = threading.Lock()


def _skill_rule(name: str) -> str:
    """读取技能文件里「## 模型规则」之后的内容，拼进 prompt。

    技能文件是可独立修改的方法论文档，改文件即改行为。
    """
    path = SKILLS_DIR / name
    if not path.exists():
        return ""
    try:
        text = path.read_text(encoding="utf-8")
    except OSError:
        return ""
    marker = "## 模型规则"
    idx = text.find(marker)
    if idx < 0:
        return ""
    return text[idx + len(marker):].strip()


def _to_sec(ts: str) -> int | None:
    """'分:秒' → 秒；解析失败返回 None。"""
    if not ts or ":" not in ts:
        return None
    try:
        m, s = ts.strip().split(":", 1)
        return int(m) * 60 + int(float(s))
    except Exception:
        return None


def _structure_spec(duration: float) -> dict:
    """按时长分档，返回段数区间和结构骨架。"""
    m = duration / 60 if duration else 0
    if m <= 0.5:
        return {"min": 3, "max": 4, "label": "≤30 秒", "skeleton": "钩子 / 主体 / 收束"}
    if m <= 1:
        return {"min": 3, "max": 4, "label": "31–60 秒", "skeleton": "钩子 / 主体 / 转折或案例 / 收束"}
    if m <= 3:
        return {"min": 4, "max": 6, "label": "1–3 分钟", "skeleton": "完整叙事弧：钩子→背景→论点→案例→收束"}
    if m <= 10:
        return {"min": 6, "max": 8, "label": "3–10 分钟", "skeleton": "多论点递进"}
    return {"min": 8, "max": 10, "label": ">10 分钟", "skeleton": "多论点递进，可合并同类"}


def _validate_structure(structure: list[dict], duration: float) -> list[str]:
    """校验结构分段；返回问题列表，空列表 = 通过。"""
    problems: list[str] = []
    spec = _structure_spec(duration)
    n = len(structure)
    if n < spec["min"] or n > spec["max"]:
        problems.append(f"段数 {n} 不在 {spec['min']}-{spec['max']} 区间")
    if not structure:
        return problems
    if structure[0].get("start") != "0:00":
        problems.append(f"第一段 start 是 {structure[0].get('start')}，应为 0:00")
    total = _fmt_seconds(duration)
    if structure[-1].get("end") != total:
        problems.append(f"最后一段 end 是 {structure[-1].get('end')}，应为 {total}")
    prev_end: int | None = None
    for i, s in enumerate(structure):
        st = _to_sec(s.get("start", ""))
        en = _to_sec(s.get("end", ""))
        if st is None or en is None:
            problems.append(f"第 {i + 1} 段时间格式异常：{s.get('start')}-{s.get('end')}")
            continue
        if prev_end is not None and st != prev_end:
            problems.append(f"分段不连续：第 {i} 段结束于 {prev_end} 秒，第 {i + 1} 段从 {st} 秒开始")
        prev_end = en
        if not s.get("role"):
            problems.append(f"第 {i + 1} 段缺 role")
        if not s.get("purpose"):
            problems.append(f"第 {i + 1} 段缺 purpose")
        if not s.get("retention"):
            problems.append(f"第 {i + 1} 段缺 retention")
    return problems


def _structure_rule_text(duration: float) -> str:
    spec = _structure_spec(duration)
    skill = _skill_rule("video-decompose.md")
    head = (
        f"本视频时长约 {_fmt_seconds(duration)}，属于「{spec['label']}」档。\n"
        f"结构分段段数必须在 {spec['min']}-{spec['max']} 段；结构骨架参考：{spec['skeleton']}。"
    )
    return head + ("\n\n" + skill if skill else "")


class LLMUnavailable(RuntimeError):
    """云端模型不可用（没配 Key、网络不通、余额不足等）。"""


def config() -> dict:
    return {
        "base_url": str(db.get_setting("llm_base_url", DEFAULT_BASE) or DEFAULT_BASE).rstrip("/"),
        "model": str(db.get_setting("llm_model_name", DEFAULT_MODEL) or DEFAULT_MODEL).strip(),
        "api_key": str(db.get_setting("llm_api_key", "") or "").strip(),
    }


def _http(url: str, key: str, payload: dict | None = None, timeout: int = 240) -> dict:
    headers = {"Content-Type": "application/json", "Authorization": f"Bearer {key}"}
    data = json.dumps(payload, ensure_ascii=False).encode("utf-8") if payload is not None else None
    req = urllib.request.Request(url, data=data, headers=headers,
                                 method="POST" if data else "GET")
    try:
        with urllib.request.urlopen(req, timeout=timeout) as resp:
            return json.loads(resp.read().decode("utf-8"))
    except urllib.error.HTTPError as exc:
        body = ""
        try:
            body = exc.read().decode("utf-8", "ignore")
        except Exception:
            pass
        if exc.code == 401:
            raise LLMUnavailable("API Key 无效或已过期") from exc
        if exc.code == 402:
            raise LLMUnavailable("API 账户余额不足，请先充值") from exc
        if exc.code == 429:
            raise LLMUnavailable("请求太快或额度用完了，请稍后再试") from exc
        raise LLMUnavailable(f"接口返回 {exc.code}：{body[:200]}") from exc
    except (urllib.error.URLError, TimeoutError) as exc:
        raise LLMUnavailable("连不上云端模型接口，请检查网络或 API 地址") from exc


def status(check: bool = True) -> dict:
    cfg = config()
    result = {
        "base_url": cfg["base_url"], "model": cfg["model"],
        "key_set": bool(cfg["api_key"]), "configured": bool(cfg["api_key"]),
        "available": False, "error": "", "models": [],
    }
    if not result["key_set"] or not check:
        return result
    try:
        data = _http(cfg["base_url"] + "/models", cfg["api_key"], timeout=8)
        names = [m.get("id", "") for m in data.get("data", [])]
        result["models"] = names
        result["available"] = True
        if names and cfg["model"] not in names:
            result["error"] = f"模型 {cfg['model']} 不在账户可用列表里"
    except LLMUnavailable as exc:
        result["error"] = str(exc)
    return result


ANALYSIS_PROMPT = """你是经验丰富的短视频/中长视频内容分析师，帮 IP 运营者拆解对标视频。
只输出一个 JSON 对象，不要输出解释，不要用 Markdown 代码块。

JSON 结构（所有字段必填）：
{
  "summary": "两句话总结这条内容的核心机制和目标观众",
  "tags": ["3-5 个标签"],
  "structure": [
    {
      "start": "0:00", "end": "0:40",
      "role": "钩子/承诺/背景/主体-论点/主体-案例/转折/收束/CTA 之一",
      "gist": "这一段讲了什么（20字内）",
      "purpose": "这一段承担什么功能",
      "retention": "靠什么留住观众",
      "risk": "这一段最大的流失风险",
      "emotion": 1到5的整数（情绪强度）
    }
  ],
  "hook": {"text": "开头 3 秒的原话", "mechanism": "钩子用了什么心理机制", "score": 0 到 100 的整数, "why": "一句话解释为什么有效"},
  "topic": {"text": "这条内容讲什么", "angle": "切入角度", "audience": "目标观众"},
  "emotion": {"primary": "主要情绪", "curve": ["情绪阶段一", "阶段二", "阶段三"], "notes": "情绪曲线怎么走"},
  "quotes": [{"text": "金句原话", "type": "金句"}],
  "conversion": {"goal": "转化目标", "device": "用了什么设计", "cta": "行动引导原话"},
  "title_options": ["可拍摄标题一", "标题二", "标题三"]
}

硬性要求：
1. 只基于字幕原文分析，不要编造字幕里没有的事实；金句必须是原话。
2. structure 的段数、起止时间见下方的「结构分段规则」，必须覆盖全片、首尾相接、时间格式用 "分:秒"。
3. 不要编造镜头数、剪辑细节；没有视频画面信息时，不要判断分镜。
4. hook.score、structure.emotion 只给整数。
5. 只输出 JSON。"""

SCRIPT_PROMPT = """你是短视频/中长视频口播稿写手。根据给到的原文和结构分段，写一份**完整、可直接拍摄**的口播稿。

输出格式（严格遵守）：
### 角色名
该段完整口播内容

### 角色名
……

要求：
1. 按给定 structure 的角色顺序输出，每段以 "### 角色名" 单独一行开头。
2. 必须覆盖原文的所有观点、案例和细节，不能只写提纲、不能省略、不能写“等等”。
3. 口播化：短句、口语、有停顿感；保留原文的金句和关键数字。
4. 目标总字数约 {expected} 字（允许 ±20%）。
5. 不要输出任何解释、标题、Markdown 代码块或额外说明。"""


def _extract_json(text: str) -> dict:
    text = text.strip()
    if text.startswith("```"):
        text = text.strip("`")
        if text.startswith("json"):
            text = text[4:]
    start = text.find("{")
    end = text.rfind("}")
    if start < 0 or end <= start:
        raise ValueError("模型没有返回 JSON")
    return json.loads(text[start:end + 1])


def _text(value, default: str = "") -> str:
    if value is None:
        return default
    return str(value).strip() or default


def _int(value, default: int = 0, low: int = 0, high: int = 100) -> int:
    try:
        num = int(float(value))
    except Exception:
        return default
    return max(low, min(high, num))


def _list(value) -> list:
    return value if isinstance(value, list) else []


def _dict(value) -> dict:
    return value if isinstance(value, dict) else {}


def _fmt_seconds(total: float) -> str:
    total = int(max(0, total))
    return f"{total // 60}:{total % 60:02d}"


def _user_context(title: str, transcript_body: str, duration: float,
                  author: str, platform: str, expected: int) -> str:
    return (
        f"标题：{title or '未命名'}\n"
        f"作者：{author or '未知'}（平台：{platform or '视频号'}）\n"
        f"时长：约 {_fmt_seconds(duration)}\n"
        f"完整口播稿目标字数：约 {expected} 字\n"
        f"字幕（带时间）：\n{transcript_body}"
    )


def _chat(cfg: dict, messages: list, max_tokens: int, as_json: bool) -> str:
    payload = {
        "model": cfg["model"], "messages": messages, "temperature": 0.2,
        "max_tokens": max_tokens,
        # DeepSeek 默认开启深度思考，会把额度耗在 reasoning 上；这里关闭
        "thinking": {"type": "disabled"},
    }
    if as_json:
        payload["response_format"] = {"type": "json_object"}
    url = cfg["base_url"] + "/chat/completions"
    try:
        reply = _http(url, cfg["api_key"], payload)
    except LLMUnavailable as exc:
        if "接口返回 400" in str(exc):
            payload.pop("thinking", None)
            if as_json and "response_format" in str(exc):
                payload.pop("response_format", None)
            reply = _http(url, cfg["api_key"], payload)
        else:
            raise
    return (reply.get("choices") or [{}])[0].get("message", {}).get("content", "")


def _normalize_analysis(raw: dict, title: str, transcript: str, duration: float) -> dict:
    hook = _dict(raw.get("hook"))
    topic = _dict(raw.get("topic"))
    emotion = _dict(raw.get("emotion"))
    conversion = _dict(raw.get("conversion"))

    structure = []
    for item in _list(raw.get("structure"))[:8]:
        item = _dict(item)
        start = _text(item.get("start"))
        end = _text(item.get("end"))
        if ":" not in start:
            continue
        structure.append({
            "start": start, "end": end or start,
            "role": _text(item.get("role"), "主体"),
            "gist": _text(item.get("gist")),
            "purpose": _text(item.get("purpose")),
            "retention": _text(item.get("retention")),
            "risk": _text(item.get("risk")),
            "emotion": _int(item.get("emotion"), 3, 1, 5),
        })
    if not structure:
        structure = [{
            "start": "0:00", "end": _fmt_seconds(duration or 60), "role": "整条",
            "gist": title, "purpose": "", "retention": "", "risk": "", "emotion": 3,
        }]

    retention = [{
        "at": f"{x['start']}–{x['end']}",
        "move": x["role"] + ("：" + x["gist"] if x["gist"] else ""),
        "why": x["retention"] or x["risk"],
    } for x in structure]

    quotes = []
    for item in _list(raw.get("quotes"))[:4]:
        item = _dict(item) if isinstance(item, dict) else {"text": item}
        text = _text(item.get("text"))
        if text:
            quotes.append({"text": text, "type": _text(item.get("type"), "金句")})

    tags = [str(t).strip() for t in _list(raw.get("tags")) if str(t).strip()][:5]
    titles = [str(t).strip() for t in _list(raw.get("title_options")) if str(t).strip()][:3]
    curve = [str(c).strip() for c in _list(emotion.get("curve")) if str(c).strip()][:4]

    return {
        "summary": _text(raw.get("summary")),
        "tags": tags,
        "duration": round(float(duration or 0), 1),
        "structure": structure,
        "retention": retention,
        "hook": {
            "text": _text(hook.get("text"), transcript[:40]),
            "mechanism": _text(hook.get("mechanism")),
            "score": _int(hook.get("score"), 80),
            "why": _text(hook.get("why")),
        },
        "topic": {
            "text": _text(topic.get("text"), title),
            "angle": _text(topic.get("angle")),
            "audience": _text(topic.get("audience")),
        },
        "emotion": {
            "primary": _text(emotion.get("primary")),
            "curve": curve,
            "notes": _text(emotion.get("notes")),
        },
        "quotes": quotes,
        "pacing": {"shots": 0, "avg_shot": "", "rhythm": "", "notes": ""},
        "conversion": {
            "goal": _text(conversion.get("goal")),
            "device": _text(conversion.get("device")),
            "cta": _text(conversion.get("cta")),
        },
        "title_options": titles or [title],
        "storyboard": [],
    }


def _parse_script(text: str) -> list[dict]:
    sections = []
    current_role = ""
    buf: list[str] = []
    for line in text.splitlines():
        m = re.match(r"^#{1,3}\s*(.+?)\s*$", line.strip())
        if m:
            if buf and current_role:
                sections.append({"role": current_role, "text": "\n".join(buf).strip()})
            current_role = m.group(1)
            buf = []
        elif line.strip():
            buf.append(line.strip())
    if buf and current_role:
        sections.append({"role": current_role, "text": "\n".join(buf).strip()})
    if not sections:
        paragraphs = [p.strip() for p in text.split("\n\n") if p.strip()]
        if paragraphs:
            sections = [{"role": "全文", "text": "\n\n".join(paragraphs)}]
    return [s for s in sections if s["text"]]


ROLE_SET = {"钩子", "承诺", "背景", "主体", "主体-论点", "主体-案例", "转折", "收束", "CTA", "整条", "全文"}


def _fix_roles(sections: list[dict], structure: list[dict]) -> list[dict]:
    """模型偶尔会把作者名当成分段标题，按结构顺序纠正。"""
    if not sections or not structure:
        return sections
    roles = [s.get("role", "") for s in sections]
    if all(r in ROLE_SET for r in roles) and len(set(roles)) > 1:
        return sections
    fixed = []
    for i, section in enumerate(sections):
        role = structure[i]["role"] if i < len(structure) else structure[-1]["role"]
        fixed.append({**section, "role": role})
    return fixed


CLEAN_PROMPT = """你是严谨的转写校对员。下面是语音转写（按时间段）和视频画面字幕的 OCR 结果。
任务：以语音转写为底稿，用画面字幕校正错别字、专有名词、人名、数字和标点。
约束：不要改写句子，不要增删内容，不要合并或拆分段落。
输出格式：每段一行，严格保持 "[分:秒–分:秒] 文本" 的格式，段数和顺序与输入一致。
只输出这些行，不要任何解释。"""


def clean_transcript(paragraphs: list[dict], ocr_lines: list[dict], title: str = "") -> list[dict] | None:
    """用画面字幕做参考，校对转写；不可靠时返回 None。"""
    if not paragraphs or not ocr_lines:
        return None
    cfg = config()
    if not cfg["api_key"]:
        return None
    asr_text = "\n".join(
        f"[{_fmt_seconds(p['start'])}–{_fmt_seconds(p['end'])}] {p['text']}" for p in paragraphs
    )
    ocr_text = "\n".join(
        f"[{_fmt_seconds(o['start'])}] {o['text']}" for o in ocr_lines[:400]
    )
    messages = [
        {"role": "system", "content": CLEAN_PROMPT},
        {"role": "user", "content": f"标题：{title}\n\n语音转写：\n{asr_text}\n\n画面字幕 OCR：\n{ocr_text}"},
    ]
    try:
        content = _chat(cfg, messages, 4000, as_json=False)
    except LLMUnavailable:
        return None

    pattern = re.compile(r"^\[(\d+:\d+)\s*[–\-]\s*(\d+:\d+)\]\s*(.+)$")
    cleaned = []
    for line in content.splitlines():
        match = pattern.match(line.strip())
        if not match:
            continue
        cleaned.append({
            "start": paragraphs[len(cleaned)]["start"],
            "end": paragraphs[len(cleaned)]["end"],
            "text": match.group(3).strip(),
        })
        if len(cleaned) == len(paragraphs):
            break
    if len(cleaned) != len(paragraphs):
        return None
    original_chars = sum(len(p["text"]) for p in paragraphs)
    new_chars = sum(len(p["text"]) for p in cleaned)
    if not (0.7 <= new_chars / max(1, original_chars) <= 1.3):
        return None
    return cleaned


PROOFREAD_PROMPT = """你是严谨的中文转写校对员。输入是按时间段分段的语音转写。
任务：只修正明显的识别错误——同音字/错别字、人名地名专有名词、数字、标点断句。
约束：不要改写句子，不要调整顺序，不要增删内容，不要合并或拆分段落。
输出格式：
先逐行输出校正后的段落，严格保持 "[分:秒–分:秒] 文本" 格式，段数和顺序不变；
然后输出一行 "### 修改清单"，每行写 "- 原词 → 新词：原因"；没有修改就写 "- 无"。
不要输出任何其他解释。"""


def proofread(paragraphs: list[dict], title: str = "") -> dict | None:
    """只改错别字的校对；不可靠时返回 None。"""
    if not paragraphs:
        return None
    cfg = config()
    if not cfg["api_key"]:
        return None
    source = "\n".join(
        f"[{_fmt_seconds(p['start'])}–{_fmt_seconds(p['end'])}] {p['text']}" for p in paragraphs
    )
    messages = [
        {"role": "system", "content": PROOFREAD_PROMPT},
        {"role": "user", "content": f"标题：{title}\n\n转写：\n{source}"},
    ]
    try:
        content = _chat(cfg, messages, 4000, as_json=False)
    except LLMUnavailable:
        return None

    pattern = re.compile(r"^\[(\d+:\d+)\s*[–\-]\s*(\d+:\d+)\]\s*(.+)$")
    corrected: list[dict] = []
    changes: list[str] = []
    in_changes = False
    for line in content.splitlines():
        line = line.strip()
        if not line:
            continue
        if line.startswith("###") and "修改" in line:
            in_changes = True
            continue
        if in_changes:
            if line.startswith("-"):
                item = line.lstrip("- ").strip()
                if item and item != "无":
                    changes.append(item)
            continue
        match = pattern.match(line)
        if match:
            corrected.append({
                "start": paragraphs[len(corrected)]["start"],
                "end": paragraphs[len(corrected)]["end"],
                "text": match.group(3).strip(),
            })
            if len(corrected) == len(paragraphs):
                break
    if len(corrected) != len(paragraphs):
        return None
    original_chars = sum(len(p["text"]) for p in paragraphs)
    new_chars = sum(len(p["text"]) for p in corrected)
    if not (0.9 <= new_chars / max(1, original_chars) <= 1.1):
        return None
    return {"paragraphs": corrected, "changes": changes[:50]}


PUNCT_FALLBACK = (
    "你是中文语音转写标点还原员。给一段没有标点的转写文本补全标点并断句。\n"
    "只加标点、断句，一个字都不改、不增、不删、不换顺序；用中文标点，按语义断句。"
    "直接输出加好标点后的完整文本，不要解释。"
)


def _split_sentences(text: str) -> list[str]:
    """按中文句末标点切分，保留标点。"""
    parts = re.split(r"(?<=[。！？；])", text)
    return [p.strip() for p in parts if p.strip()]


def restore_punctuation(paragraphs: list[dict], title: str = "",
                        duration: float = 0) -> dict | None:
    """给无标点的转写补标点、重新断句。原始段落不动，返回「标点整理版」。

    返回 {"text": 加标点后的完整全文, "sentences": [{start,end,text}]}；
    时间戳按字数比例重新分配（是估算，原始时间戳仍在原始段落里）。
    不可靠时返回 None，调用方继续用原始文本。
    """
    if not paragraphs:
        return None
    cfg = config()
    if not cfg["api_key"]:
        return None
    raw_text = "".join(p.get("text", "") for p in paragraphs)
    if not raw_text.strip():
        return None
    rule = _skill_rule("punctuation-restore.md") or PUNCT_FALLBACK
    messages = [
        {"role": "system", "content": rule},
        {"role": "user", "content": f"标题：{title or '未命名'}\n\n转写（无标点）：\n{raw_text}"},
    ]
    try:
        content = _chat(cfg, messages, 4000, as_json=False)
    except LLMUnavailable:
        return None
    punctuated = (content or "").strip()
    if not punctuated:
        return None
    # 校验：去掉标点和空白后字数应基本一致——证明只加了标点，没改字
    _strip = re.compile(r"[^一-鿿A-Za-z0-9]")
    raw_chars = len(_strip.sub("", raw_text))
    new_chars = len(_strip.sub("", punctuated))
    if raw_chars and not (0.92 <= new_chars / raw_chars <= 1.08):
        return None
    sentences = _split_sentences(punctuated)
    if not sentences:
        return None
    total = float(duration or paragraphs[-1].get("end", 0) or len(raw_text))
    total_chars = sum(len(s) for s in sentences) or 1
    cursor = 0.0
    out: list[dict] = []
    for s in sentences:
        span = total * len(s) / total_chars
        out.append({"start": round(cursor, 2), "end": round(cursor + span, 2), "text": s})
        cursor += span
    return {"text": punctuated, "sentences": out}


def _script_messages(context: str, structure: list[dict], expected: int) -> list[dict]:
    outline = "\n".join(
        f"{s['start']}–{s['end']} {s['role']}：{s['gist']}" for s in structure
    )
    return [
        {"role": "system", "content": SCRIPT_PROMPT.format(expected=expected)},
        {"role": "user", "content": context + "\n\n结构分段：\n" + outline},
    ]


def _transcript_body(transcript: str, paragraphs: list | None) -> str:
    body = transcript.strip()
    if paragraphs:
        body = "\n".join(
            f"[{_fmt_seconds(p.get('start', 0))}–{_fmt_seconds(p.get('end', 0))}] {p.get('text', '')}"
            for p in paragraphs
        )
    if len(body) > MAX_TRANSCRIPT_CHARS:
        body = body[:MAX_TRANSCRIPT_CHARS] + "\n（字幕过长，已截断）"
    return body


def decompose(title: str, transcript: str, duration: float = 0,
              author: str = "", platform: str = "视频号",
              paragraphs: list | None = None) -> dict:
    """只做结构分析（拆解），不生成任何改写内容；失败时抛 LLMUnavailable。

    按时长分档约束结构段数，并对结果做强制校验（段数/起止/连续性/字段完整），
    校验不过会把问题反馈给模型重试，仍不过则标进 structure_issues。
    """
    cfg = config()
    if not cfg["api_key"]:
        raise LLMUnavailable("还没有配置云端模型 API Key，请到「设置」里填写")

    body = _transcript_body(transcript, paragraphs)
    expected = int(duration / 60 * SCRIPT_CHARS_PER_MINUTE) if duration else 0
    context = _user_context(title, body, duration, author, platform, expected)
    system = ANALYSIS_PROMPT + "\n\n" + _structure_rule_text(duration)

    with _lock:
        messages = [
            {"role": "system", "content": system},
            {"role": "user", "content": context},
        ]
        last_error = ""
        data = None
        problems: list[str] = []
        for _attempt in range(3):
            content = _chat(cfg, messages, 3000, as_json=True)
            try:
                raw = _extract_json(content)
            except Exception as exc:  # noqa: BLE001
                last_error = str(exc)
                messages += [
                    {"role": "assistant", "content": content[:2000]},
                    {"role": "user", "content": "上面的输出不是合法 JSON。请只重新输出一个合法的 JSON 对象，不要任何解释。"},
                ]
                continue
            data = _normalize_analysis(raw, title, transcript, duration)
            problems = _validate_structure(data["structure"], duration)
            if not problems:
                break
            messages += [
                {"role": "assistant", "content": content[:2000]},
                {"role": "user", "content":
                 "结构分段校验没通过，请重新输出完整 JSON 并修正这些问题："
                 + "；".join(problems[:6])},
            ]
        if data is None:
            raise LLMUnavailable(f"模型输出无法解析：{last_error}")
        if problems:
            data["structure_issues"] = problems

        data.update({
            "author": author,
            "platform": platform,
            "transcript": transcript,
            "engine": f"云端模型 {cfg['model']}",
            "generated_at": db.now_iso(),
        })
        return data


IMAGE_NOTE_PROMPT = """你是图文笔记（小红书一类）的内容分析师。用户会给你一条笔记的标题、正文，以及按顺序提取的每张图片上的文字。

只输出一个 JSON 对象，结构如下：
{
  "title_analysis": {"hook": "标题在抓什么", "formula": "标题公式，如 年龄+反常识结论", "keywords": ["3-6 个关键词"]},
  "image_plan": [{"index": 1, "summary": "这一张的要点分析，一两句说清它在干什么"}],
  "conversion": {"comment_hook": "评论区引导的具体写法", "dm_hook": "私信或收藏引导", "cta": "整体行动号召"},
  "risks": ["对标时的注意点"]
}

硬性要求：
1. image_plan 必须覆盖每一张图，index 与输入完全一致，不要漏、不要合并。
2. 每张图只写「要点分析」，不要复述图上原文（原文由系统单独展示）。
3. 图片画面你看不到，只能依据图上文字推断；不要描述配色、构图、人物长相。
4. 不编造点赞、收藏、播放数据。
5. 只输出 JSON，不要解释。"""


_TAG_RE = re.compile(r"#([^#\s]{1,30}?)(?:\[话题\])?#")


def note_tags(desc: str) -> list[str]:
    """从正文里抠出 #话题# 标签（小红书风格），保序去重。"""
    tags: list[str] = []
    for m in _TAG_RE.finditer(desc or ""):
        tag = m.group(1).strip()
        if tag and tag not in tags:
            tags.append(tag)
    return tags


def decompose_image_note(title: str, desc: str, images: list,
                         author: str = "", platform: str = "小红书") -> dict:
    """图文笔记拆解：输入标题、正文和每张图的 OCR 文字。"""
    cfg = config()
    if not cfg["api_key"]:
        raise LLMUnavailable("还没有配置云端模型 API Key，请到「设置」里填写")

    blocks = []
    for item in images or []:
        text = (item.get("text") or "").strip()
        if not text:
            continue
        blocks.append(f"【第 {item.get('index')} 张】\n{text[:400]}")
    images_text = "\n\n".join(blocks)[:6000] or "（没有识别到图片文字）"

    rule = _skill_rule("image-note-decompose.md")
    system = IMAGE_NOTE_PROMPT + (("\n\n" + rule) if rule else "")
    user = (
        f"平台：{platform}\n作者：{author or '未知'}\n"
        f"标题：{title}\n\n正文：\n{desc or '（无正文）'}\n\n"
        f"图片文字（共 {len(images or [])} 张）：\n{images_text}"
    )

    with _lock:
        messages = [
            {"role": "system", "content": system},
            {"role": "user", "content": user},
        ]
        data = None
        last_error = ""
        for _attempt in range(2):
            content = _chat(cfg, messages, 2600, as_json=True)
            try:
                data = _extract_json(content)
                break
            except Exception as exc:  # noqa: BLE001
                last_error = str(exc)
                messages += [
                    {"role": "assistant", "content": content[:1500]},
                    {"role": "user", "content": "上面的输出不是合法 JSON。请只重新输出一个合法的 JSON 对象。"},
                ]
        if data is None:
            raise LLMUnavailable(f"模型输出无法解析：{last_error}")

        data.update({
            "kind": "image_note",
            "title": title,
            "desc": desc,
            "tags": note_tags(desc),
            "author": author,
            "platform": platform,
            "images": [
                {"index": i.get("index"), "file": i.get("file"),
                 "text": i.get("text") or "", "error": i.get("error") or ""}
                for i in (images or [])
            ],
            "engine": f"云端模型 {cfg['model']}",
            "generated_at": db.now_iso(),
        })
        return data


ACCOUNT_PROMPT = """你是短视频账号运营分析师。根据一个视频号账号的简介和已抓到的作品列表，分析这个账号的可对标之处。

只输出一个 JSON 对象，结构如下：
{
  "positioning": "账号定位（一句话，说清为谁解决什么问题）",
  "audience": "目标受众",
  "tags": ["3-6 个内容标签"],
  "style": "表达风格（人称、语气、画面形式、剪辑特征，只能从标题推断，不确定就写不确定）",
  "topics": [{"topic": "选题方向", "count": 数量, "share": "占比，如 30%"}],
  "cadence": {"frequency": "每周大约几条", "best_time": "从发布时间看的高频时段", "notes": "更新节奏观察"},
  "top_posts": [{"title": "作品标题", "why": "为什么这条在账号内表现好"}],
  "replicable": ["可复制的 3-5 条做法"],
  "risks": ["对标时的注意点或风险"]
}

硬性要求：
1. 播放量平台不公开，不要编造；只能比较账号内点赞/转发/评论/收藏的相对高低。
2. top_posts 给互动（点赞+转发+评论+收藏之和）排名靠前的 3-5 条，标题用原文。
3. 所有判断必须能落回给到的标题、时间或互动数据；信息不足就明说。
4. 只输出 JSON，不要解释。"""


def analyze_account(account: dict) -> dict:
    """账号级分析：只吃昵称、简介、作品标题和互动数；返回结构化 JSON。"""
    cfg = config()
    if not cfg["api_key"]:
        raise LLMUnavailable("还没有配置云端模型 API Key，请到「设置」里填写")
    videos = account.get("videos") or []
    if not videos:
        raise LLMUnavailable("这个账号还没有抓到作品，先刷新一次")
    lines = []
    for video in videos:
        date = (video.get("published_at") or "")[:10]
        engagement = (int(video.get("likes") or 0) + int(video.get("comments") or 0)
                      + int(video.get("shares") or 0) + int(video.get("favorites") or 0))
        lines.append(f"{date} | 互动{engagement}（赞{int(video.get('likes') or 0)}/"
                     f"评{int(video.get('comments') or 0)}/转{int(video.get('shares') or 0)}/"
                     f"藏{int(video.get('favorites') or 0)}）| {(video.get('text') or '').strip()}")
    metrics = account.get("metrics") or {}
    context = (
        f"账号昵称：{account.get('name') or ''}\n"
        f"简介：{account.get('bio') or '（没有简介）'}\n"
        f"账号数据字段：{json.dumps(metrics, ensure_ascii=False)[:300]}\n"
        f"作品数：{len(videos)} 条\n"
        f"作品列表（按时间从新到旧）：\n" + "\n".join(lines)
    )
    with _lock:
        messages = [
            {"role": "system", "content": ACCOUNT_PROMPT},
            {"role": "user", "content": context},
        ]
        last_error = ""
        raw = {}
        for _ in range(2):
            content = _chat(cfg, messages, 3000, as_json=True)
            try:
                raw = _extract_json(content)
                break
            except Exception as exc:  # noqa: BLE001
                last_error = str(exc)
                messages += [
                    {"role": "assistant", "content": content[:2000]},
                    {"role": "user", "content": "上面的输出不是合法 JSON。请只重新输出一个合法的 JSON 对象。"},
                ]
        else:
            raise LLMUnavailable(f"模型输出无法解析：{last_error}")

    return {
        "positioning": _text(raw.get("positioning")),
        "audience": _text(raw.get("audience")),
        "tags": [str(t) for t in _list(raw.get("tags"))][:8],
        "style": _text(raw.get("style")),
        "topics": _list(raw.get("topics"))[:10],
        "cadence": _dict(raw.get("cadence")),
        "top_posts": _list(raw.get("top_posts"))[:6],
        "replicable": [str(t) for t in _list(raw.get("replicable"))][:8],
        "risks": [str(t) for t in _list(raw.get("risks"))][:6],
        "video_count": len(videos),
        "generated_at": db.now_iso(),
        "engine": f"云端模型 {cfg['model']}",
    }


def rewrite(title: str, transcript: str, duration: float = 0,
            author: str = "", platform: str = "视频号",
            structure: list | None = None,
            paragraphs: list | None = None) -> dict:
    """基于拆解出的结构，另写一份可拍摄的口播稿（改写稿）。

    只读拆解结果，不回写拆解数据：调用方把结果存到 decompositions.data["rewrite"]。
    """
    cfg = config()
    if not cfg["api_key"]:
        raise LLMUnavailable("还没有配置云端模型 API Key，请到「设置」里填写")
    structure = structure or []
    if not structure:
        raise LLMUnavailable("这条拆解还没有结构分段，无法据此改写")

    body = _transcript_body(transcript, paragraphs)
    expected = int(duration / 60 * SCRIPT_CHARS_PER_MINUTE) if duration else 0
    context = _user_context(title, body, duration, author, platform, expected)
    messages = _script_messages(context, structure, expected)

    with _lock:
        text = _chat(cfg, messages, 5000, as_json=False)
        sections = _fix_roles(_parse_script(text), structure)
        full_text = "\n\n".join(s["text"] for s in sections)
        if expected and len(full_text) < expected * 0.6:
            messages += [
                {"role": "assistant", "content": text[:3000]},
                {"role": "user", "content":
                 f"口播稿不完整（{len(full_text)} 字，目标约 {expected} 字），"
                 "请补全所有观点和案例后重新输出完整口播稿，格式不变。"},
            ]
            text = _chat(cfg, messages, 5000, as_json=False)
            sections = _fix_roles(_parse_script(text), structure)
            full_text = "\n\n".join(s["text"] for s in sections)

    return {
        "sections": sections,
        "full_text": full_text,
        "chars": len(full_text),
        "expected_chars": expected,
        "engine": f"云端模型 {cfg['model']}",
        "generated_at": db.now_iso(),
    }
