from __future__ import annotations

import sqlite3
import json
import logging
from pathlib import Path
from contextlib import contextmanager
from datetime import datetime

logger = logging.getLogger(__name__)

DB_PATH = Path(__file__).resolve().parent.parent / "data.db"


def init_db():
    with get_conn() as conn:
        conn.execute("""
            CREATE TABLE IF NOT EXISTS history (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                job_id TEXT UNIQUE NOT NULL,
                source_lang TEXT NOT NULL,
                target_lang TEXT NOT NULL,
                is_batch INTEGER DEFAULT 0,
                filenames TEXT NOT NULL,
                output_paths TEXT NOT NULL,
                total_lines INTEGER DEFAULT 0,
                completed_lines INTEGER DEFAULT 0,
                device TEXT DEFAULT 'auto',
                device_used TEXT DEFAULT 'cpu',
                num_beams INTEGER DEFAULT 3,
                engine_batch_size INTEGER DEFAULT 8,
                status TEXT DEFAULT 'completed',
                elapsed_seconds REAL DEFAULT 0,
                lines_per_second REAL DEFAULT 0,
                created_at TEXT NOT NULL,
                completed_at TEXT NOT NULL
            )
        """)
    logger.info(f"History DB initialized at {DB_PATH}")


@contextmanager
def get_conn():
    conn = sqlite3.connect(str(DB_PATH))
    conn.row_factory = sqlite3.Row
    try:
        yield conn
        conn.commit()
    finally:
        conn.close()


def save_history(entry: dict):
    with get_conn() as conn:
        conn.execute("""
            INSERT OR REPLACE INTO history
            (job_id, source_lang, target_lang, is_batch, filenames, output_paths,
             total_lines, completed_lines, device, device_used, num_beams,
             engine_batch_size, status, elapsed_seconds, lines_per_second,
             created_at, completed_at)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """, (
            entry["job_id"],
            entry["source_lang"],
            entry["target_lang"],
            entry.get("is_batch", 0),
            entry["filenames"],
            entry["output_paths"],
            entry.get("total_lines", 0),
            entry.get("completed_lines", 0),
            entry.get("device", "auto"),
            entry.get("device_used", "cpu"),
            entry.get("num_beams", 3),
            entry.get("engine_batch_size", 8),
            entry.get("status", "completed"),
            entry.get("elapsed_seconds", 0),
            entry.get("lines_per_second", 0),
            entry["created_at"],
            entry["completed_at"],
        ))
    logger.info(f"History saved: {entry['job_id']}")


def get_history(limit: int = 50) -> list[dict]:
    with get_conn() as conn:
        rows = conn.execute(
            "SELECT * FROM history ORDER BY id DESC LIMIT ?", (limit,)
        ).fetchall()
    return [_row_to_dict(r) for r in rows]


def get_history_entry(job_id: str) -> dict | None:
    with get_conn() as conn:
        row = conn.execute(
            "SELECT * FROM history WHERE job_id = ?", (job_id,)
        ).fetchone()
    return _row_to_dict(row) if row else None


def delete_history(job_id: str) -> bool:
    with get_conn() as conn:
        cursor = conn.execute("DELETE FROM history WHERE job_id = ?", (job_id,))
    deleted = cursor.rowcount > 0
    if deleted:
        logger.info(f"History deleted: {job_id}")
    return deleted


def _row_to_dict(row: sqlite3.Row) -> dict:
    d = dict(row)
    d["filenames"] = json.loads(d["filenames"])
    d["output_paths"] = json.loads(d["output_paths"])
    return d
