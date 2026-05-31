"""Birth chart tool — computes Vedic (sidereal/Lahiri) kundli via Kerykeion."""
from functools import lru_cache
from langchain_core.tools import tool

# Safe ephemeris bounds for realistic birth dates (well within Swiss Ephemeris range).
_MIN_YEAR = 1800
_MAX_YEAR = 2200

NAKSHATRAS = [
    "Ashwini", "Bharani", "Krittika", "Rohini", "Mrigashira", "Ardra",
    "Punarvasu", "Pushya", "Ashlesha", "Magha", "Purva Phalguni", "Uttara Phalguni",
    "Hasta", "Chitra", "Swati", "Vishakha", "Anuradha", "Jyeshtha",
    "Mula", "Purva Ashadha", "Uttara Ashadha", "Shravana", "Dhanishta",
    "Shatabhisha", "Purva Bhadrapada", "Uttara Bhadrapada", "Revati",
]


def _nakshatra(abs_lon_deg: float) -> dict:
    """Derive nakshatra name and pada from sidereal moon longitude."""
    seg = 360.0 / 27
    i = int(abs_lon_deg // seg) % 27
    pada = int((abs_lon_deg % seg) // (seg / 4)) + 1
    return {"name": NAKSHATRAS[i], "pada": pada}


def _planet_dict(obj, include_nakshatra: bool = False) -> dict:
    """Build a planet dict from a Kerykeion astronomical object."""
    d = {
        "sign": obj.sign,
        "abs_pos": obj.abs_pos,
    }
    if include_nakshatra:
        d["nakshatra"] = _nakshatra(obj.abs_pos)
    return d


@lru_cache(maxsize=128)
def _compute_chart(
    year: int, month: int, day: int,
    hour: int, minute: int,
    lat: float, lng: float, tz: str,
) -> dict:
    """Cached raw chart computation via Kerykeion.

    The tool wrapper below adds metadata (time_known, unknown-time handling,
    date validation) but the heavy ephemeris work is cached here.
    """
    from agent.tools._ephemeris import build_subject

    # Name "Natal" (not "User") so the subject is shared with the SVG render path,
    # which also builds a "Natal" subject. compute_birth_chart never exposes the name.
    s = build_subject("Natal", year, month, day, hour, minute, lat, lng, tz)

    chart = {
        "ayanamsa": s.ayanamsa_value,
        "moon": _planet_dict(s.moon, include_nakshatra=True),
        "sun": _planet_dict(s.sun),
        "mercury": _planet_dict(s.mercury),
        "venus": _planet_dict(s.venus),
        "mars": _planet_dict(s.mars),
        "jupiter": _planet_dict(s.jupiter),
        "saturn": _planet_dict(s.saturn),
        "uranus": _planet_dict(s.uranus),
        "neptune": _planet_dict(s.neptune),
        "pluto": _planet_dict(s.pluto),
    }

    # lagna + houses are only valid when time is known (h=12 is a fallback for unknown)
    chart["lagna"] = s.first_house.sign
    chart["houses"] = {
        "1": s.first_house.sign,
        "2": s.second_house.sign,
        "3": s.third_house.sign,
        "4": s.fourth_house.sign,
        "5": s.fifth_house.sign,
        "6": s.sixth_house.sign,
        "7": s.seventh_house.sign,
        "8": s.eighth_house.sign,
        "9": s.ninth_house.sign,
        "10": s.tenth_house.sign,
        "11": s.eleventh_house.sign,
        "12": s.twelfth_house.sign,
    }
    return chart


@tool
def compute_birth_chart(
    year: int, month: int, day: int,
    hour: int | None, minute: int | None,
    lat: float, lng: float, tz: str,
) -> dict:
    """Compute the Vedic (sidereal/Lahiri, whole-sign) kundli.

    Requires lat/lng/tz — call geocode_place(<place>) FIRST and pass its resolved
    coordinates here. Do not pass a place name or guess coordinates.

    If hour/minute is None, returns rashi + nakshatra only (lagna and houses omitted) —
    tell the user the lagna and houses need a known birth time.
    """
    from datetime import date
    import pytz  # bundles its own IANA db (cross-platform; matches Kerykeion's tz handling)

    # Validate date (basic check)
    try:
        date(year, month, day)
    except ValueError as exc:
        return {"error": f"Invalid date: {exc}"}

    # Validate the year is within the supported ephemeris range.
    if not (_MIN_YEAR <= year <= _MAX_YEAR):
        return {"error": (
            f"Year {year} is outside the supported range "
            f"({_MIN_YEAR}–{_MAX_YEAR}). Please check the birth year."
        )}

    # Validate coordinates — out-of-range values silently corrupt house/lagna math.
    if not (-90.0 <= lat <= 90.0):
        return {"error": f"Latitude {lat} is out of range (-90 to 90)."}
    if not (-180.0 <= lng <= 180.0):
        return {"error": f"Longitude {lng} is out of range (-180 to 180)."}

    # Validate timezone is a real IANA zone (geocode can return None/garbage).
    if not tz or not isinstance(tz, str):
        return {"error": "Missing timezone. Resolve the birth place with geocode_place first."}
    try:
        pytz.timezone(tz)
    except pytz.UnknownTimeZoneError:
        return {"error": f"Unknown timezone {tz!r}. Expected an IANA name like 'Asia/Kolkata'."}

    time_known = hour is not None

    # Use default time if not known (will compute moon sign & nakshatra, omit houses)
    h = 12 if not time_known else hour
    m = 0 if not time_known else (minute or 0)

    try:
        raw = _compute_chart(year, month, day, h, m, lat, lng, tz)
    except Exception as exc:
        return {"error": f"Chart computation failed: {exc}"}

    # Build response from cached raw chart
    chart = {
        "ayanamsa": raw["ayanamsa"],
        "moon": raw["moon"].copy(),
        "sun": raw["sun"].copy(),
        "mercury": raw["mercury"].copy(),
        "venus": raw["venus"].copy(),
        "mars": raw["mars"].copy(),
        "jupiter": raw["jupiter"].copy(),
        "saturn": raw["saturn"].copy(),
        "uranus": raw["uranus"].copy(),
        "neptune": raw["neptune"].copy(),
        "pluto": raw["pluto"].copy(),
        "time_known": time_known,
    }

    if time_known:
        chart["lagna"] = raw["lagna"]
        chart["houses"] = raw["houses"].copy()
    else:
        chart["lagna"] = None
        chart["houses"] = None

    return chart
