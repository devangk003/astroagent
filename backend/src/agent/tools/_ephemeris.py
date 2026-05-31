"""Shared, cached Kerykeion subject construction.

`AstrologicalSubjectFactory.from_birth_data(...)` is the Swiss-ephemeris build step. chart.py
and transits.py both need a subject for the same birth data, so they route through the one
cached builder here instead of each rebuilding it.

SAFETY: the returned AstrologicalSubjectModel is shared across callers. DO NOT mutate the
returned object. Re-check this assumption on any Kerykeion upgrade ([VERIFY]).

`name` is part of the cache key on purpose so callers that differ only by name (e.g. a natal
vs. a transit subject) do not collapse to one cached entry.
"""
from __future__ import annotations

from functools import lru_cache


@lru_cache(maxsize=256)
def build_subject(
    name: str,
    year: int, month: int, day: int,
    hour: int, minute: int,
    lat: float, lng: float, tz: str,
):
    """Build (and cache) a sidereal/Lahiri whole-sign Kerykeion subject for the given data."""
    from kerykeion import AstrologicalSubjectFactory

    return AstrologicalSubjectFactory.from_birth_data(
        name, year, month, day, hour, minute,
        lng=lng, lat=lat, tz_str=tz, online=False,
        zodiac_type="Sidereal", sidereal_mode="LAHIRI",
        houses_system_identifier="W",
    )
