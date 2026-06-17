from pathlib import Path
import json
from functools import lru_cache

_DATA = Path(__file__).parent / "data" / "exercises.json"

@lru_cache(maxsize=1)
def _load() -> dict:
    try:
        return json.loads(_DATA.read_text(encoding="utf-8"))
    except FileNotFoundError:
        return {}

def _normalize_season(season: str) -> str:
    """Normalize season name: "Grind" → "grind", "Chilla Kalan" → "chilla_kalan"."""
    return season.lower().replace(" ", "_")

def get_season_lock(season: str) -> dict:
    lib = _load()
    normalized = _normalize_season(season)
    return lib.get("season_locks", {}).get(normalized, {"outdoor": True})

def get_exercises(season: str, age_mode: str, exercise_type: str) -> list[dict] | None:
    """Returns None when outdoor is locked for this season."""
    if exercise_type == "outdoor":
        lock = get_season_lock(season)
        if not lock.get("outdoor", True):
            return None   # caller renders the lock overlay

    lib = _load()
    normalized_season = _normalize_season(season)
    return lib.get(normalized_season, {}).get(age_mode.lower(), {}).get(exercise_type.lower(), [])

def get_exercise_types() -> list[str]:
    return ["indoor", "outdoor", "breathing", "morning"]
