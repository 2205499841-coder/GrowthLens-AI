import logging

from fastapi import APIRouter, File, HTTPException, UploadFile, status

from app.core.config import settings
from app.schemas.ingestion import ExcelIngestionErrorResponse
from app.schemas.schema_mapping import SchemaMappingResponse
from app.schemas.upload import ExcelParseResponse
from app.services.excel_parser import (
    build_parse_response,
    parse_excel,
    validate_file_name,
)
from app.services.schema_mapper import (
    SchemaMappingError,
    extract_excel_schema,
    map_columns,
)

router = APIRouter(prefix="/api/uploads", tags=["uploads"])
logger = logging.getLogger(__name__)


@router.post(
    "/parse",
    response_model=ExcelParseResponse,
    responses={422: {"model": ExcelIngestionErrorResponse}},
)
async def parse_uploaded_excel(file: UploadFile = File(...)) -> ExcelParseResponse:
    try:
        file_name = validate_file_name(file.filename)
        file_content = await file.read(settings.max_upload_size_bytes + 1)

        if len(file_content) > settings.max_upload_size_bytes:
            raise HTTPException(
                status_code=status.HTTP_413_CONTENT_TOO_LARGE,
                detail="文件大小不能超过 10 MB。",
            )

        parsed_excel = parse_excel(file_content)
        response_data = build_parse_response(
            file_name=file_name,
            parsed_excel=parsed_excel,
            preview_limit=settings.preview_row_limit,
        )
        return ExcelParseResponse.model_validate(response_data)
    finally:
        await file.close()


@router.post(
    "/schema-map",
    response_model=SchemaMappingResponse,
    responses={422: {"model": ExcelIngestionErrorResponse}},
)
async def map_uploaded_excel_schema(
    file: UploadFile = File(...),
) -> SchemaMappingResponse:
    try:
        validate_file_name(file.filename)
        file_content = await file.read(settings.max_upload_size_bytes + 1)

        if len(file_content) > settings.max_upload_size_bytes:
            raise HTTPException(
                status_code=status.HTTP_413_CONTENT_TOO_LARGE,
                detail="文件大小不能超过 10 MB。",
            )

        extracted_schema = extract_excel_schema(file_content)
        return map_columns(extracted_schema.columns)
    except SchemaMappingError as exc:
        logger.exception("Excel 字段识别失败：%r", exc)
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail=str(exc),
        ) from exc
    finally:
        await file.close()
