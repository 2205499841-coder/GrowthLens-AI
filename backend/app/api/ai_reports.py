from fastapi import APIRouter, HTTPException, status

from app.schemas.ai_report import AIReportRequest, AIReportResponse
from app.services.ai_report import (
    AIReportProviderError,
    generate_ai_report,
)


router = APIRouter(prefix="/api/ai", tags=["ai-report"])


@router.post("/report", response_model=AIReportResponse)
def create_ai_growth_report(
    request: AIReportRequest,
) -> AIReportResponse:
    try:
        return generate_ai_report(request)
    except AIReportProviderError as exc:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail=str(exc),
        ) from exc
