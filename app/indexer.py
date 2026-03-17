from __future__ import annotations

import logging
import re
from datetime import datetime, timezone
from pathlib import Path

from app.config import Settings
from app.db import file_hash, init_db, insert_hits, upsert_document, connect, get_document
from app.extractors import extract_text
from app.imo import extract_imos

LOGGER = logging.getLogger(__name__)
SUPPORTED_EXTENSIONS = {".pdf", ".docx", ".doxc"}


def _iter_source_files(root: Path) -> list[Path]:
    files: list[Path] = []
    for path in root.rglob("*"):
        if path.is_file() and path.suffix.lower() in SUPPORTED_EXTENSIONS:
            files.append(path)
    return sorted(files)


def _snippet_from_text(text: str, imo: str, max_len: int = 320) -> str:
    normalized = text.replace("\r", "")
    flattened = re.sub(r"\s+", " ", normalized).strip()
    trailing_imo = f"IMO {imo}"
    if "\n" in normalized and flattened.endswith(trailing_imo):
        trimmed = flattened[: -len(trailing_imo)].rstrip(" ;,.")
        if trimmed:
            return trimmed
    if flattened and len(flattened) <= 2200:
        return flattened

    pos = normalized.find(imo)
    if pos < 0:
        return normalized[:max_len].replace("\n", " ").strip()

    left_block = normalized.rfind("\n\n", 0, pos)
    left_sent = normalized.rfind(".", 0, pos)
    start = max(left_block + 2 if left_block >= 0 else 0, left_sent + 1 if left_sent >= 0 else 0)

    right_block = normalized.find("\n\n", pos)
    right_sent = normalized.find(".", pos)
    candidates = [i for i in (right_block, right_sent) if i >= 0]
    end = min(candidates) + 1 if candidates else len(normalized)

    if end - start < 220:
        start = max(0, pos - 220)
        end = min(len(normalized), pos + len(imo) + 260)

    raw = normalized[start:end]
    snippet = re.sub(r"\s+", " ", raw).strip()

    if len(snippet) > max_len:
        center = snippet.find(imo)
        if center >= 0:
            local_start = max(0, center - 180)
            local_end = min(len(snippet), center + len(imo) + 180)
            snippet = snippet[local_start:local_end].strip()
        if len(snippet) > max_len:
            snippet = snippet[:max_len].rstrip()

    if start > 0:
        snippet = "..." + snippet
    if end < len(normalized):
        snippet = snippet + "..."
    return snippet


def index_sources(settings: Settings, *, force: bool = False) -> None:
    if not settings.sources_dir.exists():
        raise FileNotFoundError(f"Sources directory not found: {settings.sources_dir}")

    files = _iter_source_files(settings.sources_dir)
    if not files:
        LOGGER.warning("No supported files found in %s", settings.sources_dir)
        return

    conn = connect(settings.db_path)
    init_db(conn)
    indexed_docs = 0
    indexed_hits = 0

    for file_path in files:
        abs_path = str(file_path.resolve())
        content_hash = file_hash(file_path)
        existing = get_document(conn, abs_path)
        if not force and existing and existing["content_hash"] == content_hash:
            LOGGER.info("Skip unchanged: %s", file_path.name)
            continue

        LOGGER.info("Indexing: %s", file_path.name)
        document_id = upsert_document(
            conn,
            path=abs_path,
            content_hash=content_hash,
            indexed_at=datetime.now(timezone.utc).isoformat(),
        )

        hits: list[tuple[str, str, str]] = []
        for chunk in extract_text(file_path):
            for imo in extract_imos(chunk.text):
                hits.append((imo, chunk.location, _snippet_from_text(chunk.text, imo)))

        insert_hits(conn, document_id=document_id, hits=hits)
        conn.commit()

        indexed_docs += 1
        indexed_hits += len(hits)
        LOGGER.info("Indexed %s hits in %s", len(hits), file_path.name)

    conn.close()
    LOGGER.info(
        "Indexing finished: %s docs updated, %s hits stored", indexed_docs, indexed_hits
    )
