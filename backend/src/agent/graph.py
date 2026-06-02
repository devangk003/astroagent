"""AstroAgent graph — orchestrator-owned. Phase 4: configurable LLM via RunnableConfig."""

import json
import os
import re
from datetime import datetime, timezone

from langgraph.graph import StateGraph, START, END
from langgraph.prebuilt import ToolNode, tools_condition
from langchain_core.messages import AIMessage, HumanMessage, SystemMessage, ToolMessage
from langchain_core.runnables import RunnableConfig
from agent.state import AstroState, BirthDetails
from agent.tools import TOOLS
from agent.model import make_model, provider_api_key
from agent.guardrails import (
    SYSTEM_PROMPT, crisis_response, injection_response, sensitive_nudge,
    detect_output_violation, output_correction_instruction, safe_reframe,
    detect_offtopic_intent, detect_near_astrology_offtopic, offtopic_redirect,
    route_input, sensitive_category, is_fatalistic,  # layered: keyword → semantic fallback
)

# Agent defaults read from .env — browser BYOK overrides these per-run. Provider is free to be
# either 'ollama' or 'openrouter'; the matching key is resolved by provider_api_key (keys set once).
_DEFAULT_PROVIDER = os.environ.get("DEFAULT_PROVIDER", "ollama")
_DEFAULT_MODEL = os.environ.get("DEFAULT_MODEL", "qwen3.5:397b")

# Tool-call budget (FR-A6 / NFR-5): hard cap on tool-calling turns per request so a
# confused model cannot loop forever. A normal full flow is geocode → chart →
# transits (~3); 8 leaves headroom for retries without runaway cost.
_MAX_TOOL_TURNS = 8


_MONTHS = [
    "january", "february", "march", "april", "may", "june",
    "july", "august", "september", "october", "november", "december",
]
# Accept full names AND 3-letter abbreviations (+ "sept") so "15 Jan 1990" parses.
_MONTH_MAP = {m: i + 1 for i, m in enumerate(_MONTHS)}
_MONTH_MAP.update({m[:3]: i + 1 for i, m in enumerate(_MONTHS)})
_MONTH_MAP["sept"] = 9


def _get_llm(config: RunnableConfig, with_tools: bool = True):
    """Create an LLM using per-run configurable fields.

    Priority: browser api_key > .env provider key. Never falls back to any hardcoded value.
    When with_tools is False the model is returned unbound — used once the tool-call budget
    is spent so the model is forced to produce a final answer instead of more tool calls.
    """
    cfg = (config or {}).get("configurable", {})
    # Normalize so "OpenRouter"/" ollama " don't slip past the provider match.
    provider = (cfg.get("provider") or _DEFAULT_PROVIDER).strip().lower()
    model = (cfg.get("model") or _DEFAULT_MODEL).strip()
    # Browser-supplied key takes precedence; otherwise fall back to the env key for this provider.
    api_key = cfg.get("api_key") or provider_api_key(provider)
    # eval_mode disables streaming so the provider returns usage_metadata (token counts) for
    # cost accounting; production keeps streaming on for token-by-token UX.
    streaming = not cfg.get("eval_mode", False)
    llm = make_model(provider, model, api_key, streaming=streaming)
    return llm.bind_tools(TOOLS) if with_tools else llm


# ---- router node ----
def router(state: AstroState) -> dict:
    """Crisis/injection short-circuit. Returns partial state updates.

    Uses deterministic keywords ONLY (fast, always-on, not LLM-dependent) so a
    crisis/injection response is guaranteed before any tokens or tools. Medical/
    legal/financial reframing is handled by the main model via the system prompt
    (see SYSTEM_PROMPT), reinforced by the keyword nudge in the agent node.
    """
    last = state["messages"][-1]
    # Messages may arrive as plain dicts over HTTP; extract content safely.
    if isinstance(last, dict):
        content = last.get("content", "")
        msg_type = last.get("type", "")
    elif hasattr(last, "content"):
        content = last.content
        msg_type = getattr(last, "type", "")
    else:
        content = ""
        msg_type = ""

    # Only check human messages (skip AI/tool messages)
    if msg_type not in ("human", "user"):
        return {}

    # Birth-form Cancel: the popup sends the literal "Cancel". Acknowledge and end the
    # turn so the agent does not immediately re-call request_birth_details (the frontend
    # hook hides the form once the latest assistant message has no pending tool call).
    if content.strip().lower() == "cancel":
        return {"messages": [AIMessage(content=(
            "No problem — we can explore your chart whenever you're ready. "
            "Is there anything else I can help you with?"
        ))]}

    route = route_input(content)
    if route == "crisis":
        return {"messages": [
            AIMessage(content=crisis_response())
        ]}
    if route == "injection":
        return {"messages": [
            AIMessage(content=injection_response())
        ]}
    # Off-topic trivia (conservative; only when no astrology/birth signal) OR an unambiguous
    # non-Vedic divination ask (tarot/numerology/palmistry/tropical) → canned decline+steer.
    if detect_offtopic_intent(content) or detect_near_astrology_offtopic(content):
        return {"messages": [AIMessage(content=offtopic_redirect())]}
    return {}  # normal flow → fall through to agent


def route_after_router(state: AstroState) -> str:
    """Conditional edge: if the router already returned an AI message, end here."""
    last = state["messages"][-1]
    if isinstance(last, AIMessage):
        return "__end__"
    return "agent"


# ---- extract birth details node ----
# Tolerant parser for the birth-details sentence. The frontend form emits the
# day-first form ("I was born on 15 January 1990 at 02:30, in <place>."), but this
# also accepts: month abbreviations, an ordinal day ("15th"), an optional "of",
# US order ("January 15, 1990"), and place names containing periods ("St. Louis").
# `place` is captured to end-of-string (place is always last) and trimmed in code.
_DATE_CORE = (
    r"(?:"
    r"(?P<day>\d{1,2})(?:st|nd|rd|th)?\s+(?:of\s+)?(?P<month>[A-Za-z]+)"   # 15 [of] January
    r"|"
    r"(?P<month2>[A-Za-z]+)\s+(?P<day2>\d{1,2})(?:st|nd|rd|th)?,?"          # January 15,
    r")\s+(?P<year>\d{4})"
)
_BIRTH_RE = re.compile(
    r"(?:My name is\s+(?P<name>[^.]+?)\.\s+)?"
    r"I was born\s+(?:on\s+)?" + _DATE_CORE +
    r"(?:\s+at\s+(?P<hour>\d{1,2}):(?P<minute>\d{1,2}))?"
    r"(?:\s*\(birth time unknown\))?"
    r".*?\bin\s+(?P<place>.+?)\.?\s*$",
    re.IGNORECASE | re.DOTALL,
)


def extract_birth_details(state: AstroState) -> dict:
    """Parse the latest human message for structured birth data if present."""
    last_human = None
    for m in reversed(state["messages"]):
        if isinstance(m, HumanMessage) or (isinstance(m, dict) and m.get("type") in ("human", "user")):
            last_human = m
            break
    if last_human is None:
        return {}

    text = last_human.content if hasattr(last_human, "content") else last_human.get("content", "")
    text_lower = text.lower()
    match = _BIRTH_RE.search(text)
    if not match:
        return {}

    # day/month come from whichever alternation branch matched (day-first or US order).
    day = int(match.group("day") or match.group("day2"))
    month_name = (match.group("month") or match.group("month2")).lower()
    month = _MONTH_MAP.get(month_name)
    if month is None:
        return {}

    year = int(match.group("year"))
    name = match.group("name")
    name = name.strip() if name else None
    place = match.group("place").strip()

    unknown_time = "birth time unknown" in text_lower
    hour_str = match.group("hour")
    minute_str = match.group("minute")

    if unknown_time or hour_str is None or minute_str is None:
        hour = minute = None
        unknown_time = True
    else:
        hour = int(hour_str)
        minute = int(minute_str)
        unknown_time = False

    bd: BirthDetails = {
        "name": name,
        "year": year,
        "month": month,
        "day": day,
        "unknown_time": unknown_time,
        "hour": hour,
        "minute": minute,
        "place": place,
        "lat": None,
        "lng": None,
        "tz": None,
    }
    return {"birth_details": bd}


# ---- cache chart node ----
def _parse_tool_content(content) -> dict | None:
    """Best-effort parse of a ToolMessage payload into a dict (str→JSON or passthrough)."""
    if isinstance(content, dict):
        return content
    if isinstance(content, str):
        try:
            return json.loads(content)
        except (ValueError, TypeError):
            return None
    return None


def cache_chart(state: AstroState) -> dict:
    """Cache the latest successful compute_birth_chart result into state['chart'] (FR-A4).

    Runs after the tools node. Caching the kundli means the agent never recomputes it on
    later turns and get_daily_transits can read the natal chart straight from state.
    """
    for m in reversed(state["messages"]):
        is_tool = isinstance(m, ToolMessage) or (isinstance(m, dict) and m.get("type") == "tool")
        if not is_tool:
            continue
        name = m.name if hasattr(m, "name") else m.get("name")
        if name != "compute_birth_chart":
            continue
        content = m.content if hasattr(m, "content") else m.get("content", "")
        parsed = _parse_tool_content(content)
        if isinstance(parsed, dict) and "error" not in parsed:
            return {"chart": parsed}
        return {}  # most recent chart call errored — don't cache garbage
    return {}


# ---- agent node ----
def agent(state: AstroState, config: RunnableConfig) -> dict:
    """The reasoning LLM node. Emits tool calls or a final reply.

    Accepts RunnableConfig so the LLM can be swapped per-run via
    configurable.provider / configurable.model / configurable.api_key.
    """
    # Tool-call budget (FR-A6): once spent, drop tools so the model must answer now.
    tool_turns = sum(
        1 for m in state["messages"]
        if isinstance(m, AIMessage) and getattr(m, "tool_calls", None)
    )
    budget_spent = tool_turns >= _MAX_TOOL_TURNS
    try:
        llm = _get_llm(config, with_tools=not budget_spent)
    except ValueError as exc:
        # Missing/invalid key or unknown provider — degrade gracefully (NFR-3), no 500.
        return {"messages": [AIMessage(content=(
            f"I can't reach a model right now: {exc} "
            "Please add a valid API key in the model selector (or backend/.env) and try again."
        ))]}
    now = datetime.now(timezone.utc)
    date_ctx = SystemMessage(
        content=f"Current date: {now.strftime('%A, %d %B %Y')}. UTC time: {now.strftime('%H:%M')}. "
                f"This is the real present date — do not substitute any date from your training data."
    )
    msgs: list = [date_ctx, SystemMessage(content=SYSTEM_PROMPT)] + state["messages"]

    # Rail 3-5: reinforce the system-prompt reframing with a targeted nudge when a
    # medical/legal/financial keyword matches. Free (no LLM call); the main model
    # handles novel phrasings on its own via SYSTEM_PROMPT.
    last_human = next(
        (m for m in reversed(state["messages"])
         if isinstance(m, HumanMessage)
         or (isinstance(m, dict) and m.get("type") in ("human", "user"))),
        None,
    )
    if last_human is not None:
        human_text = (
            last_human.content if hasattr(last_human, "content")
            else last_human.get("content", "")
        )
        sensitive = sensitive_category(human_text)
        if sensitive:
            msgs.append(SystemMessage(content=sensitive_nudge(sensitive)))

    # If the last tool call returned an error, nudge the LLM to retry with corrected params.
    last = state["messages"][-1] if state["messages"] else None
    if isinstance(last, ToolMessage) and last.content and "error" in last.content.lower():
        msgs.append(SystemMessage(
            content="The last tool call returned an error. Review the error message above, "
                    "correct the parameters, and call the tool again."
        ))

    # If birth_details exist, inject them as system context so the agent can use tools.
    bd = state.get("birth_details")
    if bd is not None:
        if bd.get("unknown_time"):
            time_str = "time unknown"
        else:
            h = bd.get("hour") or "?"
            m = str(bd.get("minute") or 0).zfill(2)
            time_str = f"{h}:{m}"
        if bd.get("lat") is not None:
            coord_line = (
                f"Coordinates: lat={bd['lat']}, lng={bd['lng']}, tz={bd['tz']}. "
                f"Use these with compute_birth_chart."
            )
        else:
            coord_line = (
                f"Coordinates not yet resolved. "
                f"First call geocode_place({bd['place']!r}), then pass the result to compute_birth_chart."
            )
        info = (
            f"Birth details on file — "
            f"{bd.get('year', '?')}-{bd.get('month', '?')}-{bd.get('day', '?')} "
            f"at {time_str}, in {bd.get('place', '?')}. {coord_line}"
        )
        msgs.append(SystemMessage(content=info))

    # If a chart is already cached (FR-A4), tell the agent so it reuses it instead of
    # recomputing — saves a tool call and lets it answer transit/reading questions directly.
    chart = state.get("chart")
    if chart:
        msgs.append(SystemMessage(content=(
            "A natal chart is already computed and cached for this user — do NOT call "
            "compute_birth_chart again. Use get_daily_transits (which reads this cached "
            "chart automatically) for transit questions.\n"
            "Explore this chart with warmth and curiosity: speak directly to the person "
            "('your Moon', 'your Saturn'), frame each placement as a tendency to reflect on, "
            "and invite them in rather than reciting data.\n"
            "Cached chart (sidereal/Lahiri):\n"
            + json.dumps(chart)
        )))

    # Budget spent (FR-A6): force a grounded final answer, no further tool calls.
    if budget_spent:
        msgs.append(SystemMessage(content=(
            "You have reached the maximum number of tool calls for this turn. Do NOT request "
            "more tools. Give your best final answer now using the information already gathered."
        )))

    resp = llm.invoke(msgs)
    return {"messages": [resp]}


# ---- output rail node ----
def _msg_text(m) -> str:
    """Best-effort extract text content from a message (object or dict; list-of-parts safe)."""
    if m is None:
        return ""
    content = m.content if hasattr(m, "content") else (m.get("content", "") if isinstance(m, dict) else "")
    if isinstance(content, list):
        parts = [p.get("text", "") if isinstance(p, dict) else str(p) for p in content]
        return " ".join(parts)
    return content if isinstance(content, str) else str(content)


def output_guard(state: AstroState, config: RunnableConfig) -> dict:
    """Output rail (defense-in-depth 3rd layer): inspect the FINAL reply for leaked advice/fatalism.

    Runs only on the agent's terminal turn (no tool calls). On a detected medical/legal/financial/
    fatalism violation it regenerates the answer ONCE with a correction; if that still violates, it
    falls back to a deterministic safe reframe. No-op (and NO extra LLM call) on a clean reply, so
    normal turns keep flat latency. Crisis/injection are handled earlier in the router.
    """
    msgs = state["messages"]
    last = msgs[-1] if msgs else None
    if not isinstance(last, AIMessage):
        return {}
    reply = _msg_text(last)
    if not reply:
        return {}

    # Re-derive the sensitive category from the latest human turn (no state field needed).
    last_human = next(
        (m for m in reversed(msgs)
         if isinstance(m, HumanMessage)
         or (isinstance(m, dict) and m.get("type") in ("human", "user"))),
        None,
    )
    human_text = _msg_text(last_human) if last_human is not None else ""
    category = sensitive_category(human_text) if human_text else None
    fatalistic = is_fatalistic(human_text)

    violation = detect_output_violation(reply, category, fatalistic)
    if violation is None:
        return {}  # clean — pass through (the common case, no extra cost)

    # Regenerate once with a strong correction (uses the agent's BYOK model, NOT the judge).
    try:
        llm = _get_llm(config, with_tools=False)
        corrected = llm.invoke(
            [SystemMessage(content=SYSTEM_PROMPT), *msgs,
             SystemMessage(content=output_correction_instruction(violation))]
        )
        corrected_text = _msg_text(corrected)
        if corrected_text.strip() and detect_output_violation(corrected_text, category, fatalistic) is None:
            # Replace the offending reply (same id → add_messages overwrites it).
            return {"messages": [AIMessage(content=corrected_text, id=last.id)]}
    except Exception:
        pass  # regeneration unavailable → deterministic safe reframe below

    return {"messages": [AIMessage(content=safe_reframe(violation), id=last.id)]}


# ---- build graph ----
builder = StateGraph(AstroState)
builder.add_node("router", router)
builder.add_node("extract_birth_details", extract_birth_details)
builder.add_node("agent", agent)
builder.add_node("tools", ToolNode(TOOLS))  # executes geocode_place, compute_birth_chart, etc.
builder.add_node("cache_chart", cache_chart)  # persists the kundli into state after tools run
builder.add_node("output_guard", output_guard)  # inspects the final reply (soft-rail output check)
builder.add_edge(START, "router")
builder.add_conditional_edges(
    "router",
    route_after_router,
    {"agent": "extract_birth_details", "__end__": END},
)
builder.add_edge("extract_birth_details", "agent")
builder.add_conditional_edges(
    "agent",
    tools_condition,  # "tools" if tool_calls present, else terminal → output_guard
    {"tools": "tools", "__end__": "output_guard"},
)
builder.add_edge("tools", "cache_chart")  # cache any fresh chart, then loop back to reason
builder.add_edge("cache_chart", "agent")
builder.add_edge("output_guard", END)

graph = builder.compile()
