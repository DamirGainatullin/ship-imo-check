from __future__ import annotations

import hashlib
import sqlite3
from dataclasses import dataclass
from pathlib import Path
from typing import Iterable


@dataclass(frozen=True)
class SearchResult:
    imo: str
    document_path: str
    location: str
    snippet: str


def connect(db_path: Path) -> sqlite3.Connection:
    conn = sqlite3.connect(db_path)
    conn.row_factory = sqlite3.Row
    return conn


def init_db(conn: sqlite3.Connection) -> None:
    conn.executescript(
        """
        CREATE TABLE IF NOT EXISTS documents (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            path TEXT NOT NULL UNIQUE,
            content_hash TEXT NOT NULL,
            indexed_at TEXT NOT NULL
        );

        CREATE TABLE IF NOT EXISTS imo_hits (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            document_id INTEGER NOT NULL,
            imo TEXT NOT NULL,
            location TEXT NOT NULL,
            snippet TEXT NOT NULL,
            FOREIGN KEY(document_id) REFERENCES documents(id) ON DELETE CASCADE
        );

        CREATE INDEX IF NOT EXISTS idx_imo_hits_imo ON imo_hits (imo);
        """
    )
    conn.commit()


def file_hash(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as fh:
        while True:
            chunk = fh.read(1024 * 1024)
            if not chunk:
                break
            digest.update(chunk)
    return digest.hexdigest()


def get_document(conn: sqlite3.Connection, path: str) -> sqlite3.Row | None:
    cur = conn.execute("SELECT * FROM documents WHERE path = ?", (path,))
    return cur.fetchone()


def upsert_document(
    conn: sqlite3.Connection,
    *,
    path: str,
    content_hash: str,
    indexed_at: str,
) -> int:
    existing = get_document(conn, path)
    if existing:
        conn.execute(
            "UPDATE documents SET content_hash = ?, indexed_at = ? WHERE id = ?",
            (content_hash, indexed_at, existing["id"]),
        )
        conn.execute("DELETE FROM imo_hits WHERE document_id = ?", (existing["id"],))
        return int(existing["id"])

    cur = conn.execute(
        "INSERT INTO documents(path, content_hash, indexed_at) VALUES (?, ?, ?)",
        (path, content_hash, indexed_at),
    )
    return int(cur.lastrowid)


def insert_hits(
    conn: sqlite3.Connection,
    *,
    document_id: int,
    hits: Iterable[tuple[str, str, str]],
) -> None:
    conn.executemany(
        """
        INSERT INTO imo_hits(document_id, imo, location, snippet)
        VALUES (?, ?, ?, ?)
        """,
        ((document_id, imo, location, snippet) for imo, location, snippet in hits),
    )


def find_by_imo(conn: sqlite3.Connection, imo: str) -> list[SearchResult]:
    cur = conn.execute(
        """
        SELECT h.imo, d.path as document_path, h.location, h.snippet
        FROM imo_hits h
        JOIN documents d ON d.id = h.document_id
        WHERE h.imo = ?
        ORDER BY d.path, h.location
        """,
        (imo,),
    )
    rows = cur.fetchall()
    return [
        SearchResult(
            imo=row["imo"],
            document_path=row["document_path"],
            location=row["location"],
            snippet=row["snippet"],
        )
        for row in rows
    ]

