"""Tests for FR-A4 (chart caching) and the chart-content parser in graph.py."""
import json

from langchain_core.messages import AIMessage, HumanMessage, ToolMessage

from agent.graph import cache_chart, _parse_tool_content, _MAX_TOOL_TURNS

_CHART = {"moon": {"sign": "Taurus"}, "lagna": "Scorpio", "time_known": True}


def test_parse_tool_content_handles_json_string():
    assert _parse_tool_content(json.dumps(_CHART)) == _CHART


def test_parse_tool_content_handles_dict_passthrough():
    assert _parse_tool_content(_CHART) == _CHART


def test_parse_tool_content_returns_none_on_garbage():
    assert _parse_tool_content("not json {") is None
    assert _parse_tool_content(12345) is None


def test_cache_chart_extracts_from_tool_message():
    """A successful compute_birth_chart ToolMessage is cached into state['chart']."""
    state = {"messages": [
        HumanMessage(content="my chart"),
        AIMessage(content="", tool_calls=[{"name": "compute_birth_chart", "args": {}, "id": "c1"}]),
        ToolMessage(content=json.dumps(_CHART), tool_call_id="c1", name="compute_birth_chart"),
    ]}
    assert cache_chart(state) == {"chart": _CHART}


def test_cache_chart_ignores_errored_chart():
    """An errored chart call must not be cached as garbage."""
    state = {"messages": [
        ToolMessage(content=json.dumps({"error": "bad date"}), tool_call_id="c1", name="compute_birth_chart"),
    ]}
    assert cache_chart(state) == {}


def test_cache_chart_ignores_other_tools():
    """Tool messages from other tools should not be cached as the chart."""
    state = {"messages": [
        ToolMessage(content=json.dumps({"lat": 1.0}), tool_call_id="g1", name="geocode_place"),
    ]}
    assert cache_chart(state) == {}


def test_tool_budget_is_bounded():
    """The runaway-loop cap (FR-A6) is a small, sane positive integer."""
    assert isinstance(_MAX_TOOL_TURNS, int)
    assert 1 <= _MAX_TOOL_TURNS <= 15
