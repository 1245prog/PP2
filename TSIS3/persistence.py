import json
import os

SETTINGS_DEFAULT = {"sound": True, "car_color": "red", "difficulty": "normal"}


def load_json(path, default):
    if not os.path.exists(path):
        return default.copy()
    with open(path, "r", encoding="utf-8") as f:
        return json.load(f)


def save_json(path, data):
    with open(path, "w", encoding="utf-8") as f:
        json.dump(data, f, indent=2)


def load_settings(path="settings.json"):
    return load_json(path, SETTINGS_DEFAULT)


def save_settings(settings, path="settings.json"):
    save_json(path, settings)


def load_leaderboard(path="leaderboard.json"):
    return load_json(path, [])


def save_score(entry, path="leaderboard.json"):
    scores = load_leaderboard(path)
    scores.append(entry)
    scores.sort(key=lambda x: x["score"], reverse=True)
    save_json(path, scores[:10])
