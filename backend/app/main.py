from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse

from app.api.ai_reports import router as ai_reports_router
from app.api.analysis import router as analysis_router
from app.api.uploads import router as uploads_router
from app.core.config import settings
from app.services.excel_parser import ExcelParseError

app = FastAPI(
    title=settings.app_name,
    version=settings.app_version,
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=list(settings.frontend_origins),
    allow_credentials=False,
    allow_methods=["GET", "POST"],
    allow_headers=["*"],
)

app.include_router(uploads_router)
app.include_router(analysis_router)
app.include_router(ai_reports_router)


@app.exception_handler(ExcelParseError)
async def handle_excel_parse_error(
    _request: Request,
    exc: ExcelParseError,
) -> JSONResponse:
    return JSONResponse(
        status_code=422,
        content=exc.to_response_payload(),
    )


@app.get("/api/health", tags=["system"])
def health_check() -> dict[str, str]:
    return {
        "status": "ok",
        "service": settings.app_name,
        "version": settings.app_version,
    }
