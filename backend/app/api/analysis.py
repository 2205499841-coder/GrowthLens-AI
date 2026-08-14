import logging

from fastapi import APIRouter, File, HTTPException, UploadFile, status

from app.core.config import settings
from app.schemas.analysis import (
    AnalysisResponse,
    DatasetPlaceholderResponse,
    GrowthAnalysisResponse,
)
from app.schemas.analysis_context import DatasetType
from app.services.aggregate_analyzer import analyze_aggregate_excel
from app.schemas.ingestion import ExcelIngestionErrorResponse
from app.services.analysis_classifier import (
    classify_analysis_context,
    classify_dataset_type,
)
from app.services.data_cleaner import clean_growth_data
from app.services.excel_parser import (
    ExcelParseError,
    ParsedExcel,
    REQUIRED_COLUMNS,
    parse_excel,
    validate_file_name,
)
from app.services.growth_metrics import build_growth_analysis
from app.services.schema_mapper import (
    SchemaMappingError,
    build_ai_mapped_excel,
    extract_excel_schema,
    map_columns,
)


router = APIRouter(prefix="/api/analysis", tags=["analysis"])
logger = logging.getLogger(__name__)


@router.post(
    "/growth",
    response_model=AnalysisResponse,
    responses={422: {"model": ExcelIngestionErrorResponse}},
)
async def analyze_growth_excel(
    file: UploadFile = File(...),
) -> AnalysisResponse:
    try:
        file_name = validate_file_name(file.filename)
        file_content = await file.read(settings.max_upload_size_bytes + 1)

        if len(file_content) > settings.max_upload_size_bytes:
            raise HTTPException(
                status_code=status.HTTP_413_CONTENT_TOO_LARGE,
                detail="文件大小不能超过 10 MB。",
            )

        mapping_source = "fixed"
        try:
            parsed_excel = parse_excel(file_content)
            classifier_columns = _get_fixed_source_columns(parsed_excel)
        except ExcelParseError as exc:
            if exc.error != "Excel字段不完整":
                raise

            try:
                extracted_schema = extract_excel_schema(file_content)
                dataset_type = classify_dataset_type(
                    extracted_schema.columns
                )
                if dataset_type == "aggregate_metrics":
                    return analyze_aggregate_excel(
                        file_content,
                        file_name=file_name,
                        extracted_schema=extracted_schema,
                    )
                if dataset_type == "unsupported":
                    return _build_placeholder_response(
                        file_name=file_name,
                        dataset_type=dataset_type,
                    )
                mapping_result = map_columns(extracted_schema.columns)
                parsed_excel = build_ai_mapped_excel(
                    file_content,
                    extracted_schema,
                    mapping_result,
                )
                mapping_source = "ai"
                classifier_columns = list(extracted_schema.columns)
            except ExcelParseError as mapping_parse_exc:
                if mapping_parse_exc.error == "AI字段映射不完整":
                    return _build_placeholder_response(
                        file_name=file_name,
                        dataset_type="unsupported",
                    )
                raise
            except SchemaMappingError as mapping_exc:
                logger.exception("AI 字段识别失败：%r", mapping_exc)
                raise HTTPException(
                    status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
                    detail={
                        "error": "AI字段识别失败",
                        "message": str(mapping_exc),
                    },
                ) from mapping_exc

        schema_mapping = {
            "mapping": parsed_excel.field_mapping,
            "source": mapping_source,
            "missing_fields": [
                field
                for field in REQUIRED_COLUMNS
                if field not in parsed_excel.field_mapping
            ],
        }
        analysis_context = classify_analysis_context(
            schema_mapping,
            classifier_columns,
        )
        cleaning_result = clean_growth_data(parsed_excel.data_frame)
        analysis = build_growth_analysis(
            cleaning_result,
            file_name=file_name,
        )
        analysis["data_ingestion"] = parsed_excel.data_ingestion_summary
        analysis["schema_mapping"] = schema_mapping
        analysis["analysis_context"] = analysis_context.model_dump(mode="json")
        return GrowthAnalysisResponse.model_validate(analysis)
    finally:
        await file.close()


def _get_fixed_source_columns(parsed_excel: ParsedExcel) -> list[str]:
    columns = list(parsed_excel.field_mapping.values())
    for column in parsed_excel.data_frame.columns:
        source_column = str(column)
        if source_column in REQUIRED_COLUMNS or source_column in columns:
            continue
        columns.append(source_column)
    return columns


def _build_placeholder_response(
    *,
    file_name: str,
    dataset_type: DatasetType,
) -> DatasetPlaceholderResponse:
    if dataset_type != "unsupported":
        raise ValueError("占位响应仅适用于 unsupported 数据类型。")
    message = (
        "当前文件暂无法形成可靠分析，请检查是否包含清晰的"
        "业务维度、经营指标或用户行为字段。"
    )

    return DatasetPlaceholderResponse(
        dataset_type=dataset_type,
        metadata={
            "file_name": file_name,
            "data_start_date": None,
            "data_end_date": None,
        },
        message=message,
    )
