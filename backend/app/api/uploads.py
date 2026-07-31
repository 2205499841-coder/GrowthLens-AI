from fastapi import APIRouter, File, HTTPException, UploadFile, status

from app.core.config import settings
from app.schemas.upload import ExcelParseResponse
from app.services.excel_parser import (
    ExcelParseError,
    build_parse_response,
    parse_excel,
    validate_file_name,
)

router = APIRouter(prefix="/api/uploads", tags=["uploads"])


@router.post("/parse", response_model=ExcelParseResponse)
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
    except ExcelParseError as exc:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_CONTENT,
            detail=str(exc),
        ) from exc
    finally:
        await file.close()
