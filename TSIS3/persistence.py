import json
import os

SETTINGS_FILE = r"C:\Study\PP2\TSIS\TSIS3\settings.json"
LEADERBOARD_FILE = r"C:\Study\PP2\TSIS\TSIS3\leaderboard.json"

DEFAULT_SETTINGS = {
    "sound": True,
    "car_color": "blue",
    "difficulty": "normal"
}


def _ensure_parent_dir(path: str) -> None:
    os.makedirs(os.path.dirname(path), exist_ok=True)


def load_settings():
    if os.path.exists(SETTINGS_FILE):
        try:
            with open(SETTINGS_FILE, "r", encoding="utf-8") as f:
                data = json.load(f)
            settings = DEFAULT_SETTINGS.copy()
            if isinstance(data, dict):
                settings.update(data)
            return settings
        except (json.JSONDecodeError, OSError):
            return DEFAULT_SETTINGS.copy()
    return DEFAULT_SETTINGS.copy()


def save_settings(settings):
    _ensure_parent_dir(SETTINGS_FILE)
    with open(SETTINGS_FILE, "w", encoding="utf-8") as f:
        json.dump(settings, f, indent=4, ensure_ascii=False)


def load_leaderboard():
    if os.path.exists(LEADERBOARD_FILE):
        try:
            with open(LEADERBOARD_FILE, "r", encoding="utf-8") as f:
                data = json.load(f)
            return data if isinstance(data, list) else []
        except (json.JSONDecodeError, OSError):
            return []
    return []


def save_score(name, score, distance, coins):
    board = load_leaderboard()
    board.append({
        "name": str(name),
        "score": int(score),
        "distance": int(distance),
        "coins": int(coins),
    })

    board = sorted(board, key=lambda row: (row["score"], row["distance"]), reverse=True)[:10]

    _ensure_parent_dir(LEADERBOARD_FILE)
    with open(LEADERBOARD_FILE, "w", encoding="utf-8") as f:
        json.dump(board, f, indent=4, ensure_ascii=False)
