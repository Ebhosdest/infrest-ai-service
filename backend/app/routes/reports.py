"""
NLP Report Query API routes.
"""

from fastapi import APIRouter, HTTPException
from app.models.reports import ReportQueryRequest, ReportQueryResponse
from app.services.report_engine import ReportEngine

router = APIRouter(prefix="/api/reports", tags=["reports"])

engine = ReportEngine()


@router.post("/query", response_model=ReportQueryResponse)
async def query_report(request: ReportQueryRequest):
    """
    Process a natural language report query.

    Examples:
    - "Show me total revenue by month for 2025"
    - "Top 10 customers by sales this year"
    - "Purchase orders over 5000000 Naira"
    - "Employee headcount by department"
    """
    if not request.query.strip():
        raise HTTPException(status_code=400, detail="Query cannot be empty")

    response = await engine.process_query(request)
    return response


@router.get("/examples")
async def get_example_queries():
    """Return example queries to help users get started."""
    return {
        "examples": [
            {"query": "Show me total revenue by month for 2025", "category": "Finance"},
            {"query": "Top 10 customers by sales this year", "category": "Sales"},
            {"query": "List all purchase orders over ₦5,000,000", "category": "Procurement"},
            {"query": "Compare inventory value by category", "category": "Inventory"},
            {"query": "Show headcount by department", "category": "HR"},
            {"query": "Which vendors have the highest spend?", "category": "Procurement"},
            {"query": "Show AR aging for all customers", "category": "Finance"},
            {"query": "Project budget vs actual cost", "category": "Projects"},
            {"query": "Monthly payroll cost for 2025", "category": "HR"},
            {"query": "Fixed asset value by category", "category": "Assets"},
        ]
    }
