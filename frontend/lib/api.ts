import type { GrowthAnalysisResult } from "@/types/analysis";
import type { AIReport } from "@/types/ai-report";
import type { ExcelParseResult } from "@/types/upload";

const API_BASE_URL =
  process.env.NEXT_PUBLIC_API_BASE_URL ?? "http://localhost:8000";

interface ApiErrorResponse {
  detail?: unknown;
  error?: string;
  message?: string;
  missing_fields?: string[];
}

async function buildApiError(
  response: Response,
  fallbackMessage: string,
): Promise<Error> {
  const errorBody = (await response.json().catch(() => null)) as
    | ApiErrorResponse
    | null;
  const detailMessage =
    typeof errorBody?.detail === "string" ? errorBody.detail : null;
  const baseMessage =
    errorBody?.message ?? detailMessage ?? errorBody?.error ?? fallbackMessage;
  const missingFields = errorBody?.missing_fields ?? [];
  const fieldMessage = missingFields.length
    ? ` 缺少字段：${missingFields.join("、")}。`
    : "";

  return new Error(`${baseMessage}${fieldMessage}`);
}

export async function parseExcel(file: File): Promise<ExcelParseResult> {
  const body = new FormData();
  body.append("file", file);

  const response = await fetch(`${API_BASE_URL}/api/uploads/parse`, {
    method: "POST",
    body,
  });

  if (!response.ok) {
    throw await buildApiError(response, "Excel 解析失败，请稍后重试。");
  }

  return (await response.json()) as ExcelParseResult;
}

export async function analyzeGrowth(
  file: File,
): Promise<GrowthAnalysisResult> {
  const body = new FormData();
  body.append("file", file);

  const response = await fetch(`${API_BASE_URL}/api/analysis/growth`, {
    method: "POST",
    body,
  });

  if (!response.ok) {
    throw await buildApiError(response, "增长分析失败，请稍后重试。");
  }

  return (await response.json()) as GrowthAnalysisResult;
}

export async function generateAIReport(
  result: GrowthAnalysisResult,
): Promise<AIReport> {
  const response = await fetch(`${API_BASE_URL}/api/ai/report`, {
    method: "POST",
    headers: {
      "Content-Type": "application/json",
    },
    body: JSON.stringify({
      analysis_context: result.analysis_context ?? {
        analysis_type: "user_growth",
        business_type: "general",
        recommended_metrics: [
          "注册用户数",
          "浏览率",
          "留资率",
          "预约率",
          "到店率",
          "成交率",
          "GMV",
          "客单价",
        ],
      },
      schema_mapping: result.schema_mapping ?? {
        mapping: result.data_ingestion.field_mapping,
        source: "fixed",
      },
      data_quality: result.data_quality,
      metrics: result.metrics,
      funnel: result.funnel,
      channels: result.channels,
    }),
  });

  if (!response.ok) {
    throw await buildApiError(response, "AI 增长报告生成失败，请稍后重试。");
  }

  return (await response.json()) as AIReport;
}
