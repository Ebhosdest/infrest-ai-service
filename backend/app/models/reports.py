"""
Data models for the NLP Report Query feature.
"""

from pydantic import BaseModel, Field
from typing import Optional
from enum import Enum


class ChartType(str, Enum):
    LINE = "line"
    BAR = "bar"
    PIE = "pie"
    SCATTER = "scatter"
    HORIZONTAL_BAR = "horizontal_bar"
    GROUPED_BAR = "grouped_bar"


class ReportQueryRequest(BaseModel):
    query: str = Field(..., max_length=500, description="Natural language report query")
    session_id: str
    refinement_context: Optional[str] = Field(None, description="Previous query for refinement")


class ParsedQuery(BaseModel):
    """What the LLM extracts from the natural language query."""
    source_table: str
    measures: list[dict]
    dimensions: list[str] = Field(default_factory=list)
    filters: list[dict] = Field(default_factory=list)
    order_by: Optional[dict] = None
    limit: int = 100
    time_period: Optional[dict] = None
    interpretation: str = ""


class ReportQueryResponse(BaseModel):
    query_interpretation: str
    columns: list[str]
    rows: list[dict]
    total_rows: int
    chart_type: ChartType
    chart_config: dict
    sql_preview: Optional[str] = None
    suggested_refinements: list[str] = Field(default_factory=list)
    processing_time_ms: int = 0
