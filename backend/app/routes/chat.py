"""
Chat API routes.

Provides the HTTP endpoints that the frontend widget calls.
Kept thin — all business logic is in the service layer.
"""

from fastapi import APIRouter, HTTPException
from app.models.chat import ChatRequest, ChatResponse
from app.services.copilot import CopilotService

router = APIRouter(prefix="/api/copilot", tags=["copilot"])

# Single instance reused across requests
copilot = CopilotService()


@router.post("/chat", response_model=ChatResponse)
async def chat(request: ChatRequest):
    """
    Main chat endpoint.

    Accepts a user message with conversation context,
    processes it through the AI pipeline, and returns
    a structured response.
    """
    if not request.message.strip():
        raise HTTPException(status_code=400, detail="Message cannot be empty")

    response = await copilot.process_message(request)
    return response


@router.get("/health")
async def health():
    """Health check for monitoring and load balancers."""
    return {"status": "healthy", "service": "infrest-copilot"}
