import logging

from fastapi import APIRouter, HTTPException, status

from app.core.config import settings
from app.schemas.ai_report import AIReportRequest, AIReportResponse
from app.services.ai_report import (
    AIReportProviderError,
    generate_ai_report,
)


router = APIRouter(prefix="/api/ai", tags=["ai-report"])
logger = logging.getLogger(__name__)


@router.post("/report", response_model=AIReportResponse)
def create_ai_growth_report(
    request: AIReportRequest,
) -> AIReportResponse:
    try:
        return generate_ai_report(request)
    except AIReportProviderError as exc:
        logger.exception(
            "AI 报告生成失败：provider=%s model=%s error=%r",
            settings.ai_provider,
            settings.ai_model,
            exc,
        )
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail=str(exc),
        ) from exc
