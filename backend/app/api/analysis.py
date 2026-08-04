from fastapi import APIRouter, File, HTTPException, UploadFile, status

from app.core.config import settings
from app.schemas.analysis import GrowthAnalysisResponse
from app.schemas.ingestion import ExcelIngestionErrorResponse
from app.services.data_cleaner import clean_growth_data
from app.services.excel_parser import (
    parse_excel,
    validate_file_name,
)
from app.services.growth_metrics import build_growth_analysis


router = APIRouter(prefix="/api/analysis", tags=["analysis"])


@router.post(
    "/growth",
    response_model=GrowthAnalysisResponse,
    responses={422: {"model": ExcelIngestionErrorResponse}},
)
async def analyze_growth_excel(
    file: UploadFile = File(...),
) -> GrowthAnalysisResponse:
    try:
        file_name = validate_file_name(file.filename)
        file_content = await file.read(settings.max_upload_size_bytes + 1)

        if len(file_content) > settings.max_upload_size_bytes:
            raise HTTPException(
                status_code=status.HTTP_413_CONTENT_TOO_LARGE,
                detail="文件大小不能超过 10 MB。",
            )

        parsed_excel = parse_excel(file_content)
        cleaning_result = clean_growth_data(parsed_excel.data_frame)
        analysis = build_growth_analysis(
            cleaning_result,
            file_name=file_name,
        )
        analysis["data_ingestion"] = parsed_excel.data_ingestion_summary
        return GrowthAnalysisResponse.model_validate(analysis)
    finally:
        await file.close()
