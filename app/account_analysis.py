"""账号分析流水线：本地统计 → 逐条打标 → 分维度分析 → 交叉校验。

为什么这么设计（来自公开技能方法论）：
- 定量（条数、节奏、占比）由**代码**算，模型只负责打标和判断，避免模型数错；
- 定性（定位、人设、钩子）由模型抽样判断，但必须挂证据；
- 结论分三级：事实 / 推断 / 未知；平台拿不到的（粉丝数、播放量）一律写"不可得"。

只调用文本模型（DeepSeek，按 token 计费），不调用任何数据接口。
"""
from __future__ import annotations

import datetime as dt
import json
import re
from collections import Counter

from . import db, llm

BATCH = 60            # 每批打标多少条
TITLE_LIMIT = 45      # 标题截断长度，控制 token


def _signal(v: dict) -> float:
    """自定义信号分：转发 > 收藏 > 评论 > 点赞（视频号靠社交分发，转发权重最高）。"""
    return (int(v.get("shares") or 0) * 3
            + int(v.get("favorites") or 0) * 2
            + int(v.get("comments") or 0) * 1
            + int(v.get("likes") or 0) * 0.5)


def _clean(text: str) -> str:
    return re.sub(r"#\S+", "", text or "").split("\n")[0].strip()


def _parse_array(raw: str) -> list:
    """模型返回数组时，通用的 _extract_json 只认对象，这里单独解析。"""
    text = (raw or "").strip()
    if text.startswith("```"):
        text = re.sub(r"^```[a-zA-Z]*\s*|\s*```$", "", text).strip()
    try:
        data = json.loads(text)
        return data if isinstance(data, list) else (data.get("items") or [])
    except Exception:  # noqa: BLE001
        pass
    start, end = text.find("["), text.rfind("]")
    if start != -1 and end > start:
        try:
            data = json.loads(text[start:end + 1])
            return data if isinstance(data, list) else []
        except Exception:  # noqa: BLE001
            return []
    return []


def local_stats(videos: list[dict]) -> dict:
    """全部本地计算，不花钱。"""
    dates = []
    for v in videos:
        try:
            if v.get("published_at"):
                dates.append(dt.datetime.fromisoformat(v["published_at"]))
        except Exception:  # noqa: BLE001
            continue
    dates.sort()
    likes = sorted(int(v.get("likes") or 0) for v in videos)
    shares = sorted(int(v.get("shares") or 0) for v in videos)
    favs = sorted(int(v.get("favorites") or 0) for v in videos)

    def pct(arr, p):
        return arr[min(len(arr) - 1, int(len(arr) * p))] if arr else 0

    # 发布间隔（天）
    gaps = [(dates[i + 1] - dates[i]).days for i in range(len(dates) - 1)] if len(dates) > 1 else []
    months = Counter(d.strftime("%Y-%m") for d in dates)
    return {
        "count": len(videos),
        "from": dates[0].strftime("%Y-%m-%d") if dates else "",
        "to": dates[-1].strftime("%Y-%m-%d") if dates else "",
        "span_days": (dates[-1] - dates[0]).days if len(dates) > 1 else 0,
        "per_month": round(len(dates) / max(1, (dates[-1] - dates[0]).days / 30), 1) if len(dates) > 1 else 0,
        "median_gap_days": round(sorted(gaps)[len(gaps) // 2], 1) if gaps else 0,
        "busiest_month": months.most_common(1)[0] if months else ("", 0),
        "monthly": dict(sorted(months.items())),
        "likes": {"median": pct(likes, .5), "p80": pct(likes, .8), "p90": pct(likes, .9), "max": likes[-1] if likes else 0},
        "shares": {"median": pct(shares, .5), "p80": pct(shares, .8), "p90": pct(shares, .9), "max": shares[-1] if shares else 0},
        "favorites": {"median": pct(favs, .5), "p90": pct(favs, .9), "max": favs[-1] if favs else 0},
        "pinned": sum(1 for v in videos if v.get("pinned")),
        "not_available": ["粉丝数", "播放量", "完播率", "涨粉数"],
    }


def _sample(videos: list[dict], n: int = 30) -> list[dict]:
    """抽样精读用的作品：信号最高 + 最低 + 中间，三档都要有。"""
    ordered = sorted(videos, key=_signal)
    if len(ordered) <= n:
        return ordered
    low = ordered[: n // 3]
    high = ordered[-n // 3:]
    mid_start = len(ordered) // 2 - (n - len(low) - len(high)) // 2
    mid = ordered[mid_start: mid_start + (n - len(low) - len(high))]
    seen, out = set(), []
    for v in high + mid + low:
        if v.get("id") not in seen:
            seen.add(v.get("id"))
            out.append(v)
    return out


def build_taxonomy(videos: list[dict], sample_n: int = 80) -> list[dict]:
    """先从这账号自己的标题里归纳出分类表（不是我们预设的）。

    取信号最高 40 条 + 最近 25 条 + 随机 15 条，覆盖面更均衡。
    """
    cfg = llm.config()
    if not cfg["api_key"]:
        raise llm.LLMUnavailable("还没有配置云端模型 API Key")
    by_signal = sorted(videos, key=_signal, reverse=True)[:40]
    by_time = sorted(videos, key=lambda v: v.get("published_at") or "", reverse=True)[:25]
    picked, seen = [], set()
    for v in by_signal + by_time + videos[:: max(1, len(videos) // 15)][:15]:
        if v.get("id") not in seen:
            seen.add(v.get("id"))
            picked.append(v)
    picked = picked[:sample_n]

    titles = "\n".join(f'- {(v.get("text") or "").replace(chr(10), " ")[:35]}' for v in picked)
    prompt = (
        "下面是一个短视频账号的作品标题。请归纳出 8-12 个「选题类目」，"
        "覆盖绝大多数作品，类目之间不要重叠。\n"
        "只输出 JSON 数组，格式："
        '[{"name":"类目名（4-8字）","desc":"一句话说明这类讲什么"}]\n\n'
        + titles
    )
    raw = llm._chat(cfg, [{"role": "user", "content": prompt}], 1500, as_json=True)
    arr = _parse_array(raw)
    out = []
    for item in arr:
        name = str(item.get("name") or "").strip()
        if name and all(name != x["name"] for x in out):
            out.append({"name": name, "desc": str(item.get("desc") or "").strip()})
    return out[:12]


def tag_videos(videos: list[dict], taxonomy: list[dict]) -> dict[str, dict]:
    """按固定分类表批量打标。模型只能选表里的类目，保证统计可加总。"""
    cfg = llm.config()
    if not cfg["api_key"]:
        raise llm.LLMUnavailable("还没有配置云端模型 API Key")
    names = [t["name"] for t in taxonomy]
    legend = "\n".join(f'- {t["name"]}：{t["desc"]}' for t in taxonomy)
    result: dict[str, dict] = {}
    for start in range(0, len(videos), BATCH):
        chunk = videos[start:start + BATCH]
        lines = [f'{i}|{(v.get("text") or "").replace(chr(10), " ")[:TITLE_LIMIT]}'
                 for i, v in enumerate(chunk)]
        prompt = (
            "给下面每条视频从给定类目里选一个，并判断形式和钩子。\n"
            "只输出 JSON 数组，不要解释。格式："
            '[{"i":序号,"topic":"类目名","form":"形式","hook":"钩子"}]\n\n'
            f"类目（必须原样使用其中一个）：\n{legend}\n"
            "form 从 口播/剧情/图文/干货教程/案例复盘/答疑/直播切片 中选一个；\n"
            "hook 从 疑问/否定/对比/数字/悬念/身份共鸣/直接结论 中选一个。\n\n"
            + "\n".join(lines)
        )
        raw = llm._chat(cfg, [{"role": "user", "content": prompt}], 3000, as_json=True)
        arr = _parse_array(raw)
        if not arr:
            raw = llm._chat(cfg, [
                {"role": "user", "content": prompt},
                {"role": "assistant", "content": (raw or "")[:1500]},
                {"role": "user", "content": "上面不是合法 JSON 数组。请只输出 JSON 数组本身。"},
            ], 3000, as_json=True)
            arr = _parse_array(raw)
        for item in arr:
            try:
                idx = int(item.get("i"))
            except Exception:  # noqa: BLE001
                continue
            if not (0 <= idx < len(chunk)):
                continue
            topic = str(item.get("topic") or "").strip()
            if topic not in names:
                # 模型没按表来：找最接近的，找不到归「其他」
                topic = next((n for n in names if n and n in topic), "其他")
            result[str(chunk[idx].get("id"))] = {
                "topic": topic,
                "form": str(item.get("form") or "").strip(),
                "hook": str(item.get("hook") or "").strip(),
            }
    return result


def aggregate(videos: list[dict], tags: dict[str, dict]) -> dict:
    """按标签统计——这一步是代码算的，不会数错。"""
    topic_counter = Counter()
    form_counter = Counter()
    hook_counter = Counter()
    topic_signal: dict[str, list[float]] = {}
    for v in videos:
        t = tags.get(str(v.get("id")))
        if not t:
            continue
        if t["topic"]:
            topic_counter[t["topic"]] += 1
            topic_signal.setdefault(t["topic"], []).append(_signal(v))
        if t["form"]:
            form_counter[t["form"]] += 1
        if t["hook"]:
            hook_counter[t["hook"]] += 1
    total = sum(topic_counter.values()) or 1
    topics = []
    for name, cnt in topic_counter.most_common(12):
        sig = topic_signal.get(name) or [0]
        topics.append({
            "topic": name,
            "count": cnt,
            "share": f"{round(cnt * 100 / total)}%",
            "median_signal": round(sorted(sig)[len(sig) // 2]),
        })
    return {
        "topics": topics,
        "forms": [{"name": k, "count": c} for k, c in form_counter.most_common(8)],
        "hooks": [{"name": k, "count": c} for k, c in hook_counter.most_common(8)],
        "tagged": sum(1 for v in videos if str(v.get("id")) in tags),
        "total": len(videos),
    }


ANALYZE_PROMPT = """你是资深短视频账号分析师。基于给出的**真实数据**分析这个视频号账号。

只输出一个 JSON 对象：
{
  "business_type": "账号类型（个人IP/知识教育/流量媒体/品牌官方/电商带货/获客服务/矩阵孵化 之一，可加副类型）",
  "positioning": "一句话定位：为谁 + 解决什么问题 + 靠什么内容机制",
  "audience": "目标受众（从选题和评论区看不出来就写：数据不足）",
  "style": "表达风格（人称、语气、形式），只能从样本标题判断",
  "pillars": [{"name": "内容支柱", "share": "占比", "note": "这类内容的作用"}],
  "cadence_note": "更新节奏的解读（数字由系统算好，不要改）",
  "spread": "传播特征：靠什么被转发（引用信号分数据）",
  "top_patterns": ["高信号作品的共性，2-4 条，每条要能指回具体作品"],
  "replicable": ["可复制的做法，3-5 条"],
  "not_replicable": ["不宜照搬的部分，1-3 条"],
  "risks": ["对标时的注意点，1-3 条"],
  "unknowns": ["当前数据判断不了的，1-3 条"]
}

硬性规则：
1. 只能用给到的数据；不要编造播放量、粉丝数、收入、涨粉率。
2. 分级表达：数据直接支持的写确定语气；推测的必须用「可能/倾向于」；没数据的写进 unknowns。
3. 数字一律引用给到的统计值，不要自己重算。
4. 只输出 JSON。"""


def analyze(account: dict) -> dict:
    videos = account.get("videos") or []
    if not videos:
        raise llm.LLMUnavailable("这个账号还没有作品，先抓一次")

    stats = local_stats(videos)
    taxonomy = build_taxonomy(videos)
    tags = tag_videos(videos, taxonomy) if taxonomy else {}
    agg = aggregate(videos, tags)
    agg["taxonomy"] = taxonomy

    # 抽样：高信号 / 中位 / 低信号各取一部分，避免只看爆款
    samples = _sample(videos, 30)
    sample_lines = []
    for v in samples:
        sample_lines.append(
            f'{(v.get("published_at") or "")[:10]} 信号{round(_signal(v))} '
            f'{"[置顶]" if v.get("pinned") else ""}{(v.get("text") or "").replace(chr(10), " ")[:60]}'
        )

    context = (
        f"账号：{account.get('name')}（{((account.get('metrics') or {}).get('verify') or '无认证')}）\n"
        f"简介：{account.get('bio') or '（无）'}\n"
        f"地区：{((account.get('metrics') or {}).get('region') or '未知')}\n"
        f"作品总数：{((account.get('metrics') or {}).get('posts') or stats['count'])}\n"
        f"本次分析样本：{stats['count']} 条（{stats['from']} ~ {stats['to']}）\n\n"
        f"【本地统计，数字以此为准】\n{json.dumps(stats, ensure_ascii=False)}\n\n"
        f"【选题分布，代码统计】\n{json.dumps(agg['topics'], ensure_ascii=False)}\n\n"
        f"【内容形式】\n{json.dumps(agg['forms'], ensure_ascii=False)}\n\n"
        f"【钩子类型】\n{json.dumps(agg['hooks'], ensure_ascii=False)}\n\n"
        f"【抽样作品（高信号/中位/低信号混合，共 {len(samples)} 条）】\n" + "\n".join(sample_lines)
    )

    cfg = llm.config()
    raw = llm._chat(cfg, [{"role": "system", "content": ANALYZE_PROMPT},
                          {"role": "user", "content": context}], 3000, as_json=True)
    data = llm._extract_json(raw)

    data.update({
        "stats": stats,
        "topics": agg["topics"],
        "forms": agg["forms"],
        "hooks": agg["hooks"],
        "evidence": {
            "analyzed": stats["count"],
            "total_posts": ((account.get("metrics") or {}).get("posts") or 0),
            "tagged": agg["tagged"],
            "sample_read": len(samples),
            "from": stats["from"],
            "to": stats["to"],
            "method": "本地统计 + 分批打标 + 抽样精读",
        },
        "video_count": stats["count"],
        "engine": f"云端模型 {cfg['model']}",
        "generated_at": db.now_iso(),
    })
    return data
