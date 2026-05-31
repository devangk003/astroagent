"""Tests for tools/transits.py — daily gochar (transit) computation."""
import pytest
from agent.tools.transits import get_daily_transits

DUMMY_NATAL = {
    "moon": {"sign": "Taurus", "abs_pos": 45.3, "nakshatra": {"name": "Rohini", "pada": 2}},
    "sun":  {"sign": "Aries",  "abs_pos": 10.1},
    "lagna": "Scorpio",
    "time_known": True,
}


def test_transits_basic():
    """A valid call returns a dict with a 'transits' key containing at least moon and sun."""
    result = get_daily_transits.invoke({"date": "2026-05-27", "natal": DUMMY_NATAL})
    assert "transits" in result, f"Expected 'transits' key, got: {result}"
    transits = result["transits"]
    assert "moon" in transits, "Expected 'moon' in transits"
    assert "sun"  in transits, "Expected 'sun' in transits"


def test_transits_invalid_date():
    """An unparseable date string causes the tool to return an 'error' key."""
    result = get_daily_transits.invoke({"date": "not-a-date", "natal": {}})
    assert "error" in result, f"Expected 'error' key for bad date, got: {result}"


def test_transits_positions_in_range():
    """All abs_pos values for a valid date must lie in the half-open interval [0, 360)."""
    result = get_daily_transits.invoke({"date": "2026-05-27", "natal": DUMMY_NATAL})
    assert "transits" in result, f"Expected 'transits' key, got: {result}"
    for planet, data in result["transits"].items():
        pos = data["abs_pos"]
        assert 0.0 <= pos < 360.0, (
            f"abs_pos for {planet} is {pos}, which is outside [0, 360)"
        )


def test_transits_natal_fields():
    """natal_moon and natal_lagna are correctly extracted from the provided natal dict."""
    natal = {
        "moon": {"sign": "Cancer", "abs_pos": 95.0},
        "lagna": "Virgo",
    }
    result = get_daily_transits.invoke({"date": "2026-05-27", "natal": natal})
    assert result.get("natal_moon") == "Cancer", (
        f"Expected natal_moon='Cancer', got: {result.get('natal_moon')}"
    )
    assert result.get("natal_lagna") == "Virgo", (
        f"Expected natal_lagna='Virgo', got: {result.get('natal_lagna')}"
    )
    # When natal is empty, both fields should be None
    result_empty = get_daily_transits.invoke({"date": "2026-05-27", "natal": {}})
    assert result_empty.get("natal_moon") is None
    assert result_empty.get("natal_lagna") is None


def test_transits_reads_natal_from_injected_state():
    """When natal is omitted, the natal chart is sourced from injected graph state (B4)."""
    state = {"chart": {"moon": {"sign": "Leo"}, "lagna": "Aries"}}
    result = get_daily_transits.invoke(
        {"date": "2026-05-27", "state": state}
    )
    assert result.get("natal_moon") == "Leo"
    assert result.get("natal_lagna") == "Aries"


def test_transits_explicit_natal_overrides_state():
    """An explicitly-passed natal takes precedence over the cached state chart."""
    state = {"chart": {"moon": {"sign": "Leo"}, "lagna": "Aries"}}
    result = get_daily_transits.invoke(
        {"date": "2026-05-27", "natal": DUMMY_NATAL, "state": state}
    )
    assert result.get("natal_moon") == "Taurus"  # from DUMMY_NATAL, not state


def test_transits_report_retrograde():
    """Each planet carries a retrograde bool, and a top-level retrograde list summarizes it (C1)."""
    result = get_daily_transits.invoke({"date": "2026-05-27"})
    assert "retrograde" in result, f"expected a 'retrograde' summary list, got {result.keys()}"
    assert isinstance(result["retrograde"], list)
    for name, p in result["transits"].items():
        assert "retrograde" in p, f"{name} missing retrograde flag"
        assert isinstance(p["retrograde"], bool)
    # The Sun is never retrograde — a correctness sanity check on the flag.
    assert result["transits"]["sun"]["retrograde"] is False
    # The summary list must match the per-planet flags exactly.
    expected = [n for n, p in result["transits"].items() if p["retrograde"]]
    assert result["retrograde"] == expected
