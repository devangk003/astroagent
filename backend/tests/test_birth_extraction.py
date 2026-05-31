"""Guards the frontend form ↔ backend regex contract for birth-detail parsing.

If anyone changes the sentence the form emits (frontend/components/birth-form.tsx)
or the parser (graph.py), these round-trip cases catch it loudly instead of the
agent silently looping on "please share your birth details".
"""
from agent.graph import extract_birth_details, router
from langchain_core.messages import AIMessage


def _extract(text: str):
    return extract_birth_details({"messages": [{"type": "human", "content": text}]}).get(
        "birth_details"
    )


# ── The four exact formats birth-form.tsx can emit ────────────────────────────

def test_form_name_known_time():
    bd = _extract("My name is Priya. I was born on 15 January 1990 at 02:30, in Mumbai, India.")
    assert bd is not None
    assert (bd["name"], bd["year"], bd["month"], bd["day"]) == ("Priya", 1990, 1, 15)
    assert bd["hour"] == 2 and bd["minute"] == 30 and bd["unknown_time"] is False
    assert bd["place"] == "Mumbai, India"


def test_form_no_name_known_time():
    bd = _extract("I was born on 9 June 2001 at 18:45, in Chennai.")
    assert bd is not None
    assert bd["name"] is None and bd["hour"] == 18 and bd["minute"] == 45


def test_form_unknown_time():
    bd = _extract("My name is Sam. I was born on 3 March 1988 (birth time unknown), in Pune.")
    assert bd is not None
    assert bd["unknown_time"] is True and bd["hour"] is None and bd["minute"] is None


# ── Tolerance for variations that previously silently failed ──────────────────

def test_month_abbreviation():
    bd = _extract("I was born on 3 Jan 1988 at 09:05, in Delhi.")
    assert bd is not None and bd["month"] == 1 and bd["day"] == 3


def test_ordinal_and_of():
    bd = _extract("I was born on 15th of January 1990 at 14:30, in New Delhi.")
    assert bd is not None and bd["day"] == 15 and bd["month"] == 1


def test_us_order():
    bd = _extract("I was born on January 15, 1990 at 02:30, in Paris.")
    assert bd is not None and bd["day"] == 15 and bd["month"] == 1


def test_place_with_period_not_truncated():
    bd = _extract("My name is Sam. I was born on 3 Jan 1988 at 09:05, in St. Louis.")
    assert bd is not None and bd["place"] == "St. Louis"


def test_normal_message_is_not_parsed():
    assert _extract("What does my moon sign mean?") is None


# ── Cancel handling ───────────────────────────────────────────────────────────

def test_cancel_short_circuits_with_ack():
    out = router({"messages": [{"type": "human", "content": "Cancel"}]})
    msg = out["messages"][0]
    assert isinstance(msg, AIMessage)
    assert "whenever you're ready" in msg.content
