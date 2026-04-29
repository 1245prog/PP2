import psycopg2
from config import DB_CONFIG

SCHEMA_SQL = """
CREATE TABLE IF NOT EXISTS players (
    id SERIAL PRIMARY KEY,
    username VARCHAR(50) UNIQUE NOT NULL
);
CREATE TABLE IF NOT EXISTS game_sessions (
    id SERIAL PRIMARY KEY,
    player_id INTEGER REFERENCES players(id),
    score INTEGER NOT NULL,
    level_reached INTEGER NOT NULL,
    played_at TIMESTAMP DEFAULT NOW()
);
"""


def conn():
    return psycopg2.connect(**DB_CONFIG)


def init_db():
    c = conn()
    cur = c.cursor()
    cur.execute(SCHEMA_SQL)
    c.commit()
    cur.close()
    c.close()


def get_or_create_player(username):
    c = conn()
    cur = c.cursor()
    cur.execute("INSERT INTO players(username) VALUES(%s) ON CONFLICT(username) DO NOTHING", (username,))
    cur.execute("SELECT id FROM players WHERE username=%s", (username,))
    pid = cur.fetchone()[0]
    c.commit()
    cur.close()
    c.close()
    return pid


def save_result(username, score, level):
    pid = get_or_create_player(username)
    c = conn()
    cur = c.cursor()
    cur.execute("INSERT INTO game_sessions(player_id, score, level_reached) VALUES(%s,%s,%s)", (pid, score, level))
    c.commit()
    cur.close()
    c.close()


def top10():
    c = conn()
    cur = c.cursor()
    cur.execute("""
        SELECT p.username, g.score, g.level_reached, g.played_at
        FROM game_sessions g
        JOIN players p ON p.id = g.player_id
        ORDER BY g.score DESC
        LIMIT 10
    """)
    rows = cur.fetchall()
    cur.close()
    c.close()
    return rows


def personal_best(username):
    c = conn()
    cur = c.cursor()
    cur.execute("""
        SELECT COALESCE(MAX(g.score), 0)
        FROM game_sessions g
        JOIN players p ON p.id = g.player_id
        WHERE p.username=%s
    """, (username,))
    v = cur.fetchone()[0]
    cur.close()
    c.close()
    return v
