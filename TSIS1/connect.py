from __future__ import annotations

from pathlib import Path

import psycopg2

from config import DB_CONFIG

BASE_DIR = Path(__file__).resolve().parent
SCHEMA_FILE = BASE_DIR / "schema.sql"
PROCEDURES_FILE = BASE_DIR / "procedures.sql"


def get_connection():
    return psycopg2.connect(**DB_CONFIG)


def initialize_database() -> None:
    with get_connection() as conn:
        with conn.cursor() as cur:
            cur.execute(SCHEMA_FILE.read_text(encoding="utf-8"))
            cur.execute(PROCEDURES_FILE.read_text(encoding="utf-8"))
