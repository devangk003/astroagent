"""Phase 1 gate — verify geocode_place resolves real places."""
from agent.tools.geocode import geocode_place


def test_geocode_mumbai():
    """Mumbai → lat~19, lng~72, tz=Asia/Kolkata."""
    r = geocode_place.invoke({"place": "Mumbai"})
    assert "error" not in r, f"Unexpected error: {r}"
    assert abs(r["lat"] - 19.0) < 1.0
    assert abs(r["lng"] - 72.8) < 1.0
    assert r["tz"] == "Asia/Kolkata"


def test_geocode_delhi():
    """Delhi → lat~28, lng~77, tz=Asia/Kolkata."""
    r = geocode_place.invoke({"place": "Delhi"})
    assert "error" not in r, f"Unexpected error: {r}"
    assert abs(r["lat"] - 28.6) < 1.0
    assert abs(r["lng"] - 77.2) < 1.0
    assert r["tz"] == "Asia/Kolkata"


def test_geocode_unknown():
    """Garbage input → error dict."""
    r = geocode_place.invoke({"place": "qwertyuiop12345unknown"})
    assert "error" in r


def test_geocode_empty_place_no_network():
    """Empty place → clear error, without a network call."""
    r = geocode_place.invoke({"place": "   "})
    assert "error" in r


def test_geocode_resolved_name_present():
    """Successful resolution surfaces resolved_name so wrong matches are visible."""
    r = geocode_place.invoke({"place": "Mumbai"})
    assert "error" not in r, f"Unexpected error: {r}"
    assert r.get("resolved_name")


def test_geocode_tz_none_returns_error(monkeypatch):
    """A location whose timezone can't be determined (ocean/pole) → error, not tz=None."""
    import agent.tools.geocode as g
    import geopy.geocoders
    import timezonefinder

    class _Loc:
        latitude, longitude, address = -90.0, 0.0, "South Pole"

    class _FakeNominatim:
        def __init__(self, *a, **k): pass
        def geocode(self, *a, **k): return _Loc()

    class _FakeTF:
        def timezone_at(self, *a, **k): return None

    monkeypatch.setattr(geopy.geocoders, "Nominatim", _FakeNominatim)
    monkeypatch.setattr(timezonefinder, "TimezoneFinder", _FakeTF)
    g._geo.cache_clear()  # bypass any cached real result
    r = geocode_place.invoke({"place": "South Pole"})
    g._geo.cache_clear()
    assert "error" in r and "timezone" in r["error"].lower()
