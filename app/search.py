from __future__ import annotations

from app.config import Settings
from app.db import find_by_imo, init_db, connect, SearchResult
from app.imo import normalize_imo, extract_imo_digits


def find_imo(settings: Settings, raw_imo: str) -> list[SearchResult]:
    try:
        # Primary path: strict IMO checksum validation.
        imo = normalize_imo(raw_imo)
    except ValueError as exc:
        # Fallback for data sources (notably EU DOCX) that may contain
        # 7-digit entries in the IMO column without valid checksum.
        if "checksum" in str(exc).lower():
            imo = extract_imo_digits(raw_imo)
        else:
            raise
    conn = connect(settings.db_path)
    init_db(conn)
    try:
        return find_by_imo(conn, imo)
    finally:
        conn.close()
