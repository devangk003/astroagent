"""Shared state schema for the AstroAgent graph. Orchestrator-owned — do not edit from sub-agents."""
from typing import Annotated, Optional
from typing_extensions import TypedDict
from langgraph.graph.message import add_messages


class BirthDetails(TypedDict):
    name: Optional[str]
    year: int
    month: int
    day: int
    unknown_time: bool
    hour: Optional[int]    # None if birth time unknown
    minute: Optional[int]  # None if birth time unknown
    place: str
    lat: Optional[float]   # filled by geocode_place
    lng: Optional[float]
    tz: Optional[str]


class AstroState(TypedDict):
    messages: Annotated[list, add_messages]  # required by assistant-ui runtime
    birth_details: Optional[BirthDetails]
    chart: Optional[dict]  # cached compute_birth_chart output (PRD §10) — avoids recompute & feeds transits
