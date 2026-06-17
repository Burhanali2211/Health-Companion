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
    return plans.get(season, {}).get(age_mode, {}).get(meal_type, [])

def get_meal_types() -> list[str]:
    return ["morning", "afternoon", "evening", "immunity", "avoid"]
