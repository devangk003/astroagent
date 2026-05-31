"""Daily transits tool — computes gochar (transit) positions for a given date vs. natal moon/lagna."""
from datetime import datetime, timezone
from functools import lru_cache
from typing import Annotated, Optional

from langchain_core.tools import tool
from langgraph.prebuilt import InjectedState

PLANET_NAMES = [
    "moon", "sun", "mercury", "venus", "mars",
    "jupiter", "saturn", "uranus", "neptune", "pluto",
]


def _planet_dict(obj) -> dict:
    """Build a minimal planet dict (sign + abs_pos + retrograde) from a Kerykeion object."""
    return {
        "sign": obj.sign,
        "abs_pos": obj.abs_pos,
        "retrograde": bool(getattr(obj, "retrograde", False)),
    }


@lru_cache(maxsize=256)
def _compute_transits(date_str: str) -> dict:
    """Cached transit computation for a given date (12:00 UTC, lat=0, lng=0).

    Cache key is the date string so repeated calls for the same date are free.
    """
    from agent.tools._ephemeris import build_subject

    # Parse date and use noon UTC as a stable, well-defined moment
    d = datetime.fromisoformat(date_str)

    s = build_subject("Transit", d.year, d.month, d.day, 12, 0, 0.0, 0.0, "UTC")

    return {
        "moon":    _planet_dict(s.moon),
        "sun":     _planet_dict(s.sun),
        "mercury": _planet_dict(s.mercury),
        "venus":   _planet_dict(s.venus),
        "mars":    _planet_dict(s.mars),
        "jupiter": _planet_dict(s.jupiter),
        "saturn":  _planet_dict(s.saturn),
        "uranus":  _planet_dict(s.uranus),
        "neptune": _planet_dict(s.neptune),
        "pluto":   _planet_dict(s.pluto),
    }


@tool
def get_daily_transits(
    date: str = "",
    natal: dict = None,
    state: Annotated[Optional[dict], InjectedState] = None,
) -> dict:
    """Return gochar (transit) positions for a given date vs the natal moon/lagna.

    The natal chart is read automatically from the conversation's cached chart — you do
    NOT need to pass it. Just call get_daily_transits(date) (date optional, defaults today).

    Args:
        date: ISO date string (YYYY-MM-DD). Defaults to today's UTC date if not provided.
        natal: (Optional) natal chart dict. Normally omit this — the cached chart is used.
    Returns on success:
        {
          "transits": {planet_name: {"sign": str, "abs_pos": float, "retrograde": bool}, ...},
          "retrograde": [planet_name, ...],  # planets currently retrograde (empty list if none)
          "natal_moon": str | None,   # natal moon sign, from natal["moon"]["sign"]
          "natal_lagna": str | None,  # natal ascendant sign, from natal["lagna"]
          "date": str
        }
    Use the "retrograde" list to answer "which planets are in retrograde?" — do not guess.
    Returns on error:
        {"error": str}
    """
    if not date:
        date = datetime.now(timezone.utc).strftime("%Y-%m-%d")

    # Prefer an explicitly-passed natal; otherwise read the cached chart from graph state
    # (FR-A4/B4) so the model doesn't have to re-pass the whole natal dict every call.
    if not natal:
        natal = (state or {}).get("chart") or {}
    if natal is None:
        natal = {}

    # Validate date format — be explicit about the expected shape (not a raw ValueError).
    try:
        datetime.fromisoformat(date)
    except (ValueError, TypeError):
        return {"error": f"Invalid date {date!r}. Expected ISO format YYYY-MM-DD (e.g. 2026-05-29)."}

    # Extract natal reference points safely
    natal_moon: str | None = None
    natal_lagna: str | None = None

    moon_entry = natal.get("moon")
    if isinstance(moon_entry, dict):
        natal_moon = moon_entry.get("sign")

    lagna_entry = natal.get("lagna")
    if isinstance(lagna_entry, str):
        natal_lagna = lagna_entry

    # Compute transit positions (cached)
    try:
        transits = _compute_transits(date)
    except Exception as exc:
        return {"error": f"Transit computation failed: {exc}"}

    result: dict = {
        "transits": transits,
        "retrograde": [name for name, p in transits.items() if p.get("retrograde")],
        "natal_moon": natal_moon,
        "natal_lagna": natal_lagna,
        "date": date,
    }
    if natal_moon is None and natal_lagna is None and natal:
        result["warning"] = (
            "natal dict was provided but contained no moon/lagna data — "
            "call compute_birth_chart first and pass its full output as natal"
        )
    return result
