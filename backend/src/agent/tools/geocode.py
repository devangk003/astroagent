"""Geocoding tool — resolves a place name to {lat, lng, tz}."""
from functools import lru_cache
from langchain_core.tools import tool


@lru_cache(maxsize=512)
def _geo(place: str) -> dict | None:
    """Cached geocode lookup via Nominatim + timezonefinder.

    Returns None if the place can't be resolved, or {"error": ...} if a location was
    found but its timezone could not be determined (e.g. open ocean / Antarctica).
    On success returns {lat, lng, tz, resolved_name} — resolved_name lets the caller
    surface WHICH place was used (Nominatim returns its single best match).
    """
    from geopy.geocoders import Nominatim
    from timezonefinder import TimezoneFinder

    # Nominatim policy: custom user_agent, ~1 req/sec — caching covers us
    loc = Nominatim(user_agent="astroagent").geocode(place, addressdetails=True)
    if not loc:
        return None
    tz = TimezoneFinder().timezone_at(lat=loc.latitude, lng=loc.longitude)
    if not tz:
        return {"error": (
            f"Found {loc.address!r} but could not determine its timezone "
            f"(it may be over open ocean or a polar region). "
            f"Please provide a more specific place."
        )}
    return {
        "lat": loc.latitude,
        "lng": loc.longitude,
        "tz": tz,
        "resolved_name": loc.address,
    }


@tool
def geocode_place(place: str) -> dict:
    """Resolve a place name to {lat, lng, tz, resolved_name}. Returns {error} if not found.

    resolved_name is Nominatim's best match — mention it to the user so a wrong match
    (e.g. the wrong "Paris") can be caught instead of silently using bad coordinates.
    """
    if not place or not place.strip():
        return {"error": "No place provided. Please share your birth city/town."}
    try:
        r = _geo(place.strip())
    except Exception as exc:
        return {"error": f"Geocoding failed: {exc}"}
    return r or {"error": f"Could not resolve place: {place!r}"}
