#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""CLI backend for /webnovel-study deterministic steps."""

from __future__ import annotations

import argparse
import json
import math
import re
import sys
import zipfile
from datetime import datetime, timezone
from html import unescape
from pathlib import Path, PurePosixPath
from typing import Any
import xml.etree.ElementTree as ET

from runtime_compat import enable_windows_utf8_stdio
from security_utils import atomic_write_json, read_json_safe, sanitize_filename

from .config import DataModulesConfig

SUPPORTED_FORMATS = {"txt", "md", "epub", "pdf"}
MODE_REQUIRED_REPORTS = {
    "full": [
        "00_总览.md",
        "01_剧情结构.md",
        "02_人物特点.md",
        "03_文笔风格.md",
        "04_常用词句.md",
        "05_章节节奏.json",
        "06_可复用模式.json",
    ],
    "plot": ["00_总览.md", "01_剧情结构.md", "05_章节节奏.json", "06_可复用模式.json"],
    "characters": ["00_总览.md", "02_人物特点.md", "06_可复用模式.json"],
    "style": ["00_总览.md", "03_文笔风格.md", "04_常用词句.md", "06_可复用模式.json"],
    "phrases": ["00_总览.md", "04_常用词句.md", "06_可复用模式.json"],
    "pacing": ["00_总览.md", "01_剧情结构.md", "05_章节节奏.json", "06_可复用模式.json"],
}
ALWAYS_REQUIRED_CACHE = [
    "chapter_index.json",
    "chapter_source.jsonl",
    "chapter_analysis.jsonl",
    "study_meta.json",
]
NUM_TOKEN = "0-9零一二三四五六七八九十百千万两〇○壹贰叁肆伍陆柒捌玖拾"
CHAPTER_LINE_RE = re.compile(
    rf"^(?:第[{NUM_TOKEN}]+[章节回集部篇][^\n]{{0,80}}|Chapter\s+\d+[^\n]{{0,80}}|序章[^\n]{{0,80}}|楔子[^\n]{{0,80}}|引子[^\n]{{0,80}})$",
    re.IGNORECASE,
)
VOLUME_LINE_RE = re.compile(rf"^(?:第[{NUM_TOKEN}]+卷[^\n]{{0,80}}|卷[{NUM_TOKEN}][^\n]{{0,80}})$")
SINGLE_CHAPTER_RE = re.compile(rf"^第(?P<num>[{NUM_TOKEN}]+)[章节回集部篇](?![\d\-~至到])")
PUNCT_ONLY_RE = re.compile(r"[\s\W_]+", re.UNICODE)


class StudyCommandError(RuntimeError):
    pass


def _json_dump(data: Any) -> str:
    return json.dumps(data, ensure_ascii=False, indent=2)


def _print_json(data: Any) -> None:
    print(_json_dump(data))


def _now_utc() -> str:
    return datetime.now(timezone.utc).replace(microsecond=0).isoformat().replace("+00:00", "Z")


def _today_local() -> str:
    return datetime.now().strftime("%Y-%m-%d")


def _make_book_safe(name: str) -> str:
    safe = sanitize_filename(name or "").replace("_", "-")
    safe = re.sub(r"-+", "-", safe).strip("-")
    if not safe or safe.startswith("."):
        safe = f"study-{safe or 'book'}"
    return safe


def _normalize_text(text: str) -> str:
    text = text.replace("\ufeff", "")
    text = text.replace("\r\n", "\n").replace("\r", "\n")
    text = text.replace("\xa0", " ").replace("\u3000", " ")
    text = text.replace("\x00", "")
    text = re.sub(r"[ \t]+\n", "\n", text)
    text = re.sub(r"\n{3,}", "\n\n", text)
    return text.strip()


def _strip_html(html_text: str) -> str:
    html_text = re.sub(r"(?is)<(script|style).*?>.*?</\1>", " ", html_text)
    html_text = re.sub(r"(?is)<!--.*?-->", " ", html_text)
    html_text = re.sub(r"(?i)<br\s*/?>", "\n", html_text)
    html_text = re.sub(r"(?i)</p>", "\n", html_text)
    html_text = re.sub(r"(?i)</div>", "\n", html_text)
    html_text = re.sub(r"(?i)</h[1-6]>", "\n", html_text)
    html_text = re.sub(r"(?s)<[^>]+>", " ", html_text)
    return _normalize_text(unescape(html_text))


def _clean_heading(line: str) -> str:
    line = line.strip()
    line = re.sub(r"^[#>*\-\d\.\)\(\s]+", "", line)
    return _normalize_text(line)


def _first_nonempty_line(text: str) -> str:
    for line in text.splitlines():
        candidate = _clean_heading(line)
        if candidate:
            return candidate
    return ""


def _is_private_use(ch: str) -> bool:
    code = ord(ch)
    return 0xE000 <= code <= 0xF8FF


def _text_stats(text: str) -> dict[str, Any]:
    visible_chars = [ch for ch in text if not ch.isspace()]
    visible = len(visible_chars)
    cjk = sum(1 for ch in visible_chars if "\u4e00" <= ch <= "\u9fff")
    pua = sum(1 for ch in visible_chars if _is_private_use(ch))
    ascii_letters = sum(1 for ch in visible_chars if ch.isascii() and ch.isalpha())
    digits = sum(1 for ch in visible_chars if ch.isdigit())
    return {
        "visible_chars": visible,
        "cjk_chars": cjk,
        "private_use_chars": pua,
        "ascii_letters": ascii_letters,
        "digits": digits,
        "cjk_ratio": round(cjk / visible, 4) if visible else 0.0,
        "private_use_ratio": round(pua / visible, 4) if visible else 0.0,
    }


def _readable_excerpt(text: str, limit: int = 1200) -> str:
    filtered = "".join(ch for ch in text if not _is_private_use(ch))
    filtered = _normalize_text(filtered)
    if len(filtered) <= limit:
        return filtered
    return filtered[:limit].rstrip() + "..."


def _detect_obfuscation(stats: dict[str, Any]) -> bool:
    visible = int(stats.get("visible_chars") or 0)
    if visible < 40:
        return False
    pua_ratio = float(stats.get("private_use_ratio") or 0.0)
    cjk_ratio = float(stats.get("cjk_ratio") or 0.0)
    if pua_ratio >= 0.08:
        return True
    return pua_ratio >= 0.03 and cjk_ratio <= 0.12


def _structure_quality(title: str, excerpt: str, obfuscated: bool) -> str:
    if title and not obfuscated and len(excerpt) >= 120:
        return "A"
    if title:
        return "B"
    if excerpt:
        return "C"
    return "D"


def _confidence_from_quality(quality: str) -> str:
    return {"A": "high", "B": "medium", "C": "low", "D": "low"}.get(quality, "low")


def _batch_count(chapter_count: int) -> int:
    if chapter_count <= 0:
        return 0
    if chapter_count <= 80:
        return 1
    batch_size = 25 if chapter_count <= 200 else 30
    return max(1, math.ceil(chapter_count / batch_size))


def _extract_single_chapter_number(evidence_range: str) -> int:
    value = (evidence_range or "").strip()
    if any(token in value for token in ("-", "~", "至", "到", "、", ",")):
        return 0
    match = SINGLE_CHAPTER_RE.match(value)
    if match:
        digits = re.sub(r"\D", "", match.group("num"))
        return int(digits) if digits else 0
    return 0


def _normalize_pattern_description(text: str) -> str:
    return PUNCT_ONLY_RE.sub("", text or "").lower()


def _pattern_to_memory_entry(pattern: dict[str, Any]) -> dict[str, Any]:
    parts = [
        str(pattern.get("name") or "").strip(),
        str(pattern.get("description") or "").strip(),
        str(pattern.get("transfer_rule") or "").strip(),
        str(pattern.get("adaptation_note") or "").strip(),
    ]
    parts = [part for part in parts if part]
    description = "；".join(parts)
    return {
        "pattern_type": str(pattern.get("pattern_type") or "hook").strip() or "hook",
        "description": description,
        "source_chapter": _extract_single_chapter_number(str(pattern.get("evidence_range") or "")),
        "learned_at": _now_utc(),
    }


def _write_jsonl(path: Path, records: list[dict[str, Any]]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    content = ""
    if records:
        content = "\n".join(json.dumps(record, ensure_ascii=False) for record in records) + "\n"
    path.write_text(content, encoding="utf-8")


def _touch_file(path: Path) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    if not path.exists():
        path.write_text("", encoding="utf-8")


def _parse_range(range_spec: str, chapter_count: int) -> tuple[int, int]:
    if chapter_count <= 0:
        return (0, 0)
    value = (range_spec or "all").strip().lower()
    if value == "all":
        return (1, chapter_count)
    front_match = re.fullmatch(r"front(\d+)", value)
    if front_match:
        end = min(chapter_count, int(front_match.group(1)))
        return (1, max(1, end))
    interval_match = re.fullmatch(r"(\d+)-(\d+)", value)
    if interval_match:
        start = max(1, int(interval_match.group(1)))
        end = min(chapter_count, int(interval_match.group(2)))
        if start > end:
            raise StudyCommandError(f"无效 range: {range_spec}")
        return (start, end)
    raise StudyCommandError(f"不支持的 range: {range_spec}")


def _apply_range(chapters: list[dict[str, Any]], range_spec: str) -> list[dict[str, Any]]:
    start, end = _parse_range(range_spec, len(chapters))
    if start == 0 and end == 0:
        return []
    return [chapter for chapter in chapters if start <= int(chapter["chapter_number"]) <= end]


def _finalize_chapter_record(
    *,
    chapter_number: int,
    volume: str,
    chapter_title: str,
    raw_text: str,
    start_offset: int,
    end_offset: int,
    source_ref: str,
    valid: bool = True,
    heuristic: bool = False,
) -> dict[str, Any]:
    normalized_raw = _normalize_text(raw_text)
    excerpt = _readable_excerpt(normalized_raw)
    stats = _text_stats(normalized_raw)
    obfuscated = _detect_obfuscation(stats)
    quality = _structure_quality(chapter_title, excerpt, obfuscated)
    evidence_basis = ["title"]
    if excerpt:
        evidence_basis.append("excerpt")
    return {
        "chapter_number": chapter_number,
        "volume": volume,
        "chapter_title": chapter_title,
        "start_offset": start_offset,
        "end_offset": end_offset,
        "valid": valid,
        "quality": quality,
        "source_ref": source_ref,
        "content_excerpt": excerpt,
        "confidence": _confidence_from_quality(quality),
        "evidence_basis": evidence_basis,
        "obfuscation_detected": obfuscated,
        "text_stats": stats,
        "heuristic": heuristic,
    }


def _extract_plain_text_chapters(text: str) -> tuple[list[dict[str, Any]], list[str]]:
    warnings: list[str] = []
    normalized = _normalize_text(text)
    if not normalized:
        return [], ["源文本为空"]

    lines = normalized.split("\n")
    chapters: list[dict[str, Any]] = []
    current_title = ""
    current_volume = ""
    current_lines: list[str] = []
    current_start = 0
    offset = 0

    def flush(current_number: int, current_end: int) -> None:
        nonlocal current_title, current_volume, current_lines, current_start
        if not current_title:
            return
        record = _finalize_chapter_record(
            chapter_number=current_number,
            volume=current_volume,
            chapter_title=current_title,
            raw_text="\n".join(current_lines),
            start_offset=current_start,
            end_offset=current_end,
            source_ref="plain-text",
        )
        chapters.append(record)
        current_title = ""
        current_lines = []

    for line in lines:
        candidate = _clean_heading(line)
        line_len = len(line) + 1
        if candidate and VOLUME_LINE_RE.match(candidate):
            current_volume = candidate
            offset += line_len
            continue
        if candidate and CHAPTER_LINE_RE.match(candidate):
            flush(len(chapters) + 1, max(current_start, offset - 1))
            current_title = candidate
            current_start = offset
            current_lines = []
            offset += line_len
            continue
        if current_title:
            current_lines.append(line)
        offset += line_len

    flush(len(chapters) + 1, max(current_start, len(normalized)))

    if chapters:
        return chapters, warnings

    warnings.append("未识别稳定章标，已降级为前段研究版")
    fallback_excerpt = normalized[:6000]
    fallback = _finalize_chapter_record(
        chapter_number=1,
        volume="",
        chapter_title="开篇研究块 1",
        raw_text=fallback_excerpt,
        start_offset=0,
        end_offset=len(fallback_excerpt),
        source_ref="plain-text",
        heuristic=True,
    )
    return [fallback], warnings


def _read_zip_text(zf: zipfile.ZipFile, path: PurePosixPath) -> str:
    candidates = [path.as_posix(), path.as_posix().lstrip("/")]
    last_error: Exception | None = None
    for candidate in candidates:
        try:
            return zf.read(candidate).decode("utf-8", errors="ignore")
        except Exception as exc:  # pragma: no cover - best effort fallback
            last_error = exc
    if last_error is not None:
        raise last_error
    raise KeyError(path.as_posix())


def _read_epub_container_rootfile(zf: zipfile.ZipFile) -> PurePosixPath:
    raw = zf.read("META-INF/container.xml")
    root = ET.fromstring(raw)
    for elem in root.iter():
        if elem.tag.endswith("rootfile"):
            full_path = elem.attrib.get("full-path")
            if full_path:
                return PurePosixPath(full_path)
    raise StudyCommandError("EPUB 缺少 OPF rootfile")


def _extract_opf_title(opf_root: ET.Element) -> str:
    for elem in opf_root.iter():
        if elem.tag.endswith("title") and (elem.text or "").strip():
            return _normalize_text(elem.text or "")
    return ""


def _extract_html_title(html_text: str, plain_text: str) -> str:
    for pattern in (
        r"(?is)<h1[^>]*>(.*?)</h1>",
        r"(?is)<h2[^>]*>(.*?)</h2>",
        r"(?is)<title[^>]*>(.*?)</title>",
    ):
        match = re.search(pattern, html_text)
        if match:
            candidate = _strip_html(match.group(1))
            if candidate:
                return _clean_heading(candidate)
    return _first_nonempty_line(plain_text)


def _extract_epub_chapters(source_path: Path) -> tuple[str, list[dict[str, Any]], list[str], bool]:
    warnings: list[str] = []
    chapters: list[dict[str, Any]] = []
    obfuscation_detected = False
    current_volume = ""

    with zipfile.ZipFile(source_path) as zf:
        opf_path = _read_epub_container_rootfile(zf)
        opf_root = ET.fromstring(zf.read(opf_path.as_posix()))
        book_title = _extract_opf_title(opf_root) or source_path.stem

        manifest: dict[str, dict[str, str]] = {}
        spine_ids: list[str] = []
        for elem in opf_root.iter():
            if elem.tag.endswith("item"):
                manifest_id = elem.attrib.get("id")
                if manifest_id:
                    manifest[manifest_id] = {
                        "href": elem.attrib.get("href", ""),
                        "media_type": elem.attrib.get("media-type", ""),
                    }
            elif elem.tag.endswith("itemref"):
                idref = elem.attrib.get("idref")
                if idref:
                    spine_ids.append(idref)

        base_dir = opf_path.parent
        for idref in spine_ids:
            item = manifest.get(idref)
            if not item:
                continue
            href = item.get("href", "")
            media_type = (item.get("media_type", "") or "").lower()
            if not href:
                continue
            lower_href = href.lower()
            if "html" not in media_type and not lower_href.endswith((".xhtml", ".html", ".htm")):
                continue

            file_path = base_dir / PurePosixPath(href)
            try:
                html_text = _read_zip_text(zf, file_path)
            except Exception:
                warnings.append(f"EPUB 章节读取失败: {file_path.as_posix()}")
                continue

            plain_text = _strip_html(html_text)
            title = _extract_html_title(html_text, plain_text)
            if title and VOLUME_LINE_RE.match(title):
                current_volume = title
                continue

            chapter_like_href = bool(re.search(r"chapter[_\-]?\d+|chap[_\-]?\d+", lower_href))
            valid = bool(title and CHAPTER_LINE_RE.match(title)) or chapter_like_href
            if not valid:
                continue
            if not title:
                title = f"章节 {len(chapters) + 1}"

            record = _finalize_chapter_record(
                chapter_number=len(chapters) + 1,
                volume=current_volume,
                chapter_title=title,
                raw_text=plain_text,
                start_offset=0,
                end_offset=0,
                source_ref=file_path.as_posix(),
            )
            obfuscation_detected = obfuscation_detected or bool(record["obfuscation_detected"])
            chapters.append(record)

        if not chapters:
            warnings.append("EPUB 未识别到稳定章节，无法建立可靠章索引")

        return book_title, chapters, warnings, obfuscation_detected


def _extract_pdf_text(source_path: Path) -> str:
    try:
        from pypdf import PdfReader  # type: ignore
    except Exception as exc:  # pragma: no cover - optional dependency
        raise StudyCommandError("PDF 仅在已安装 pypdf 且文本层可读时支持") from exc

    reader = PdfReader(str(source_path))
    chunks: list[str] = []
    for page in reader.pages:
        chunks.append(page.extract_text() or "")
    return _normalize_text("\n".join(chunks))


def _load_source(source_path: Path) -> dict[str, Any]:
    source_format = source_path.suffix.lower().lstrip(".")
    if source_format not in SUPPORTED_FORMATS:
        raise StudyCommandError(f"暂不支持的样书格式: .{source_format}")

    if source_format in {"txt", "md"}:
        book_title = source_path.stem
        text = source_path.read_text(encoding="utf-8", errors="ignore")
        chapters, warnings = _extract_plain_text_chapters(text)
        return {
            "book_title": book_title,
            "chapters": chapters,
            "warnings": warnings,
            "obfuscation_detected": any(ch.get("obfuscation_detected") for ch in chapters),
            "source_format": source_format,
        }

    if source_format == "pdf":
        text = _extract_pdf_text(source_path)
        chapters, warnings = _extract_plain_text_chapters(text)
        return {
            "book_title": source_path.stem,
            "chapters": chapters,
            "warnings": warnings,
            "obfuscation_detected": any(ch.get("obfuscation_detected") for ch in chapters),
            "source_format": source_format,
        }

    book_title, chapters, warnings, obfuscation_detected = _extract_epub_chapters(source_path)
    return {
        "book_title": book_title,
        "chapters": chapters,
        "warnings": warnings,
        "obfuscation_detected": obfuscation_detected,
        "source_format": source_format,
    }


def _determine_analysis_mode(chapters: list[dict[str, Any]], obfuscation_detected: bool) -> tuple[str, str, list[str]]:
    warnings: list[str] = []
    if not chapters:
        warnings.append("未建立可用章索引，已阻断整本分析")
        return "blocked", "D", warnings

    heuristic_only = all(bool(ch.get("heuristic")) for ch in chapters)
    if heuristic_only:
        warnings.append("未识别稳定章标，仅能做开篇研究或结构级分析")
        return "degraded_structure_only", "C", warnings

    if obfuscation_detected:
        warnings.append("检测到正文存在私有码或异常字符，已降级为结构级分析")
        return "degraded_structure_only", "B", warnings

    low_quality = sum(1 for chapter in chapters if chapter.get("quality") in {"C", "D"})
    if low_quality and low_quality >= max(1, len(chapters) // 3):
        warnings.append("可读正文比例偏低，建议以结构分析为主")
        return "degraded_structure_only", "C", warnings

    quality_order = {"A": 4, "B": 3, "C": 2, "D": 1}
    min_quality = min((quality_order.get(str(ch.get("quality") or "D"), 1) for ch in chapters), default=1)
    overall_quality = {4: "A", 3: "B", 2: "C", 1: "D"}[min_quality]
    return "full_text", overall_quality, warnings


def _build_study_meta(
    *,
    source_path: Path,
    source_format: str,
    book_title: str,
    book_safe: str,
    all_chapters: list[dict[str, Any]],
    selected_chapters: list[dict[str, Any]],
    mode: str,
    range_spec: str,
    compare_current: bool,
    write_memory: bool,
    analysis_mode: str,
    text_quality: str,
    obfuscation_detected: bool,
    warnings: list[str],
    report_root: Path,
    cache_root: Path,
) -> dict[str, Any]:
    analysis_basis = ["章节标题", "结构化源数据缓存"]
    if analysis_mode == "full_text":
        analysis_basis.insert(1, "可读正文片段")
    else:
        analysis_basis.insert(1, "可读简介/正文片段（若可用）")

    return {
        "source_path": str(source_path),
        "source_format": source_format,
        "book_title": book_title,
        "book_safe": book_safe,
        "chapter_count": len(all_chapters),
        "selected_chapter_count": len(selected_chapters),
        "mode": mode,
        "range": range_spec,
        "batch_count": _batch_count(len(selected_chapters)),
        "text_quality": text_quality,
        "analysis_mode": analysis_mode,
        "obfuscation_detected": obfuscation_detected,
        "compare_current": compare_current,
        "write_memory": write_memory,
        "warnings": warnings,
        "generated_at": _today_local(),
        "analysis_basis": analysis_basis,
        "report_root": str(report_root),
        "cache_root": str(cache_root),
    }


def _prepare_command(args: argparse.Namespace) -> int:
    config = DataModulesConfig.from_project_root(args.project_root)
    config.ensure_dirs()

    source_path = Path(args.source_path).expanduser().resolve()
    if not source_path.is_file():
        raise StudyCommandError(f"样书不存在: {source_path}")

    loaded = _load_source(source_path)
    all_chapters = loaded["chapters"]
    selected_chapters = _apply_range(all_chapters, args.range)
    obfuscation_detected = bool(loaded["obfuscation_detected"])
    analysis_mode, text_quality, mode_warnings = _determine_analysis_mode(all_chapters, obfuscation_detected)
    warnings = list(dict.fromkeys([*loaded["warnings"], *mode_warnings]))

    book_title = str(loaded["book_title"] or source_path.stem).strip() or source_path.stem
    book_safe = args.book_safe or _make_book_safe(book_title)
    report_root = config.project_root / "参考拆书" / book_safe
    cache_root = config.webnovel_dir / "study_cache" / book_safe
    report_root.mkdir(parents=True, exist_ok=True)
    cache_root.mkdir(parents=True, exist_ok=True)

    chapter_index = [
        {
            "chapter_number": chapter["chapter_number"],
            "volume": chapter.get("volume", ""),
            "chapter_title": chapter["chapter_title"],
            "start_offset": chapter["start_offset"],
            "end_offset": chapter["end_offset"],
            "valid": chapter["valid"],
            "quality": chapter["quality"],
            "source_ref": chapter.get("source_ref", ""),
        }
        for chapter in all_chapters
    ]
    chapter_source = [
        {
            "chapter_number": chapter["chapter_number"],
            "volume": chapter.get("volume", ""),
            "chapter_title": chapter["chapter_title"],
            "content_excerpt": chapter.get("content_excerpt", ""),
            "source_ref": chapter.get("source_ref", ""),
            "quality": chapter["quality"],
            "confidence": chapter.get("confidence", "medium"),
            "evidence_basis": chapter.get("evidence_basis", ["title"]),
            "obfuscation_detected": bool(chapter.get("obfuscation_detected")),
            "text_stats": chapter.get("text_stats", {}),
        }
        for chapter in selected_chapters
    ]

    meta = _build_study_meta(
        source_path=source_path,
        source_format=str(loaded["source_format"]),
        book_title=book_title,
        book_safe=book_safe,
        all_chapters=all_chapters,
        selected_chapters=selected_chapters,
        mode=args.mode,
        range_spec=args.range,
        compare_current=bool(args.compare_current),
        write_memory=bool(args.write_memory),
        analysis_mode=analysis_mode,
        text_quality=text_quality,
        obfuscation_detected=obfuscation_detected,
        warnings=warnings,
        report_root=report_root,
        cache_root=cache_root,
    )

    atomic_write_json(cache_root / "chapter_index.json", chapter_index, backup=False)
    _write_jsonl(cache_root / "chapter_source.jsonl", chapter_source)
    _touch_file(cache_root / "chapter_analysis.jsonl")
    atomic_write_json(cache_root / "study_meta.json", meta, backup=False)

    result = {
        "status": "blocked" if analysis_mode == "blocked" else "success",
        "book_title": book_title,
        "book_safe": book_safe,
        "report_root": str(report_root),
        "cache_root": str(cache_root),
        "chapter_count": len(all_chapters),
        "selected_chapter_count": len(selected_chapters),
        "text_quality": text_quality,
        "analysis_mode": analysis_mode,
        "obfuscation_detected": obfuscation_detected,
        "warnings": warnings,
    }
    _print_json(result)
    return 1 if analysis_mode == "blocked" else 0


def _bridge_memory_command(args: argparse.Namespace) -> int:
    config = DataModulesConfig.from_project_root(args.project_root)
    report_path = config.project_root / "参考拆书" / args.book_safe / "06_可复用模式.json"
    cache_root = config.webnovel_dir / "study_cache" / args.book_safe
    meta_path = cache_root / "study_meta.json"

    if not report_path.is_file():
        raise StudyCommandError(f"未找到模式文件: {report_path}")

    payload = read_json_safe(report_path, {})
    patterns = list(payload.get("patterns") or [])
    eligible = [
        pattern for pattern in patterns
        if int(pattern.get("score") or 0) >= args.min_score
        and str(pattern.get("learnability") or "") != "不建议学"
    ]
    eligible.sort(key=lambda item: int(item.get("score") or 0), reverse=True)
    selected = eligible[: args.limit]

    memory_path = config.webnovel_dir / "project_memory.json"
    existing = read_json_safe(memory_path, {"patterns": []})
    existing_patterns = list(existing.get("patterns") or [])
    seen = {
        (
            str(item.get("pattern_type") or ""),
            _normalize_pattern_description(str(item.get("description") or "")),
        )
        for item in existing_patterns
    }

    appended: list[dict[str, Any]] = []
    for pattern in selected:
        memory_entry = _pattern_to_memory_entry(pattern)
        key = (
            str(memory_entry.get("pattern_type") or ""),
            _normalize_pattern_description(str(memory_entry.get("description") or "")),
        )
        if key in seen or not memory_entry["description"]:
            continue
        seen.add(key)
        existing_patterns.append(memory_entry)
        appended.append(memory_entry)

    existing["patterns"] = existing_patterns
    atomic_write_json(memory_path, existing)

    meta = read_json_safe(meta_path, {})
    if meta:
        meta["write_memory"] = True
        meta["memory_bridge_at"] = _now_utc()
        meta["memory_bridge_count"] = len(appended)
        meta["memory_bridge_status"] = "success"
        atomic_write_json(meta_path, meta, backup=False)

    _print_json(
        {
            "status": "success",
            "book_safe": args.book_safe,
            "memory_file": str(memory_path),
            "selected_patterns": len(selected),
            "appended_patterns": len(appended),
            "skipped_patterns": max(0, len(selected) - len(appended)),
        }
    )
    return 0


def _verify_command(args: argparse.Namespace) -> int:
    config = DataModulesConfig.from_project_root(args.project_root)
    report_root = config.project_root / "参考拆书" / args.book_safe
    cache_root = config.webnovel_dir / "study_cache" / args.book_safe
    meta_path = cache_root / "study_meta.json"
    meta = read_json_safe(meta_path, {})

    required_reports = list(MODE_REQUIRED_REPORTS[args.mode])
    if args.compare_current:
        required_reports.append("07_对当前项目建议.md")

    missing_reports = [name for name in required_reports if not (report_root / name).is_file()]
    missing_cache = [name for name in ALWAYS_REQUIRED_CACHE if not (cache_root / name).is_file()]
    missing_meta_fields = [
        field
        for field in [
            "source_path",
            "source_format",
            "book_title",
            "book_safe",
            "chapter_count",
            "mode",
            "range",
            "text_quality",
            "analysis_mode",
            "obfuscation_detected",
            "generated_at",
        ]
        if field not in meta
    ]

    mismatches: list[str] = []
    if meta:
        if str(meta.get("mode")) != args.mode:
            mismatches.append(f"mode={meta.get('mode')} (expected {args.mode})")
        if bool(meta.get("compare_current")) != bool(args.compare_current):
            mismatches.append(
                f"compare_current={meta.get('compare_current')} (expected {bool(args.compare_current)})"
            )
        if bool(meta.get("write_memory")) != bool(args.write_memory):
            mismatches.append(f"write_memory={meta.get('write_memory')} (expected {bool(args.write_memory)})")

    memory_ok = True
    if args.write_memory:
        memory_path = config.webnovel_dir / "project_memory.json"
        memory_ok = memory_path.is_file() and bool(read_json_safe(memory_path, {}).get("patterns") is not None)
        if meta and str(meta.get("memory_bridge_status") or "") != "success":
            mismatches.append("memory_bridge_status missing or not success")

    ok = not missing_reports and not missing_cache and not missing_meta_fields and not mismatches and memory_ok
    result = {
        "status": "success" if ok else "missing",
        "book_safe": args.book_safe,
        "report_root": str(report_root),
        "cache_root": str(cache_root),
        "missing_reports": missing_reports,
        "missing_cache": missing_cache,
        "missing_meta_fields": missing_meta_fields,
        "meta_mismatches": mismatches,
        "memory_ok": memory_ok,
    }
    _print_json(result)
    return 0 if ok else 1


def main() -> None:
    parser = argparse.ArgumentParser(description="webnovel study manager")
    parser.add_argument("--project-root", required=True, help="书项目根目录")
    sub = parser.add_subparsers(dest="command", required=True)

    prepare = sub.add_parser("prepare", help="准备 study 缓存与源数据")
    prepare.add_argument("source_path", help="样书路径")
    prepare.add_argument("--mode", choices=sorted(MODE_REQUIRED_REPORTS.keys()), default="full")
    prepare.add_argument("--range", default="all", help="分析范围，如 all/front10/1-20")
    prepare.add_argument("--compare-current", action="store_true", help="后续需要对比当前项目")
    prepare.add_argument("--write-memory", action="store_true", help="后续需要桥接写入 project memory")
    prepare.add_argument("--book-safe", help="可选，覆盖自动生成的 book_safe")
    prepare.set_defaults(func=_prepare_command)

    bridge = sub.add_parser("bridge-memory", help="把高分模式写入 project_memory.json")
    bridge.add_argument("--book-safe", required=True)
    bridge.add_argument("--limit", type=int, default=10)
    bridge.add_argument("--min-score", type=int, default=8)
    bridge.set_defaults(func=_bridge_memory_command)

    verify = sub.add_parser("verify", help="核验 study 产物是否齐全")
    verify.add_argument("--book-safe", required=True)
    verify.add_argument("--mode", choices=sorted(MODE_REQUIRED_REPORTS.keys()), default="full")
    verify.add_argument("--compare-current", action="store_true")
    verify.add_argument("--write-memory", action="store_true")
    verify.set_defaults(func=_verify_command)

    args = parser.parse_args()
    try:
        code = int(args.func(args) or 0)
    except StudyCommandError as exc:
        _print_json({"status": "error", "error": str(exc)})
        code = 1
    raise SystemExit(code)


if __name__ == "__main__":
    enable_windows_utf8_stdio(skip_in_pytest=True)
    main()
