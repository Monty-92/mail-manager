"""FastAPI router for the LLM analysis service."""

import structlog
from fastapi import APIRouter, HTTPException

from llm_analysis.analyzer import analyze_email
from llm_analysis.repository import get_analysis_by_email_id, get_unanalyzed_emails
from llm_analysis.schemas import AnalysisResult, StoredAnalysis

logger = structlog.get_logger()

router = APIRouter(prefix="/analyze", tags=["analysis"])


@router.get("/{email_id}", response_model=StoredAnalysis)
async def get_analysis(email_id: str) -> StoredAnalysis:
    """Retrieve a stored analysis for an email."""
    analysis = await get_analysis_by_email_id(email_id)
    if analysis is None:
        raise HTTPException(status_code=404, detail="analysis not found")
    return analysis


@router.post("/batch", response_model=list[AnalysisResult])
async def analyze_batch(limit: int = 50) -> list[AnalysisResult]:
    """Analyze up to `limit` emails that have no analysis yet."""
    emails = await get_unanalyzed_emails(limit)
    results = []
    for email in emails:
        result = await analyze_email(email.id)
        results.append(result)
    return results


@router.post("/{email_id}", response_model=AnalysisResult)
async def analyze_single(email_id: str) -> AnalysisResult:
    """Analyze a single email by ID (on-demand trigger)."""
    result = await analyze_email(email_id)
    if result.error == "email not found":
        raise HTTPException(status_code=404, detail="email not found")
    return result
