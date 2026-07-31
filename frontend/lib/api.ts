import type { GrowthAnalysisResult } from "@/types/analysis";
import type { ExcelParseResult } from "@/types/upload";

const API_BASE_URL =
  process.env.NEXT_PUBLIC_API_BASE_URL ?? "http://localhost:8000";

export async function parseExcel(file: File): Promise<ExcelParseResult> {
  const body = new FormData();
  body.append("file", file);

  const response = await fetch(`${API_BASE_URL}/api/uploads/parse`, {
    method: "POST",
    body,
  });

  if (!response.ok) {
    const errorBody = (await response.json().catch(() => null)) as
      | { detail?: string }
      | null;
    throw new Error(errorBody?.detail ?? "Excel 解析失败，请稍后重试。");
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
    const errorBody = (await response.json().catch(() => null)) as
      | { detail?: string }
      | null;
    throw new Error(errorBody?.detail ?? "增长分析失败，请稍后重试。");
  }

  return (await response.json()) as GrowthAnalysisResult;
}
