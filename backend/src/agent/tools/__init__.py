"""Tool registry — orchestrator-owned. Import all tools here."""
from langchain_core.tools import tool
from agent.tools.geocode import geocode_place
from agent.tools.chart import compute_birth_chart
from agent.tools.transits import get_daily_transits
from agent.tools.knowledge import knowledge_lookup


# NOTE: the tool name "request_birth_details" is a frontend↔backend contract — the popup
# in frontend/hooks/use-pending-birth-request.ts detects this exact toolName to show the
# birth form. If you rename it, update that hook too (guarded by a test).
@tool
def request_birth_details(needs_name: bool = True) -> str:
    """Request the user's birth details via an interactive form in the UI.

    Args:
        needs_name: True if the user's name is not yet known — the form will include
                    a name field at the top. False if the name is already in the conversation.

    Call this when the user's question requires birth data (chart, transits, planetary
    positions) and birth details are NOT already present in the conversation history.
    Do NOT call this if birth date, time, and place are already known.
    """
    return ""


TOOLS = [geocode_place, compute_birth_chart, get_daily_transits, knowledge_lookup, request_birth_details]

__all__ = ["TOOLS", "geocode_place", "compute_birth_chart", "get_daily_transits", "knowledge_lookup", "request_birth_details"]
