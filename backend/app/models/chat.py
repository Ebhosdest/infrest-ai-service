"""
Data models for the Copilot chat feature.

These define the exact shape of data flowing between the frontend
and the AI service. Pydantic validates everything automatically —
if the frontend sends bad data, it gets a clear error before any
processing happens.
"""

from pydantic import BaseModel, Field
from typing import Optional
from datetime import datetime
from enum import Enum


class MessageRole(str, Enum):
    USER = "user"
    ASSISTANT = "assistant"
    SYSTEM = "system"


class ResponseType(str, Enum):
    TEXT = "text"
    DATA_TABLE = "data_table"
    NAVIGATION = "navigation"
    ACTION_CONFIRM = "action_confirm"
    ERROR = "error"
    CHART = "chart"


class ChatMessage(BaseModel):
    """A single message in the conversation."""
    role: MessageRole
    content: str
    timestamp: datetime = Field(default_factory=datetime.utcnow)


class ChatRequest(BaseModel):
    """
    What the frontend sends when the user submits a message.

    session_id tracks the conversation. current_module tells the AI
    where the user is in the ERP, so it can give context-aware responses.
    """
    message: str = Field(..., max_length=2000, description="The user's message")
    session_id: str = Field(..., description="Unique session identifier")
    current_module: Optional[str] = Field(None, description="Which ERP module the user is currently viewing")
    conversation_history: list[ChatMessage] = Field(default_factory=list, description="Previous messages in this session")


class NavigationAction(BaseModel):
    """Tells the frontend to navigate to a specific route."""
    path: str
    label: str
    params: Optional[dict] = None


class DataTableResponse(BaseModel):
    """Structured data returned as a table."""
    columns: list[str]
    rows: list[dict]
    total_rows: int
    summary: Optional[str] = None


class ChartResponse(BaseModel):
    """Chart data for visualisation."""
    chart_type: str  # line, bar, pie, scatter
    title: str
    data: dict
    options: Optional[dict] = None


class ChatResponse(BaseModel):
    """
    What the AI service sends back to the frontend.

    response_type tells the widget how to render the response.
    A text response is just displayed. A navigation response
    triggers a route change. A data_table response renders a table.
    """
    message: str
    response_type: ResponseType = ResponseType.TEXT
    session_id: str
    navigation: Optional[NavigationAction] = None
    data_table: Optional[DataTableResponse] = None
    chart: Optional[ChartResponse] = None
    suggested_actions: list[str] = Field(default_factory=list)
    confidence: Optional[float] = Field(None, ge=0.0, le=1.0)
    processing_time_ms: Optional[int] = None
