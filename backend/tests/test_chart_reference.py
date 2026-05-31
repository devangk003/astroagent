"""Reference-chart accuracy gate (FR-B2 / NFR-11): verify Kerykeion's sidereal/Lahiri
output against externally-known anchors, within ~1 degree.

Anchors (independent of this codebase):
  * Lahiri (Chitrapaksha) ayanamsa at J2000.0 is 23 deg 51' ~= 23.853 deg.
  * Tropical Sun on 2000-01-01 12:00 UT is ~280.4 deg; sidereal = 280.4 - 23.85 ~= 256.5 deg
    -> Sagittarius. (Sun enters sidereal Capricorn at Makar Sankranti, ~Jan 14.)
  * On 1990-01-15 the Sun has just entered sidereal Capricorn (Makar Sankranti).
"""
from agent.tools.chart import compute_birth_chart

_TOL_DEG = 1.0


def _chart(**kw):
    return compute_birth_chart.invoke(kw)


def test_lahiri_ayanamsa_at_j2000():
    """Lahiri ayanamsa on 2000-01-01 must be ~23.85 deg (the defining value of the mode)."""
    r = _chart(year=2000, month=1, day=1, hour=12, minute=0, lat=51.48, lng=0.0, tz="Europe/London")
    assert abs(r["ayanamsa"] - 23.853) < 0.1, f"ayanamsa drifted: {r['ayanamsa']}"


def test_sidereal_sun_2000_within_one_degree():
    """Sidereal Sun on 2000-01-01 12:00 UT must be ~256.5 deg (Sagittarius), within ~1 deg."""
    r = _chart(year=2000, month=1, day=1, hour=12, minute=0, lat=51.48, lng=0.0, tz="Europe/London")
    assert r["sun"]["sign"] == "Sag", f"expected Sag, got {r['sun']['sign']}"
    assert abs(r["sun"]["abs_pos"] - 256.5) < _TOL_DEG, f"sun abs_pos={r['sun']['abs_pos']}"


def test_makar_sankranti_sun_in_capricorn_1990():
    """On 1990-01-15 the sidereal Sun has just entered Capricorn (early degrees)."""
    r = _chart(year=1990, month=1, day=15, hour=2, minute=30, lat=28.6139, lng=77.2090, tz="Asia/Kolkata")
    assert r["sun"]["sign"] == "Cap", f"expected Cap, got {r['sun']['sign']}"
    # 'just entered' -> within the first few degrees of the sign (abs 270-273).
    assert 270.0 <= r["sun"]["abs_pos"] < 273.0, f"sun abs_pos={r['sun']['abs_pos']}"


def test_chart_is_deterministic():
    """Same input -> identical output (regression guard for the ephemeris path)."""
    args = dict(year=1990, month=1, day=15, hour=2, minute=30, lat=28.6139, lng=77.2090, tz="Asia/Kolkata")
    assert _chart(**args) == _chart(**args)
