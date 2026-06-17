from datetime import date, datetime
from pathlib import Path
import json
from typing import Optional

_DATA_PATH = Path(__file__).parent / "data" / "seasons.json"

def _load_data() -> dict:
    try:
        return json.loads(_DATA_PATH.read_text(encoding="utf-8"))
    except FileNotFoundError:
        return {"seasons": [], "districts": []}

def get_season_for_date(d: Optional[date] = None) -> dict:
    """Return season dict matching the given date (default: today)."""
    if d is None:
        d = date.today()

    data = _load_data()
    month, day = d.month, d.day

    for season in data["seasons"]:
        if season["wraps_year"]:
            # Chilla Kalan: Dec 21 – Jan 29
            if (month == season["start_month"] and day >= season["start_day"]) or \
               (month == season["end_month"] and day <= season["end_day"]):
                return season
        else:
            sm, sd = season["start_month"], season["start_day"]
            em, ed = season["end_month"], season["end_day"]

            if sm == em:
                if month == sm and sd <= day <= ed:
                    return season
            else:
                if (month == sm and day >= sd) or \
                   (month > sm and month < em) or \
                   (month == em and day <= ed):
                    return season

    # Fallback — should never happen with correct data
    return data["seasons"][0]

def get_day_number_in_season(d: Optional[date] = None) -> int:
    """Return how many days into the current season we are (1-indexed)."""
    if d is None:
        d = date.today()

    season = get_season_for_date(d)
    sm, sd = season["start_month"], season["start_day"]

    if season["wraps_year"] and d.month == 1:
        # Jan portion: days from Dec 21
        dec_start = date(d.year - 1, sm, sd)
        return (d - dec_start).days + 1
    else:
        year = d.year
        try:
            season_start = date(year, sm, sd)
        except ValueError:
            season_start = date(year, sm, sd)
        return (d - season_start).days + 1

def get_district(district_id: str) -> Optional[dict]:
    """Return district dict by id."""
    data = _load_data()
    for dist in data["districts"]:
        if dist["id"] == district_id.lower():
            return dist
    return data["districts"][0]  # Default to Srinagar

def get_all_districts() -> list[dict]:
    return _load_data().get("districts", [])

def get_context(district_id: str = "srinagar", d: Optional[date] = None) -> dict:
    """Full health context for the given district and date."""
    if d is None:
        d = date.today()

    season = get_season_for_date(d)
    district = get_district(district_id)
    day_num = get_day_number_in_season(d)

    cold_factor = district.get("coldFactor", 1.0)
    temp_min = round(season["temp_min_approx"] * cold_factor)
    temp_max = round(season["temp_max_approx"] * cold_factor)

    return {
        "season": season,
        "day_number": day_num,
        "district": district,
        "temp_min": temp_min,
        "temp_max": temp_max,
        "kangri_alert": season.get("kangri_alert", False),
        "outdoor_exercise_safe": season.get("outdoor_exercise_safe", True),
        "timestamp": datetime.now().isoformat()
    }
