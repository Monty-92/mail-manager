import structlog
from fastapi import APIRouter, HTTPException

from preprocessing.pipeline import preprocess_email
from preprocessing.repository import get_unprocessed_emails
from preprocessing.schemas import PreprocessingStatus, PreprocessResult

logger = structlog.get_logger()

router = APIRouter(prefix="/preprocess", tags=["preprocessing"])


@router.post("/batch", response_model=list[PreprocessResult])
async def preprocess_batch(limit: int = 50) -> list[PreprocessResult]:
    """Preprocess up to `limit` emails that have no embedding yet."""
    emails = await get_unprocessed_emails(limit)
    results = []
    for email in emails:
        result = await preprocess_email(email.id)
        results.append(result)
    return results


@router.post("/{email_id}", response_model=PreprocessResult)
async def preprocess_single(email_id: str) -> PreprocessResult:
    """Preprocess a single email by ID (on-demand trigger)."""
    result = await preprocess_email(email_id)
    if result.status == PreprocessingStatus.FAILED and result.error == "email not found":
        raise HTTPException(status_code=404, detail="email not found")
    return result
