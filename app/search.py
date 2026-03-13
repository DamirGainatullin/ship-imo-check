from __future__ import annotations

from app.config import Settings
from app.db import find_by_imo, init_db, connect, SearchResult
from app.imo import normalize_imo


def find_imo(settings: Settings, raw_imo: str) -> list[SearchResult]:
    imo = normalize_imo(raw_imo)
    conn = connect(settings.db_path)
    init_db(conn)
    try:
        return find_by_imo(conn, imo)
    finally:
        conn.close()

