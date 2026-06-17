from pathlib import Path
import json
from functools import lru_cache

_DATA = Path(__file__).parent / "data" / "diet_plans.json"

@lru_cache(maxsize=1)
def _load() -> dict:
    try:
        return json.loads(_DATA.read_text(encoding="utf-8"))
    except FileNotFoundError:
        return {}

def get_diet_plan(season: str, age_mode: str, meal_type: str) -> list[dict]:
    plans = _load()
    # Normalize season name: "Grind" → "grind", "Chilla Kalan" → "chilla_kalan"
    normalized_season = season.lower().replace(" ", "_")
    # Normalize meal type: "breakfast" → "morning", "lunch" → "afternoon", etc.
    meal_map = {
        "breakfast": "morning",
        "morning": "morning",
        "lunch": "afternoon",
        "afternoon": "afternoon",
        "dinner": "evening",
        "evening": "evening",
    }
    normalized_meal = meal_map.get(meal_type.lower(), meal_type.lower())
    return plans.get(normalized_season, {}).get(age_mode.lower(), {}).get(normalized_meal, [])

def get_meal_types() -> list[str]:
    return ["morning", "afternoon", "evening", "immunity", "avoid"]
