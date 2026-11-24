"""HTTP API：工作总台、拆解、存档、设置。"""
from __future__ import annotations

import json
import threading
import time
from datetime import datetime, timedelta
from pathlib import Path

from fastapi import APIRouter, File, Form, HTTPException, UploadFile

from . import account_analysis, account_fetch, asr, config, dataxapi, db, link_parser, llm, note_ocr, ocr, tikhub
from . import channels_sync, login_scan, scheduler
from .demo import build_demo

router = APIRouter(prefix="/api")


# ---------- helpers ----------

def _jloads(text: str, default):
    try:
        return json.loads(text)
    except Exception:
        return default


def _summary(row) -> dict:
    data = _jloads(row["data"], {})
    options = {}
    if "options" in row.keys():
        options = _jloads(row["options"], {})
    stats = {}
    if "s_meta" in row.keys():
        stats = (_jloads(row["s_meta"], {}).get("link") or {}).get("stats") or {}
    return {
        "id": row["id"],
        "source_id": row["source_id"],
        "title": row["title"],
        "status": row["status"],
        "is_demo": bool(row["is_demo"]),
        "created_at": row["created_at"],
        "updated_at": row["updated_at"],
        "author": data.get("author", ""),
        "platform": data.get("platform", ""),
        "tags": data.get("tags", []),
        "hook_score": (data.get("hook") or {}).get("score"),
        "summary": data.get("summary", ""),
        "options": options,
        "stats": stats,
        "has_rewrite": bool(data.get("rewrite") or data.get("script")),
    }


def _detail(row) -> dict:
    item = _summary(row)
    item["data"] = _jloads(row["data"], {})
    with db.db() as conn:
        versions = conn.execute(
            "SELECT version, note, created_at FROM versions WHERE decomposition_id=? ORDER BY version DESC",
            (row["id"],),
        ).fetchall()
    item["versions"] = [dict(v) for v in versions]
    source = db.get_source(row["source_id"]) if row["source_id"] else None
    if source:
        meta = _jloads(source["meta"], {})
        asr_meta = meta.get("asr") or {}
        item["source"] = {
            "id": source["id"],
            "status": source["status"],
            "file_name": source["file_name"],
            "duration": source["duration"],
            "transcript": source["transcript"],
            "transcript_raw": asr_meta.get("raw_transcript") or "",
            "ocr": {
                "lines": (asr_meta.get("ocr") or {}).get("lines", 0),
                "clean": bool(asr_meta.get("clean_paragraphs")),
                "model": (asr_meta.get("ocr") or {}).get("model", ""),
                "error": (asr_meta.get("ocr") or {}).get("error", ""),
            },
            "segments": asr_meta.get("segments") or [],
            "paragraphs": (asr_meta.get("clean_paragraphs")
                           or asr_meta.get("proofread_paragraphs")
                           or asr_meta.get("paragraphs") or []),
            "proofread": bool(asr_meta.get("proofread_paragraphs")),
            "proofread_changes": asr_meta.get("proofread_changes") or [],
            "punctuated_text": asr_meta.get("punctuated_text") or "",
            "punctuated_sentences": asr_meta.get("punctuated_sentences") or [],
            "shots": asr_meta.get("shots") or [],
            "video": asr_meta.get("video") or {},
            "has_file": bool(source["file_path"]),
            "is_demo": bool(source["is_demo"]),
            "error": meta.get("error", ""),
            "asr": {
                "model": asr_meta.get("model", ""),
                "device": asr_meta.get("device", ""),
                "language": asr_meta.get("language", ""),
                "elapsed": asr_meta.get("elapsed"),
            },
            "progress": asr.progress(source["id"]),
        }
    return item


def _wait_transcript(source: dict | None, timeout_sec: int = 900) -> dict | None:
    """等转写完成；没有文件或已经结束就立即返回。"""
    if not source:
        return None
    deadline = time.time() + timeout_sec
    while source and source["status"] == "transcribing":
        if time.time() > deadline:
            return source
        time.sleep(2)
        source = db.get_source(source["id"])
    return source


def _fmt_seconds(total: float) -> str:
    total = int(max(0, total))
    return f"{total // 60}:{total % 60:02d}"


def _join_tokens(tokens: list[str]) -> str:
    text = ""
    for token in tokens:
        if not text:
            text = token
        elif (token[:1].isascii() and token[:1].isalnum()
              and text[-1:].isascii() and (text[-1:].isalnum() or text[-1:] in ".,!?")):
            text += " " + token
        else:
            text += token
    return text


def _build_storyboard(shots: list, segments: list) -> list:
    """把口播按时间归属到镜头。有词级时间戳用词；没有就用段，一段只归一个镜头，避免重复。"""
    words = []
    for seg in segments:
        for word in seg.get("words") or []:
            text = (word.get("word") or "").strip()
            if text:
                words.append((
                    float(word.get("start", 0)),
                    float(word.get("end", 0)),
                    text,
                ))

    buckets: list[list[str]] = [[] for _ in shots]
    if words:
        words.sort(key=lambda x: x[0])
        shot_index = 0
        for w_start, w_end, text in words:
            mid = (w_start + w_end) / 2
            while shot_index < len(shots) and mid > shots[shot_index].get("end", 0):
                shot_index += 1
            if shot_index >= len(shots):
                break
            if mid >= shots[shot_index].get("start", 0):
                buckets[shot_index].append(text)
    else:
        # 段级时间戳：每段按中点归到一个镜头，绝不重复出现
        for seg in segments:
            text = (seg.get("text") or "").strip()
            if not text:
                continue
            mid = (float(seg.get("start", 0)) + float(seg.get("end", 0))) / 2
            target = 0
            for i, shot in enumerate(shots):
                if float(shot.get("start", 0)) <= mid <= float(shot.get("end", 0)):
                    target = i
                    break
                if mid > float(shot.get("end", 0)):
                    target = i
            buckets[target].append(text)

    rows = []
    LONG_SHOT = 15.0
    for i, shot in enumerate(shots):
        start, end = float(shot.get("start", 0)), float(shot.get("end", 0))
        number = shot.get("index", i + 1)
        if end - start <= LONG_SHOT:
            rows.append({
                "time": f"{_fmt_seconds(start)}–{_fmt_seconds(end)}",
                "shot": f"镜头 {number}",
                "duration": shot.get("duration", 0),
                "line": _join_tokens(buckets[i])[:300],
                "note": "",
                "keyframe": shot.get("keyframe", ""),
            })
            continue

        # 一镜到底的画面（固定机位）不切假镜头，按口播段落把它拆成几行，注明是同一镜头
        segs = [
            (float(s.get("start", 0)), float(s.get("end", 0)), (s.get("text") or "").strip())
            for s in segments
            if (s.get("text") or "").strip()
            and float(s.get("end", 0)) >= start and float(s.get("start", 0)) <= end
        ]
        groups: list[tuple[float, float, str]] = []
        buf: list[str] = []
        group_start = 0.0
        for s_start, s_end, text in segs:
            if not buf:
                group_start = s_start
            buf.append(text)
            if s_end - group_start >= 9 or len("".join(buf)) >= 90:
                groups.append((group_start, s_end, "".join(buf)))
                buf = []
        if buf:
            groups.append((group_start, segs[-1][1] if segs else end, "".join(buf)))
        if not groups:
            groups = [(start, end, _join_tokens(buckets[i]))]

        total = len(groups)
        for gi, (g_start, g_end, text) in enumerate(groups, 1):
            rows.append({
                "time": f"{_fmt_seconds(g_start)}–{_fmt_seconds(g_end)}",
                "shot": f"镜头 {number} · {gi}/{total}",
                "duration": round(g_end - g_start, 2),
                "line": text[:300],
                "note": "同一镜头连续画面",
                "keyframe": shot.get("keyframe", ""),
            })
    return rows


def _finish_decomposition(decomp_id: str, data: dict, is_demo: bool, note: str) -> None:
    with db.db() as conn:
        conn.execute(
            "UPDATE decompositions SET status='done', data=?, is_demo=?, updated_at=? WHERE id=?",
            (json.dumps(data, ensure_ascii=False), 1 if is_demo else 0,
             db.now_iso(), decomp_id),
        )
        vrow = conn.execute(
            "SELECT COALESCE(MAX(version), 0) AS v FROM versions WHERE decomposition_id=?",
            (decomp_id,),
        ).fetchone()
        version = int(vrow["v"]) + 1
        conn.execute(
            "INSERT INTO versions(id, decomposition_id, version, data, note, created_at) "
            "VALUES(?, ?, ?, ?, ?, ?)",
            (db.new_id("ver"), decomp_id, version,
             json.dumps(data, ensure_ascii=False), note, db.now_iso()),
        )
        conn.execute(
            "INSERT INTO events(type, payload, created_at) VALUES(?, ?, ?)",
            ("decomposition.done",
             json.dumps({"id": decomp_id, "version": version, "demo": is_demo},
                        ensure_ascii=False), db.now_iso()),
        )


def _fail_decomposition(decomp_id: str, message: str) -> None:
    with db.db() as conn:
        conn.execute(
            "UPDATE decompositions SET status='failed', data=?, updated_at=? WHERE id=?",
            (json.dumps({"error": message}, ensure_ascii=False), db.now_iso(), decomp_id),
        )
    db.log_event("decomposition.failed", {"id": decomp_id, "error": message})


def _new_decomposition(title: str, author: str, platform: str, url: str,
                       account: str = "", storyboard: bool = True,
                       video_id: str = "") -> str:
    """按链接直接建一条拆解（账号作品用），返回拆解 id。"""
    source_id = db.new_id("src")
    decomp_id = db.new_id("dec")
    created = db.now_iso()
    options = {"storyboard": storyboard}
    if account:
        options["account"] = account
    if video_id:
        options["video_id"] = video_id
    # 没有链接时先标成 preparing（正在取链接），由后台线程取到后再开始跑
    status = "processing" if url else "preparing"
    with db.db() as conn:
        conn.execute(
            """INSERT INTO sources(id, title, platform, author, url, file_name, file_path,
                   file_size, status, transcript, meta, is_demo, created_at)
               VALUES(?, ?, ?, ?, ?, '', '', 0, 'ready', '', ?, 0, ?)""",
            (source_id, title, platform or "视频号", author, url,
             json.dumps({"options": options}, ensure_ascii=False), created),
        )
        conn.execute(
            """INSERT INTO decompositions(id, source_id, title, status, data, options, is_demo,
                   created_at, updated_at)
               VALUES(?, ?, ?, ?, '{}', ?, 0, ?, ?)""",
            (decomp_id, source_id, title, status, json.dumps(options, ensure_ascii=False),
             created, created),
        )
    if url:
        _finish_later(decomp_id)
    return decomp_id


def _fetch_link_source(source: dict) -> dict:
    """把只有链接的素材落地：视频下载后转写；图文笔记下载图片并识别文字。"""
    info = link_parser.parse(source["url"])
    platform = info.get("platform") or source.get("platform") or "视频号"
    kind = info.get("kind") or "video"
    title = (info.get("title") or "").strip()
    author = (info.get("author") or {}).get("nickname") or source.get("author") or ""
    cover = info.get("cover_url") or ""
    referer = link_parser.referer_for(platform)

    meta = _jloads(source.get("meta"), {})
    meta["link"] = {
        "url": source["url"], "title": title, "cover": cover,
        "author": author, "stats": info.get("stats") or {},
        "platform": platform, "kind": kind,
        "fetched_at": db.now_iso(),
    }

    if kind == "image_note":
        meta = _fetch_note_images(source, info, meta, referer)
        with db.db() as conn:
            conn.execute(
                "UPDATE sources SET title=?, author=?, platform=?, status='ready', meta=? WHERE id=?",
                (title or source.get("title") or "", author, platform,
                 json.dumps(meta, ensure_ascii=False), source["id"]),
            )
            if title:
                conn.execute(
                    "UPDATE decompositions SET title=? WHERE source_id=? "
                    "AND (title='' OR title='未命名内容' OR title='链接素材（待解析）')",
                    (title, source["id"]),
                )
        db.log_event("link.fetched_note", {
            "source": source["id"],
            "images": len((meta.get("note") or {}).get("images") or []),
        })
        return db.get_source(source["id"])

    dest = config.UPLOAD_DIR / f"{db.new_id('file')}.mp4"
    size = link_parser.download(info["video_url"], dest, referer=referer)

    with db.db() as conn:
        conn.execute(
            "UPDATE sources SET title=?, author=?, platform=?, file_name=?, file_path=?, file_size=?, "
            "status='ready', meta=? WHERE id=?",
            (title or source.get("title") or "", author, platform, dest.name, str(dest),
             size, json.dumps(meta, ensure_ascii=False), source["id"]),
        )
        if title:
            conn.execute(
                "UPDATE decompositions SET title=? WHERE source_id=? "
                "AND (title='' OR title='未命名内容' OR title='链接素材（待解析）')",
                (title, source["id"]),
            )
    db.log_event("link.fetched", {"source": source["id"], "size": size, "platform": platform})
    asr.enqueue(source["id"])
    return db.get_source(source["id"])


def _fetch_note_images(source: dict, info: dict, meta: dict, referer: str) -> dict:
    """下载图文笔记的全部图片，并做本地文字识别。"""
    sid = source["id"]
    img_dir = config.DATA_DIR / "images" / sid
    img_dir.mkdir(parents=True, exist_ok=True)

    images: list[dict] = []
    for idx, raw in enumerate(info.get("image_list") or [], 1):
        url = raw.get("url") if isinstance(raw, dict) else raw
        if not url:
            continue
        dest = img_dir / f"{idx:02d}.jpg"
        item = {"index": idx, "file": dest.name, "source_url": url, "text": "", "lines": []}
        try:
            item["bytes"] = link_parser.download_image(url, dest, referer=referer)
        except link_parser.LinkError as exc:
            item["error"] = str(exc)
        images.append(item)

    meta["note"] = {
        "title": (info.get("title") or "").strip(),
        "desc": (info.get("desc") or "").strip(),
        "images": images,
        "ocr_done": False,
    }
    _ocr_note_images(sid, meta)
    return meta


def _split_note_lines(lines: list[dict]) -> dict:
    """把一张图上的文字切成「标题」和「正文段落」。

    标题靠字号判断：OCR 会返回每行外框高度，标题字大、正文字小。
    正文按句子合段：行尾没有句号就连到下一行，避免"一句一断"。
    """
    if not lines:
        return {"title": "", "paragraphs": [], "body": ""}

    # 同一水平线上的文字块（左右并排）要按 x 从左到右读，不能让 y 的细微差别打乱顺序
    heights_all = sorted(float(l.get("h") or 0) for l in lines if l.get("h"))
    median_h = heights_all[len(heights_all) // 2] if heights_all else 10.0
    band = max(8.0, median_h * 0.6)
    ordered = sorted(lines, key=lambda l: (int((l.get("y") or 0) / band), l.get("x") or 0))

    heights = [float(l.get("h") or 0) for l in ordered]
    max_h = max(heights) if heights else 0
    cut = max_h * 0.72

    # 标题：字号明显偏大的、从上往下连续几行
    head_idx: list[int] = []
    if max_h and len(ordered) <= 5 and min(heights) >= max_h * 0.45:
        # 封面常见：整张就几行大字（字号有大小层次但都远大于正文），那就全是标题
        head_idx = list(range(len(ordered)))
    else:
        for i, line in enumerate(ordered[:4]):
            if float(line.get("h") or 0) >= cut:
                head_idx.append(i)
            else:
                break
    # 字号一样时退化：第一行短且以冒号/问号结尾，也算标题
    if not head_idx:
        first = ordered[0].get("text") or ""
        if len(first) <= 22 and first[-1:] in "：:？?！!":
            head_idx = [0]

    title = "\n".join(ordered[i].get("text") or "" for i in head_idx)
    body_lines = [l.get("text") or "" for i, l in enumerate(ordered) if i not in head_idx]

    sentences: list[str] = []
    buf = ""
    for text in body_lines:
        buf += text
        if text[-1:] in "。！？；":
            sentences.append(buf)
            buf = ""
    if buf.strip():
        sentences.append(buf)

    paragraphs = ["".join(sentences[i:i + 2]) for i in range(0, len(sentences), 2)]
    return {"title": title, "paragraphs": paragraphs, "body": "\n".join(paragraphs)}


def _ocr_note_images(source_id: str, meta: dict) -> None:
    """给图文笔记的图片逐张提取文字，并按「标题 / 正文」分开写回 meta。"""
    note = meta.get("note") or {}
    images = [i for i in (note.get("images") or []) if i.get("file") and not i.get("error")]
    if not images:
        return
    base = config.DATA_DIR / "images" / source_id
    try:
        results = note_ocr.run([base / i["file"] for i in images])
    except note_ocr.OcrUnavailable as exc:
        note["ocr_error"] = str(exc)
        return
    by_file = {Path(str(r.get("file", ""))).name: r for r in results}
    for item in images:
        row = by_file.get(item["file"]) or {}
        lines = [l for l in (row.get("lines") or []) if (l.get("score") or 0) >= 0.6]
        item["lines"] = lines
        parts = _split_note_lines(lines)
        item["title"] = parts["title"]
        item["paragraphs"] = parts["paragraphs"]
        item["body"] = parts["body"]
        item["text"] = "\n".join(l["text"] for l in lines)
    note["ocr_done"] = True


def _decompose_image_note(decomp_id: str, source: dict, title: str,
                          old_data_raw: str, rerun: bool = False) -> None:
    """图文笔记走独立的拆解通道：不转写、不做分镜。"""
    meta = _jloads(source.get("meta"), {})
    note = meta.get("note") or {}
    images = note.get("images") or []
    if not images:
        _fail_decomposition(decomp_id, "没有拿到图片，无法拆解这条图文笔记")
        return
    try:
        data = llm.decompose_image_note(
            title or note.get("title") or "未命名笔记",
            note.get("desc") or "",
            images,
            source.get("author") or "",
            source.get("platform") or "小红书",
        )
    except Exception as exc:  # noqa: BLE001
        _fail_decomposition(decomp_id, f"图文拆解失败：{exc}")
        return
    old_data = _jloads(old_data_raw, {})
    if old_data.get("rewrite"):
        data["rewrite"] = old_data["rewrite"]
    _finish_decomposition(decomp_id, data, False, "重新拆解" if rerun else "图文笔记拆解")


def _complete_decomposition(decomp_id: str, rerun: bool = False) -> None:
    """链接先自动解析落地；视频走转写拆解，图文走图片识别拆解。"""
    try:
        with db.db() as conn:
            row = conn.execute(
                "SELECT d.id, d.title, d.source_id, d.data FROM decompositions d WHERE d.id=?",
                (decomp_id,),
            ).fetchone()
        if not row:
            return
        title = row["title"] or "未命名内容"
        source = db.get_source(row["source_id"]) if row["source_id"] else None
        if source and not source.get("file_path") and source.get("url"):
            try:
                source = _fetch_link_source(source)
            except link_parser.LinkError as exc:
                _fail_decomposition(decomp_id, str(exc))
                return
        link_kind = ((_jloads(source.get("meta"), {}) if source else {}).get("link") or {}).get("kind")
        if link_kind == "image_note":
            _decompose_image_note(decomp_id, source, title, row["data"], rerun)
            return
        source = _wait_transcript(source)

        if source and source.get("file_path"):
            if source["status"] == "transcribing":
                _fail_decomposition(decomp_id, "转写超时，请稍后在字幕页重新转写后再拆解")
                return
            if source["status"] == "transcribe_failed" or not source["transcript"]:
                detail = _jloads(source["meta"], {}).get("error", "")
                _fail_decomposition(decomp_id, "没有拿到字幕：" + (detail or "转写未完成"))
                return
            source_meta = _jloads(source.get("meta"), {})
            asr_meta = source_meta.get("asr") or {}
            paragraphs = (asr_meta.get("clean_paragraphs")
                          or asr_meta.get("proofread_paragraphs")
                          or asr_meta.get("paragraphs") or [])
            ocr_items = (asr_meta.get("ocr") or {}).get("items") or []
            transcript_text = source["transcript"]
            if paragraphs and not asr_meta.get("proofread_paragraphs"):
                proof = llm.proofread(paragraphs, title)
                if proof:
                    paragraphs = proof["paragraphs"]
                    transcript_text = "\n".join(p["text"] for p in paragraphs)
                    asr_meta["proofread_paragraphs"] = paragraphs
                    asr_meta["proofread_changes"] = proof["changes"]
                    source_meta["asr"] = asr_meta
                    with db.db() as conn:
                        conn.execute(
                            "UPDATE sources SET transcript=?, meta=? WHERE id=?",
                            (transcript_text,
                             json.dumps(source_meta, ensure_ascii=False),
                             source["id"]),
                        )
            if ocr_items and paragraphs:
                cleaned = llm.clean_transcript(paragraphs, ocr_items, title)
                if cleaned:
                    paragraphs = cleaned
                    transcript_text = "\n".join(p["text"] for p in cleaned)
                    asr_meta["clean_paragraphs"] = cleaned
                    asr_meta["clean_transcript"] = transcript_text
                    source_meta["asr"] = asr_meta
                    with db.db() as conn:
                        conn.execute(
                            "UPDATE sources SET transcript=?, meta=? WHERE id=?",
                            (transcript_text,
                             json.dumps(source_meta, ensure_ascii=False),
                             source["id"]),
                        )
            # 标点还原：产出「标点整理版」全文（原始转写字段不动，只存 meta）
            if paragraphs and not asr_meta.get("punctuated_text"):
                punct = llm.restore_punctuation(
                    paragraphs, title, source.get("duration") or 0)
                if punct:
                    asr_meta["punctuated_text"] = punct["text"]
                    asr_meta["punctuated_sentences"] = punct["sentences"]
                    source_meta["asr"] = asr_meta
                    with db.db() as conn:
                        conn.execute(
                            "UPDATE sources SET meta=? WHERE id=?",
                            (json.dumps(source_meta, ensure_ascii=False), source["id"]),
                        )
                    transcript_text = punct["text"]
            data = llm.decompose(
                title, transcript_text, source.get("duration") or 0,
                source.get("author") or "", source.get("platform") or "视频号",
                paragraphs=paragraphs,
            )
            old_data = _jloads(row["data"], {})
            if old_data.get("rewrite"):
                # 重新拆解只更新拆解部分，已有的改写稿保留
                data["rewrite"] = old_data["rewrite"]
            shots = asr_meta.get("shots") or []
            if shots:
                durations = [s.get("duration", 0) for s in shots if s.get("duration")]
                avg = round(sum(durations) / len(durations), 2) if durations else 0
                data["pacing"] = {
                    "shots": len(shots),
                    "avg_shot": f"{avg}s" if avg else "",
                    "rhythm": "",
                    "notes": "",
                }
                data["storyboard"] = _build_storyboard(
                    shots, asr_meta.get("segments") or paragraphs
                )
            _finish_decomposition(decomp_id, data, False,
                                  "重新拆解" if rerun else "云端模型拆解")
            return

        # 没有视频文件（链接导入、只填了标题）：读不到真实内容，不能凭空拆解
        if source and source.get("url"):
            _fail_decomposition(
                decomp_id,
                "这条是链接导入的。链接解析还没接入（第 5 阶段），目前读不到视频内容；"
                "可以先把视频下载下来，再在本页上传视频文件拆解。",
            )
        else:
            _fail_decomposition(decomp_id, "没有可用的视频文件或字幕，无法拆解。请上传视频后再试。")
    except llm.LLMUnavailable as exc:
        _fail_decomposition(decomp_id, "本地拆解模型不可用：" + str(exc))
    except Exception as exc:  # noqa: BLE001
        _fail_decomposition(decomp_id, str(exc) or "拆解失败")


def _finish_later(decomp_id: str, rerun: bool = False, delay: float = 3.2) -> None:
    timer = threading.Timer(delay, _complete_decomposition, args=(decomp_id, rerun))
    timer.daemon = True
    timer.start()


# ---------- health ----------

@router.get("/health")
def health():
    return {
        "ok": True,
        "name": config.APP_NAME,
        "version": config.APP_VERSION,
        "mode": "demo" if config.DEMO_MODE else "real",
        "data_dir": str(config.DATA_DIR),
    }


# ---------- overview ----------

@router.get("/overview")
def overview():
    with db.db() as conn:
        total = conn.execute("SELECT COUNT(*) c FROM decompositions").fetchone()["c"]
        done = conn.execute("SELECT COUNT(*) c FROM decompositions WHERE status='done'").fetchone()["c"]
        processing = conn.execute("SELECT COUNT(*) c FROM decompositions WHERE status='processing'").fetchone()["c"]
        sources = conn.execute("SELECT COUNT(*) c FROM sources").fetchone()["c"]
        week_ago = (datetime.now() - timedelta(days=7)).isoformat(timespec="seconds")
        week = conn.execute(
            "SELECT COUNT(*) c FROM decompositions WHERE created_at >= ?", (week_ago,)
        ).fetchone()["c"]
        recent = conn.execute(
            "SELECT * FROM decompositions ORDER BY created_at DESC LIMIT 5"
        ).fetchall()
        platform_rows = conn.execute(
            "SELECT COALESCE(s.platform,'未标注') p, COUNT(*) c "
            "FROM decompositions d LEFT JOIN sources s ON s.id=d.source_id "
            "GROUP BY p ORDER BY c DESC"
        ).fetchall()
        daily_rows = conn.execute(
            "SELECT substr(created_at,1,10) d, COUNT(*) c FROM decompositions "
            "WHERE created_at >= ? GROUP BY d", (week_ago,)
        ).fetchall()

    daily_map = {r["d"]: r["c"] for r in daily_rows}
    days = []
    for i in range(6, -1, -1):
        day = (datetime.now() - timedelta(days=i))
        key = day.strftime("%Y-%m-%d")
        days.append({"label": day.strftime("%m/%d"), "value": daily_map.get(key, 0)})

    todos = []
    for row in recent:
        if row["status"] == "processing":
            todos.append({"kind": "processing", "id": row["id"], "title": row["title"],
                          "text": "正在拆解，完成后可查看结果"})
    todos.append({"kind": "profile", "id": "profile", "title": "补充 IP 档案",
                  "text": "定位、受众和表达风格尚未完善"})
    todos.append({"kind": "plan", "id": "plan", "title": "本周内容计划",
                  "text": "还没有为本周安排选题"})

    return {
        "stats": {
            "total": total, "done": done, "processing": processing,
            "sources": sources, "week": week,
        },
        "recent": [_summary(r) for r in recent],
        "todos": todos[:5],
        "platforms": [{"name": r["p"], "value": r["c"]} for r in platform_rows],
        "daily": days,
        "mode": "demo" if config.DEMO_MODE else "real",
        "metrics": _real_metrics(),
        "sync": _sync_state(),
        "login": login_scan.status(),
        "account": db.get_setting("account", {}),
    }


def _yesterday() -> str:
    return (datetime.now() - timedelta(days=1)).strftime("%Y-%m-%d")


def _real_metrics() -> dict | None:
    row = db.latest_metric()
    if not row:
        return None
    return {
        "date": row["stat_date"],
        "followers": row["followers_total"],
        "followersNet": row["followers_net"],
        "followersAdd": row["followers_add"],
        "followersDel": row["followers_del"],
        "totalViews": row["play_total"],
        "topViews": row["top_play"],
        "topTitle": row["top_title"],
        "engagement": row["engagement_rate"],
        "like": row["like_total"],
        "comment": row["comment_total"],
        "forward": row["forward_total"],
        "fav": row["fav_total"],
        "syncedAt": row["synced_at"],
        "isYesterday": row["stat_date"] == _yesterday(),
    }


def _sync_state() -> dict:
    state = db.get_setting("sync_state", {}) or {}
    latest = db.latest_metric()
    y = _yesterday()
    status = state.get("status") or ("ok" if latest and latest["stat_date"] == y else "pending")
    if status == "ok" and latest and latest["stat_date"] != y:
        status = "pending"
    return {
        "status": status,
        "at": state.get("at") or (latest["synced_at"] if latest else ""),
        "date": (latest or {}).get("stat_date", ""),
        "message": state.get("message", ""),
        "running": channels_sync.is_running(),
        "hasData": bool(latest),
        "scheduler": scheduler.status(),
    }


@router.get("/sync/status")
def sync_status():
    return _sync_state()


@router.post("/sync/run")
def sync_run(date: str = ""):
    if channels_sync.is_running():
        return {"ok": False, "status": "running", "message": "正在同步，请稍候"}

    def _work():
        channels_sync._run(date or None)

    threading.Thread(target=_work, daemon=True).start()
    return {"ok": True, "status": "started"}


@router.post("/login/scan")
def login_scan_start():
    """打开带界面的 Chrome，等用户扫码登录视频号助手。"""
    return login_scan.start()


@router.get("/login/status")
def login_scan_status():
    result = login_scan.status()
    result["sync"] = _sync_state()
    return result


# ---------- decompositions ----------

@router.get("/decompositions")
def list_decompositions(q: str = "", status: str = "", platform: str = ""):
    sql = ("SELECT d.*, s.author AS s_author, s.platform AS s_platform, s.meta AS s_meta "
           "FROM decompositions d LEFT JOIN sources s ON s.id=d.source_id WHERE 1=1")
    params: list = []
    if q:
        sql += " AND d.title LIKE ?"
        params.append(f"%{q}%")
    if status:
        sql += " AND d.status=?"
        params.append(status)
    if platform:
        sql += " AND s.platform=?"
        params.append(platform)
    sql += " ORDER BY d.created_at DESC"
    with db.db() as conn:
        rows = conn.execute(sql, params).fetchall()
    return {"items": [_summary(r) for r in rows], "total": len(rows)}


@router.get("/decompositions/{decomp_id}")
def get_decomposition(decomp_id: str):
    with db.db() as conn:
        row = conn.execute("SELECT * FROM decompositions WHERE id=?", (decomp_id,)).fetchone()
    if not row:
        raise HTTPException(404, "拆解不存在")
    return _detail(row)


@router.post("/decompositions")
async def create_decomposition(
    title: str = Form(""),
    author: str = Form(""),
    platform: str = Form("视频号"),
    url: str = Form(""),
    storyboard: str = Form("1"),
    account: str = Form(""),
    file: UploadFile | None = File(None),
):
    clean_title = (title or "").strip()
    want_storyboard = storyboard not in ("0", "false", "False", "")
    account_name = (account or "").strip()
    file_name = ""
    file_path = ""
    file_size = 0

    if file is not None and file.filename:
        safe_name = Path(file.filename).name
        target = config.UPLOAD_DIR / f"{db.new_id('file')}_{safe_name}"
        size = 0
        with target.open("wb") as fh:
            while True:
                chunk = await file.read(1024 * 1024)
                if not chunk:
                    break
                size += len(chunk)
                if size > config.UPLOAD_LIMIT_MB * 1024 * 1024:
                    fh.close()
                    target.unlink(missing_ok=True)
                    raise HTTPException(413, f"文件超过 {config.UPLOAD_LIMIT_MB}MB 限制")
                fh.write(chunk)
        file_name = safe_name
        file_path = str(target)
        file_size = size
        if not clean_title:
            clean_title = Path(safe_name).stem

    if not clean_title:
        clean_title = "未命名内容"

    source_id = db.new_id("src")
    decomp_id = db.new_id("dec")
    created = db.now_iso()
    with db.db() as conn:
        option_data = {"storyboard": want_storyboard}
        if account_name:
            option_data["account"] = account_name
        source_meta = json.dumps({"options": option_data}, ensure_ascii=False)
        options = json.dumps(option_data, ensure_ascii=False)
        conn.execute(
            """INSERT INTO sources(id, title, platform, author, url, file_name, file_path,
                   file_size, status, transcript, meta, is_demo, created_at)
               VALUES(?, ?, ?, ?, ?, ?, ?, ?, 'ready', '', ?, 0, ?)""",
            (source_id, clean_title, platform or "视频号", author, url,
             file_name, file_path, file_size, source_meta, created),
        )
        conn.execute(
            """INSERT INTO decompositions(id, source_id, title, status, data, options, is_demo,
                   created_at, updated_at)
               VALUES(?, ?, ?, 'processing', '{}', ?, 0, ?, ?)""",
            (decomp_id, source_id, clean_title, options, created, created),
        )
        conn.execute(
            "INSERT INTO events(type, payload, created_at) VALUES(?, ?, ?)",
            ("decomposition.created",
             json.dumps({"id": decomp_id, "file": file_name,
                         "storyboard": want_storyboard,
                         "account": account_name}, ensure_ascii=False), created),
        )
    if file_path:
        asr.enqueue(source_id)
    _finish_later(decomp_id)
    return {"id": decomp_id, "status": "processing"}


@router.post("/decompositions/{decomp_id}/rerun")
def rerun_decomposition(decomp_id: str):
    with db.db() as conn:
        row = conn.execute("SELECT id FROM decompositions WHERE id=?", (decomp_id,)).fetchone()
        if not row:
            raise HTTPException(404, "拆解不存在")
        conn.execute(
            "UPDATE decompositions SET status='processing', updated_at=? WHERE id=?",
            (db.now_iso(), decomp_id),
        )
    _finish_later(decomp_id, rerun=True, delay=2.4)
    return {"id": decomp_id, "status": "processing"}


@router.post("/decompositions/{decomp_id}/rewrite")
def generate_rewrite(decomp_id: str):
    """基于已完成的拆解结构，另写一份改写稿；拆解数据只读。"""
    with db.db() as conn:
        row = conn.execute("SELECT * FROM decompositions WHERE id=?", (decomp_id,)).fetchone()
    if not row:
        raise HTTPException(404, "拆解不存在")
    if row["status"] != "done":
        raise HTTPException(409, "拆解还没完成，不能改写")
    data = _jloads(row["data"], {})
    structure = data.get("structure") or []
    if not structure:
        raise HTTPException(400, "这条拆解没有结构分段，无法据此改写")
    source = db.get_source(row["source_id"]) if row["source_id"] else None
    if not source:
        raise HTTPException(400, "找不到原始素材")
    asr_meta = _jloads(source.get("meta"), {}).get("asr") or {}
    paragraphs = (asr_meta.get("clean_paragraphs")
                  or asr_meta.get("proofread_paragraphs")
                  or asr_meta.get("paragraphs") or [])
    try:
        result = llm.rewrite(
            row["title"] or "", source.get("transcript") or data.get("transcript") or "",
            source.get("duration") or 0, source.get("author") or "",
            source.get("platform") or "视频号",
            structure=structure, paragraphs=paragraphs,
        )
    except llm.LLMUnavailable as exc:
        raise HTTPException(503, str(exc))
    data["rewrite"] = result
    with db.db() as conn:
        conn.execute(
            "UPDATE decompositions SET data=?, updated_at=? WHERE id=?",
            (json.dumps(data, ensure_ascii=False), db.now_iso(), decomp_id),
        )
        vrow = conn.execute(
            "SELECT COALESCE(MAX(version),0) v FROM versions WHERE decomposition_id=?",
            (decomp_id,),
        ).fetchone()
        version = int(vrow["v"]) + 1
        conn.execute(
            "INSERT INTO versions(id, decomposition_id, version, data, note, created_at) "
            "VALUES(?, ?, ?, ?, ?, ?)",
            (db.new_id("ver"), decomp_id, version,
             json.dumps(data, ensure_ascii=False), "生成改写稿", db.now_iso()),
        )
    db.log_event("decomposition.rewrite", {"id": decomp_id, "chars": result["chars"]})
    return {"ok": True, "rewrite": result}


@router.put("/decompositions/{decomp_id}")
def update_decomposition(decomp_id: str, payload: dict):
    note = str(payload.get("note") or "手动编辑")
    data = payload.get("data")
    if not isinstance(data, dict):
        raise HTTPException(400, "data 必须是对象")
    with db.db() as conn:
        row = conn.execute("SELECT id FROM decompositions WHERE id=?", (decomp_id,)).fetchone()
        if not row:
            raise HTTPException(404, "拆解不存在")
        conn.execute(
            "UPDATE decompositions SET data=?, updated_at=? WHERE id=?",
            (json.dumps(data, ensure_ascii=False), db.now_iso(), decomp_id),
        )
        vrow = conn.execute(
            "SELECT COALESCE(MAX(version),0) v FROM versions WHERE decomposition_id=?",
            (decomp_id,),
        ).fetchone()
        version = int(vrow["v"]) + 1
        conn.execute(
            "INSERT INTO versions(id, decomposition_id, version, data, note, created_at) "
            "VALUES(?, ?, ?, ?, ?, ?)",
            (db.new_id("ver"), decomp_id, version,
             json.dumps(data, ensure_ascii=False), note, db.now_iso()),
        )
    return {"ok": True, "version": version}


@router.delete("/decompositions/{decomp_id}")
def delete_decomposition(decomp_id: str):
    with db.db() as conn:
        row = conn.execute(
            "SELECT d.id, s.file_path FROM decompositions d "
            "LEFT JOIN sources s ON s.id=d.source_id WHERE d.id=?", (decomp_id,)
        ).fetchone()
        if not row:
            raise HTTPException(404, "拆解不存在")
        conn.execute("DELETE FROM decompositions WHERE id=?", (decomp_id,))
        if row["file_path"]:
            try:
                Path(row["file_path"]).unlink(missing_ok=True)
            except Exception:
                pass
    return {"ok": True}


@router.get("/decompositions/{decomp_id}/versions/{version}")
def get_version(decomp_id: str, version: int):
    with db.db() as conn:
        row = conn.execute(
            "SELECT * FROM versions WHERE decomposition_id=? AND version=?",
            (decomp_id, version),
        ).fetchone()
    if not row:
        raise HTTPException(404, "版本不存在")
    return {"version": row["version"], "note": row["note"],
            "created_at": row["created_at"], "data": _jloads(row["data"], {})}


# ---------- sources ----------

@router.get("/sources")
def list_sources():
    with db.db() as conn:
        rows = conn.execute("SELECT * FROM sources ORDER BY created_at DESC").fetchall()
    return {"items": [{
        "id": r["id"], "title": r["title"], "platform": r["platform"],
        "author": r["author"], "url": r["url"], "file_name": r["file_name"],
        "file_size": r["file_size"], "status": r["status"],
        "created_at": r["created_at"], "is_demo": bool(r["is_demo"]),
    } for r in rows]}


@router.post("/sources/{source_id}/transcribe")
def source_transcribe(source_id: str):
    return asr.enqueue(source_id)


@router.post("/llm/test")
def llm_test():
    """检查云端模型配置：只请求模型列表，不产生费用。"""
    return llm.status(check=True)


@router.post("/ocr/test")
def ocr_test():
    """测试画面字幕 OCR 配置（发一张 64×64 白图，产生极小消耗）。"""
    return ocr.status(check=True)


@router.post("/link/login")
def link_login():
    """打开浏览器，用微信扫码登录腾讯元宝（视频号链接解析用）。"""
    return link_parser.start_login()


@router.get("/link/status")
def link_status():
    return link_parser.login_status()


_phone_lock = threading.Lock()


@router.post("/phone/clip")
def phone_clip(payload: dict):
    """手机剪贴板回传：只存链接，不自动拆解。"""
    url = str(payload.get("url") or "").strip()
    if not (url.startswith("https://weixin.qq.com/sph/") or url.startswith("http://weixin.qq.com/sph/")):
        raise HTTPException(400, "不是视频号分享链接")
    account = str(payload.get("account") or "").strip()
    cutoff = (datetime.now() - timedelta(minutes=10)).isoformat(timespec="seconds")
    with _phone_lock:
        with db.db() as conn:
            row = conn.execute(
                "SELECT id FROM phone_links WHERE url=? AND created_at>=? LIMIT 1",
                (url, cutoff),
            ).fetchone()
            if row:
                return {"ok": True, "id": row["id"], "duplicate": True}
            link_id = db.new_id("pl")
            conn.execute(
                "INSERT INTO phone_links(id, url, account, note, used, created_at) VALUES(?,?,?,?,0,?)",
                (link_id, url, account, str(payload.get("note") or ""), db.now_iso()),
            )
    db.log_event("phone.clip", {"url": url, "id": link_id})
    return {"ok": True, "id": link_id}


@router.get("/phone/links")
def phone_links(limit: int = 50):
    with db.db() as conn:
        rows = conn.execute(
            "SELECT id, url, account, note, used, created_at FROM phone_links "
            "ORDER BY created_at DESC LIMIT ?", (max(1, min(limit, 200)),)
        ).fetchall()
    return {"items": [dict(r) for r in rows]}


@router.post("/phone/links/{link_id}/decompose")
def phone_link_decompose(link_id: str):
    with db.db() as conn:
        row = conn.execute("SELECT * FROM phone_links WHERE id=?", (link_id,)).fetchone()
    if not row:
        raise HTTPException(404, "链接不存在")
    decomp_id = _new_decomposition("", "", "视频号", row["url"],
                                   account=row["account"] or "", storyboard=True)
    with db.db() as conn:
        conn.execute("UPDATE phone_links SET used=1 WHERE id=?", (link_id,))
    return {"ok": True, "id": decomp_id}


# ---------- 账号级数据接口（TikHub） ----------

@router.get("/tikhub/status")
def tikhub_status():
    result = {"configured": tikhub.configured(), "price_hint": "视频号端点约 $0.01/次"}
    if result["configured"]:
        try:
            result["account"] = tikhub.account()
        except tikhub.TikHubError as exc:
            result["account_error"] = str(exc)
    return result


@router.post("/tikhub/probe")
def tikhub_probe(payload: dict):
    channel_id = str(payload.get("channel_id") or "").strip()
    if not channel_id.startswith("sph"):
        raise HTTPException(400, "请填 sph 开头的视频号 ID")
    try:
        result = tikhub.probe(channel_id)
    except tikhub.TikHubError as exc:
        raise HTTPException(503, str(exc))
    return {"ok": True, "username": result.get("username", ""),
            "saved_to": result.get("saved_to", "")}


@router.get("/dataxapi/status")
def dataxapi_status():
    return {"configured": dataxapi.configured(), "price_hint": "搜账号 $0.06 / 主页 $0.02 / 作品 $0.02 每页"}


@router.post("/dataxapi/probe")
def dataxapi_probe(payload: dict):
    nickname = str(payload.get("nickname") or "").strip()
    if not nickname:
        raise HTTPException(400, "请填视频号昵称（一字不差）")
    try:
        result = dataxapi.probe(nickname)
    except dataxapi.DataXError as exc:
        raise HTTPException(503, str(exc))
    return {"ok": True, "username": result.get("username", ""),
            "saved_to": result.get("saved_to", "")}


# ---------- 对标账号（视频号，DataXAPI） ----------

def _account_pages(pages: int) -> int:
    return max(1, min(int(pages or 1), 5))


def _snapshot_account(nickname: str, pages: int = 2) -> dict:
    """昵称 → 账号资料 + 多页作品；只发昵称/内部 ID。"""
    search = dataxapi.search_user(nickname)
    items = (search.get("data") or {}).get("items") or []
    exact = [i for i in items if (i.get("name") or "").strip() == nickname.strip()] or items
    if not exact:
        raise HTTPException(404, "没搜到这个昵称的视频号，请核对一字不差")
    username = str(exact[0].get("id") or "")
    if not username:
        raise HTTPException(502, "搜索返回里没有账号 ID")
    profile = dataxapi.user_get(username)
    info = dataxapi.normalize_profile((profile.get("data") or {}).get("item") or {})

    videos: list[dict] = []
    cursor = ""
    for _ in range(_account_pages(pages)):
        page = dataxapi.user_videos(username, cursor)
        data = page.get("data") or {}
        videos.extend(dataxapi.normalize_video(v) for v in (data.get("items") or []))
        # 游标在响应顶层 page 里，不在 data.page
        cursor = ((page.get("page") or {}).get("next_cursor")) or ""
        if not cursor:
            break
    seen = {}
    for video in videos:
        if video["id"]:
            seen.setdefault(video["id"], video)
    ordered = sorted(seen.values(), key=lambda v: v.get("published_at") or "", reverse=True)

    return {
        "platform": "视频号",
        "name": info["name"] or nickname.strip(),
        "username": username,
        "avatar": info["avatar"],
        "bio": info["bio"],
        "metrics": info["metrics"],
        "videos": ordered,
        "fetched_at": db.now_iso(),
    }


@router.get("/accounts")
def accounts_list():
    return {"items": db.list_accounts()}


@router.get("/spend/today")
def spend_today():
    """今日付费调用流水：本地 events 表统计，不调用任何接口、不花钱。"""
    import datetime as _dt
    today = _dt.date.today().isoformat()
    with db.db() as conn:
        rows = conn.execute(
            "SELECT payload, created_at FROM events WHERE type='tikhub.call' "
            "AND created_at LIKE ? ORDER BY id", (today + "%",)
        ).fetchall()
    total = 0.0
    by_api: dict[str, int] = {}
    for row in rows:
        try:
            data = json.loads(row["payload"] or "{}")
        except Exception:  # noqa: BLE001
            data = {}
        total += float(data.get("est_usd") or 0.01)
        path = str(data.get("path") or data.get("api") or "未知")
        key = path.rstrip("/").split("/")[-1]
        by_api[key] = by_api.get(key, 0) + 1
    return {"date": today, "calls": len(rows), "est_usd": round(total, 2), "by_api": by_api}


@router.get("/accounts/{account_id}")
def account_detail(account_id: str):
    account = db.get_account(account_id)
    if not account:
        raise HTTPException(404, "账号不存在")
    return account


@router.post("/accounts/preview")
def account_preview(payload: dict):
    """只查基础信息（搜索 + 主页 + 第一页），约 $0.03，不抓整段。"""
    nickname = str(payload.get("nickname") or "").strip()
    if not nickname:
        raise HTTPException(400, "请填视频号昵称（一字不差）")
    try:
        return account_fetch.preview(nickname)
    except LookupError as exc:
        raise HTTPException(404, str(exc))
    except tikhub.TikHubError as exc:
        raise HTTPException(503, str(exc))


@router.post("/accounts/{account_id}/collect")
def account_collect(account_id: str, payload: dict | None = None):
    """按选定范围抓作品。mode: m1/m3/m6/y1/all。"""
    account = db.get_account(account_id)
    if not account:
        raise HTTPException(404, "账号不存在")
    mode = str((payload or {}).get("mode") or account_fetch.DEFAULT_RANGE)
    try:
        account_fetch.collect(account["name"], mode=mode, account_id=account_id)
    except LookupError as exc:
        raise HTTPException(404, str(exc))
    except tikhub.TikHubError as exc:
        raise HTTPException(503, str(exc))
    return db.get_account(account_id)


@router.post("/accounts")
def account_create(payload: dict):
    nickname = str(payload.get("nickname") or "").strip()
    if not nickname:
        raise HTTPException(400, "请填视频号昵称（一字不差）")
    mode = str(payload.get("mode") or account_fetch.DEFAULT_RANGE)
    try:
        account_id = account_fetch.collect(nickname, mode=mode)
    except LookupError as exc:
        raise HTTPException(404, str(exc))
    except tikhub.TikHubError as exc:
        raise HTTPException(503, str(exc))
    filters = payload.get("filters") or {}
    account = db.get_account(account_id) or {}
    account["filters"] = {
        "days": int(filters.get("days") or 90),
        "metric": str(filters.get("metric") or "likes"),
        "min": int(filters.get("min") or 0),
    }
    db.save_account(account, account_id)
    db.log_event("account.created", {"id": account_id,
                                     "videos": len(account.get("videos") or []), "mode": mode})
    return db.get_account(account_id)


@router.post("/accounts/{account_id}/refresh")
def account_refresh(account_id: str, payload: dict | None = None):
    account = db.get_account(account_id)
    if not account:
        raise HTTPException(404, "账号不存在")
    payload = payload or {}
    mode = str(payload.get("mode") or account_fetch.DEFAULT_RANGE)
    try:
        account_fetch.collect(account["name"], mode=mode, account_id=account_id)
    except LookupError as exc:
        raise HTTPException(404, str(exc))
    except tikhub.TikHubError as exc:
        raise HTTPException(503, str(exc))
    return db.get_account(account_id)


@router.put("/accounts/{account_id}/filters")
def account_filters(account_id: str, payload: dict):
    account = db.get_account(account_id)
    if not account:
        raise HTTPException(404, "账号不存在")
    account["filters"] = {
        "days": int(payload.get("days") or 30),
        "metric": str(payload.get("metric") or "shares"),
        "min": int(payload.get("min") or 100),
    }
    db.save_account(account, account_id)
    return {"ok": True, "filters": account["filters"]}


@router.post("/accounts/{account_id}/analyze")
def account_analyze(account_id: str):
    account = db.get_account(account_id)
    if not account:
        raise HTTPException(404, "账号不存在")
    try:
        analysis = account_analysis.analyze(account)
    except llm.LLMUnavailable as exc:
        raise HTTPException(503, str(exc))
    data = {**account, "analysis": json.dumps(analysis, ensure_ascii=False)}
    db.save_account(data, account_id)
    db.log_event("account.analyzed", {"id": account_id})
    return {"ok": True, "analysis": analysis}


_video_locks: dict[str, threading.Lock] = {}
_video_locks_guard = threading.Lock()


def _video_lock(key: str) -> threading.Lock:
    with _video_locks_guard:
        return _video_locks.setdefault(key, threading.Lock())


def _find_decomp_for_video(video_id: str, account_name: str, title: str) -> dict | None:
    """这条作品是不是已经建过拆解：先按 video_id，再按「同账号 + 标题前 12 字」兼容老数据。"""
    with db.db() as conn:
        rows = conn.execute(
            "SELECT id, title, status, options FROM decompositions ORDER BY created_at DESC"
        ).fetchall()
    for row in rows:
        opt = _jloads(row["options"], {})
        if opt.get("video_id") == video_id:
            return {"id": row["id"], "status": row["status"], "title": row["title"]}
    key = (title or "")[:12]
    if not key:
        return None
    for row in rows:
        opt = _jloads(row["options"], {})
        if opt.get("account") and opt.get("account") == account_name \
                and (row["title"] or "")[:12] == key:
            return {"id": row["id"], "status": row["status"], "title": row["title"]}
    return None


def _save_video_link(account_id: str, video_id: str, share: str) -> None:
    """把分享链接永久写进账号作品表，以后同一条永不再取。"""
    account = db.get_account(account_id)
    if not account:
        return
    hit = False
    for item in account.get("videos") or []:
        if item.get("id") == video_id:
            item["link"] = share
            item["link_fetched_at"] = db.now_iso()
            hit = True
            break
    if hit:
        db.save_account(account, account_id)


def _prepare_link_then_run(decomp_id: str, account_id: str) -> None:
    """后台取分享链接 → 写回作品与素材 → 再走下载/转写/拆解。"""
    try:
        with db.db() as conn:
            row = conn.execute(
                "SELECT source_id, options FROM decompositions WHERE id=?", (decomp_id,)
            ).fetchone()
        if not row:
            return
        source_id = row["source_id"]
        video_id = str((_jloads(row["options"], {}) or {}).get("video_id") or "")
        if not video_id:
            _fail_decomposition(decomp_id, "这条拆解没有作品 ID，无法取链接")
            return

        # 取链接前再查一次：并发下如果别人已经取到，直接用，不再付费
        share = ""
        account = db.get_account(account_id) or {}
        for item in account.get("videos") or []:
            if item.get("id") == video_id and item.get("link"):
                share = item["link"]
                break
        if not share:
            share = tikhub.video_share_url(video_id)     # $0.01，只在这里花一次
            _save_video_link(account_id, video_id, share)
            db.log_event("link.paid", {"decomp": decomp_id, "video_id": video_id})
        with db.db() as conn:
            conn.execute("UPDATE sources SET url=? WHERE id=?", (share, source_id))
    except tikhub.TikHubError as exc:
        _fail_decomposition(decomp_id, "取分享链接失败：" + str(exc))
        return
    except Exception as exc:  # noqa: BLE001
        _fail_decomposition(decomp_id, "取分享链接出错：" + str(exc)[:120])
        return
    _finish_later(decomp_id)


@router.post("/accounts/{account_id}/videos/{video_id}/decompose")
def account_video_decompose(account_id: str, video_id: str, payload: dict | None = None):
    account = db.get_account(account_id)
    if not account:
        raise HTTPException(404, "账号不存在")
    video = next((v for v in account.get("videos") or [] if v.get("id") == video_id), None)
    if not video:
        raise HTTPException(404, "这条作品不在账号列表里，先刷新")
    title = (video.get("text") or "").strip()[:60] or "未命名作品"

    # 关键：先查重。已经建过拆解就直接返回，不再新建、不再付费
    with _video_lock(f"{account_id}:{video_id}"):
        existing = _find_decomp_for_video(video_id, account["name"], title)
        if existing:
            return {"ok": True, "id": existing["id"], "existing": True,
                    "status": existing["status"], "share_url": video.get("link") or ""}

        # 已有链接：立刻建拆解，不花钱
        if video.get("link"):
            decomp_id = _new_decomposition(
                title, account["name"], account["platform"], video["link"],
                account=account["name"], storyboard=True, video_id=video_id,
            )
            return {"ok": True, "id": decomp_id, "share_url": video["link"]}

        # 没有链接：先建一条「正在取链接」的记录，后台去取，界面立刻返回
        decomp_id = _new_decomposition(
            title, account["name"], account["platform"], "",
            account=account["name"], storyboard=True, video_id=video_id,
        )
    threading.Thread(target=_prepare_link_then_run,
                     args=(decomp_id, account_id), daemon=True).start()
    return {"ok": True, "id": decomp_id, "pending_link": True}


@router.delete("/accounts/{account_id}")
def account_delete(account_id: str):
    db.delete_account(account_id)
    return {"ok": True}


@router.get("/export")
def export_data():
    """导出本机的真实拆解和账号数据（不含演示数据、不含 Key），供发给同事导入。"""
    with db.db() as conn:
        decs = conn.execute(
            "SELECT d.title, d.data, d.options, "
            "s.platform AS s_platform, s.author AS s_author, s.url AS s_url, "
            "s.duration AS s_duration, s.transcript AS s_transcript, s.meta AS s_meta "
            "FROM decompositions d LEFT JOIN sources s ON s.id=d.source_id "
            "WHERE d.is_demo=0 AND d.status='done' ORDER BY d.created_at"
        ).fetchall()
        accs = conn.execute("SELECT * FROM accounts ORDER BY name").fetchall()

    decompositions = [{
        "title": d["title"],
        "platform": d["s_platform"] or "",
        "author": d["s_author"] or "",
        "url": d["s_url"] or "",
        "duration": d["s_duration"] or 0,
        "transcript": d["s_transcript"] or "",
        "source_meta": d["s_meta"] or "{}",
        "data": d["data"],
        "options": d["options"],
    } for d in decs]

    accounts = [{
        "name": a["name"], "platform": a["platform"], "username": a["username"],
        "avatar": a["avatar"], "bio": a["bio"],
        "metrics": a["metrics"], "videos": a["videos"], "analysis": a["analysis"],
        "filters": a["filters"],
    } for a in accs]

    return {
        "type": "ipwb-export", "version": 1, "exported_at": db.now_iso(),
        "decompositions": decompositions, "accounts": accounts,
        "counts": {"decompositions": len(decompositions), "accounts": len(accounts)},
    }


@router.post("/import")
def import_data(payload: dict):
    """导入同事导出的数据；按标题/账号名去重，已存在的跳过。"""
    now = db.now_iso()
    imported_dec = skipped_dec = 0
    imported_acc = skipped_acc = 0

    for item in payload.get("decompositions") or []:
        title = (item.get("title") or "").strip()
        if not title:
            continue
        with db.db() as conn:
            exists = conn.execute("SELECT id FROM decompositions WHERE title=?", (title,)).fetchone()
        if exists:
            skipped_dec += 1
            continue
        source_id = db.new_id("src")
        decomp_id = db.new_id("dec")
        with db.db() as conn:
            conn.execute(
                "INSERT INTO sources(id,title,platform,author,url,duration,status,transcript,meta,is_demo,created_at) "
                "VALUES(?,?,?,?,?,?,'ready',?,?,0,?)",
                (source_id, title, item.get("platform") or "视频号", item.get("author") or "",
                 item.get("url") or "", item.get("duration") or 0,
                 item.get("transcript") or "", item.get("source_meta") or "{}", now),
            )
            conn.execute(
                "INSERT INTO decompositions(id,source_id,title,status,data,options,is_demo,created_at,updated_at) "
                "VALUES(?,?,?,'done',?,?,0,?,?)",
                (decomp_id, source_id, title, item.get("data") or "{}",
                 item.get("options") or "{}", now, now),
            )
        imported_dec += 1

    for item in payload.get("accounts") or []:
        name = (item.get("name") or "").strip()
        if not name:
            continue
        with db.db() as conn:
            exists = conn.execute("SELECT id FROM accounts WHERE name=?", (name,)).fetchone()
        if exists:
            skipped_acc += 1
            continue
        acc_id = db.new_id("acc")
        with db.db() as conn:
            conn.execute(
                "INSERT INTO accounts(id,platform,name,username,avatar,bio,metrics,videos,analysis,filters,fetched_at,created_at,updated_at) "
                "VALUES(?,?,?,?,?,?,?,?,?,?,'',?,?)",
                (acc_id, item.get("platform") or "视频号", name, item.get("username") or "",
                 item.get("avatar") or "", item.get("bio") or "",
                 item.get("metrics") or "{}", item.get("videos") or "[]",
                 item.get("analysis") or "", item.get("filters") or "{}", now, now),
            )
        imported_acc += 1

    db.log_event("import", {"dec": imported_dec, "acc": imported_acc,
                            "skip_dec": skipped_dec, "skip_acc": skipped_acc})
    return {
        "ok": True,
        "imported": {"decompositions": imported_dec, "accounts": imported_acc},
        "skipped": {"decompositions": skipped_dec, "accounts": skipped_acc},
    }


def _find_share_url(payload) -> str:
    hit = []

    def walk(node):
        if isinstance(node, dict):
            for value in node.values():
                walk(value)
        elif isinstance(node, list):
            for value in node:
                walk(value)
        elif isinstance(node, str) and node.startswith("http") and (
                "weixin.qq.com/sph" in node or "channels.weixin.qq.com" in node):
            hit.append(node)

    walk(payload)
    return hit[0] if hit else ""


# ---------- metrics ----------

@router.get("/metrics")
def metrics_list(limit: int = 60):
    rows = db.list_metrics(limit)
    for row in rows:
        row.pop("raw", None)
    return {"items": rows, "total": len(rows)}


# ---------- settings ----------

@router.get("/settings")
def get_settings():
    return {
        "demo_mode": db.get_setting("demo_mode", True),
        "asr_model": db.get_setting("asr_model", ""),
        "llm_model": db.get_setting("llm_model", ""),
        "writing_model": db.get_setting("writing_model", ""),
        "data_dir": str(config.DATA_DIR),
        "version": config.APP_VERSION,
        "sync": scheduler.status(),
        "asr": asr.status(),
        "llm": llm.status(check=False),
        "ocr": ocr.status(check=False),
        "link": link_parser.login_status(),
        "tikhub": {"key_set": tikhub.configured()},
        "dataxapi": {"key_set": dataxapi.configured()},
    }


@router.put("/settings")
def update_settings(payload: dict):
    allowed = {
        "demo_mode", "asr_model", "asr_model_name", "llm_model", "writing_model",
        "llm_base_url", "llm_model_name", "llm_api_key",
        "ocr_base_url", "ocr_model", "ocr_api_key",
        "tikhub_api_key", "dataxapi_api_key",
    }
    for key, value in payload.items():
        if key in allowed:
            db.set_setting(key, value)
    return {"ok": True}
