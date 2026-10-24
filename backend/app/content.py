import json
from functools import lru_cache

from .config import CONTENT_PATH

LANGUAGES = {
    "ta-IN": {"code": "ta-IN", "name": "Tamil", "native": "தமிழ்"},
    "hi-IN": {"code": "hi-IN", "name": "Hindi", "native": "हिन्दी"},
}


@lru_cache
def library() -> dict:
    with open(CONTENT_PATH, encoding="utf-8") as f:
        return json.load(f)


def level_names() -> dict:
    return {int(k): v for k, v in library()["levels"].items()}


def targets(language: str | None = None) -> list[dict]:
    ts = library()["targets"]
    return [t for t in ts if language is None or t["language"] == language]


def target(target_id: str) -> dict | None:
    return next((t for t in library()["targets"] if t["id"] == target_id), None)


def items(target_id: str, level: int) -> list[dict]:
    t = target(target_id)
    return t["items"].get(str(level), []) if t else []


def find_item(target_id: str, text: str) -> tuple[int, dict] | None:
    t = target(target_id)
    if not t:
        return None
    for level, its in t["items"].items():
        for it in its:
            if it["text"] == text:
                return int(level), it
    return None


def baseline_items(language: str) -> list[dict]:
    """Two short words per target: enough to rank targets without a long test."""
    out = []
    for t in targets(language):
        for it in t["items"]["2"][:2]:
            out.append({"speech_target_id": t["id"], "level": 2, **it})
    return out
