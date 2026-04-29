from __future__ import annotations

from datetime import datetime
from typing import Any

import psycopg2
from psycopg2 import Error

from config import DB_CONFIG

SCHEMA_SQL = """
CREATE TABLE IF NOT EXISTS players (
    id       SERIAL PRIMARY KEY,
    username VARCHAR(50) UNIQUE NOT NULL
);

CREATE TABLE IF NOT EXISTS game_sessions (
    id            SERIAL PRIMARY KEY,
    player_id     INTEGER REFERENCES players(id) ON DELETE CASCADE,
    score         INTEGER NOT NULL,
    level_reached INTEGER NOT NULL,
    played_at     TIMESTAMP DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS idx_game_sessions_score ON game_sessions(score DESC);
CREATE INDEX IF NOT EXISTS idx_game_sessions_player_id ON game_sessions(player_id);
"""

def get_connection():
    return psycopg2.connect(**DB_CONFIG)

def init_db() -> bool:
    try:
        with get_connection() as conn:
            with conn.cursor() as cur:
                cur.execute(SCHEMA_SQL)
        return True
    except Error:
        return False

def _get_or_create_player_id(cur, username: str) -> int:
    cur.execute("SELECT id FROM players WHERE username = %s", (username,))
    row = cur.fetchone()
    if row:
        return int(row[0])

    cur.execute(
        """
        INSERT INTO players (username)
        VALUES (%s)
        ON CONFLICT (username)
        DO UPDATE SET username = EXCLUDED.username
        RETURNING id
        """,
        (username,),
    )
    return int(cur.fetchone()[0])

def save_game_session(username: str, score: int, level_reached: int) -> bool:
    try:
        with get_connection() as conn:
            with conn.cursor() as cur:
                player_id = _get_or_create_player_id(cur, username)
                cur.execute(
                    """
                    INSERT INTO game_sessions (player_id, score, level_reached)
                    VALUES (%s, %s, %s)
                    """,
                    (player_id, int(score), int(level_reached)),
                )
        return True
    except Error:
        return False

def get_personal_best(username: str) -> int:
    try:
        with get_connection() as conn:
            with conn.cursor() as cur:
                cur.execute(
                    """
                    SELECT COALESCE(MAX(gs.score), 0)
                    FROM game_sessions gs
                    JOIN players p ON p.id = gs.player_id
                    WHERE p.username = %s
                    """,
                    (username,),
                )
                row = cur.fetchone()
                return int(row[0] or 0)
    except Error:
        return 0

def get_leaderboard(limit: int = 10) -> list[dict[str, Any]]:
    try:
        with get_connection() as conn:
            with conn.cursor() as cur:
                cur.execute(
                    """
                    SELECT
                        p.username,
                        gs.score,
                        gs.level_reached,
                        gs.played_at
                    FROM game_sessions gs
                    JOIN players p ON p.id = gs.player_id
                    ORDER BY gs.score DESC, gs.level_reached DESC, gs.played_at ASC
                    LIMIT %s
                    """,
                    (int(limit),),
                )
                rows = cur.fetchall()

        result: list[dict[str, Any]] = []
        for username, score, level_reached, played_at in rows:
            result.append(
                {
                    "username": username,
                    "score": int(score),
                    "level_reached": int(level_reached),
                    "played_at": played_at if isinstance(played_at, datetime) else played_at,
                }
            )
        return result
    except Error:
        return []
