"""Phase 1 gate — verify compute_birth_chart produces a correct Vedic kundli."""
from agent.tools.chart import compute_birth_chart


def test_chart_01_mumbai():
    """14 Aug 1995, 9:30am, Mumbai — verified moon ≈ 341.37° Pisces (Uttara Bhadrapada pada 3)."""
    r = compute_birth_chart.invoke({
        "year": 1995, "month": 8, "day": 14,
        "hour": 9, "minute": 30,
        "lat": 19.0760, "lng": 72.8777, "tz": "Asia/Kolkata",
    })
    assert "error" not in r, f"Unexpected error: {r}"
    assert r["time_known"] is True

    moon = r["moon"]
    assert moon["sign"] == "Pis"
    abs_pos = moon["abs_pos"]
    assert abs(341.3744 - abs_pos) < 1.0, f"Moon abs_pos {abs_pos} outside tolerance"

    nak = moon["nakshatra"]
    assert nak["name"] == "Uttara Bhadrapada"
    assert nak["pada"] == 3

    # Lagna should be present
    assert r["lagna"] is not None
    assert "houses" in r and r["houses"] is not None


def test_chart_02_delhi():
    """3 March 1988, 11:45pm, Delhi — verify lagna and key planets present."""
    r = compute_birth_chart.invoke({
        "year": 1988, "month": 3, "day": 3,
        "hour": 23, "minute": 45,
        "lat": 28.6139, "lng": 77.2089, "tz": "Asia/Kolkata",
    })
    assert "error" not in r
    assert r["time_known"] is True
    assert r["lagna"] is not None
    assert r["houses"] is not None
    # Moon sign should be present
    assert r["moon"]["sign"] is not None


def test_chart_unknown_time():
    """Unknown birth time → partial chart (rashi + nakshatra, no lagna/houses)."""
    r = compute_birth_chart.invoke({
        "year": 1992, "month": 6, "day": 5,
        "hour": None, "minute": None,
        "lat": 13.0827, "lng": 80.2707, "tz": "Asia/Kolkata",
    })
    assert "error" not in r
    assert r["time_known"] is False
    assert r["moon"]["sign"] is not None
    assert r["moon"]["nakshatra"] is not None
    assert r["lagna"] is None
    assert r["houses"] is None


def test_chart_invalid_date():
    """30 February returns graceful error."""
    r = compute_birth_chart.invoke({
        "year": 1990, "month": 2, "day": 30,
        "hour": 9, "minute": 0,
        "lat": 19.0, "lng": 72.0, "tz": "Asia/Kolkata",
    })
    assert "error" in r


# ── Boundary validation: fail loudly, never silently compute garbage ──────────

_BASE = {"year": 1990, "month": 6, "day": 15, "hour": 12, "minute": 0,
         "lat": 19.0, "lng": 72.0, "tz": "Asia/Kolkata"}


def test_chart_latitude_out_of_range():
    r = compute_birth_chart.invoke({**_BASE, "lat": 95.0})
    assert "error" in r and "atitude" in r["error"]


def test_chart_longitude_out_of_range():
    r = compute_birth_chart.invoke({**_BASE, "lng": 200.0})
    assert "error" in r and "ongitude" in r["error"]


def test_chart_bad_timezone():
    r = compute_birth_chart.invoke({**_BASE, "tz": "Not/AZone"})
    assert "error" in r and "timezone" in r["error"].lower()


def test_chart_empty_timezone():
    r = compute_birth_chart.invoke({**_BASE, "tz": ""})
    assert "error" in r


def test_chart_year_out_of_range():
    r = compute_birth_chart.invoke({**_BASE, "year": 1700})
    assert "error" in r and "range" in r["error"].lower()


def test_chart_noon_birth_is_time_known():
    """A real noon birth must be time_known=True (not mistaken for unknown time)."""
    r = compute_birth_chart.invoke({**_BASE})
    assert "error" not in r
    assert r["time_known"] is True
