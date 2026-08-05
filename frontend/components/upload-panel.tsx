"use client";

import { ChangeEvent, FormEvent, useState } from "react";

import { analyzeGrowth } from "@/lib/api";
import type { GrowthAnalysisResult } from "@/types/analysis";

const ACCEPTED_FILE_EXTENSION = ".xlsx";
const MAX_FILE_SIZE_BYTES = 10 * 1024 * 1024;
const DATA_TEMPLATE_PATH = "/sample_data/portrait_growth_demo.xlsx";

interface UploadPanelProps {
  compact?: boolean;
  currentFileName?: string;
  onAnalyzed: (result: GrowthAnalysisResult) => void;
}

export function UploadPanel({
  compact = false,
  currentFileName,
  onAnalyzed,
}: UploadPanelProps) {
  const [selectedFile, setSelectedFile] = useState<File | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [isUploading, setIsUploading] = useState(false);

  function handleFileChange(event: ChangeEvent<HTMLInputElement>) {
    const file = event.target.files?.[0] ?? null;
    setError(null);

    if (!file) {
      setSelectedFile(null);
      return;
    }

    if (!file.name.toLowerCase().endsWith(ACCEPTED_FILE_EXTENSION)) {
      event.target.value = "";
      setSelectedFile(null);
      setError("当前仅支持 .xlsx 格式的 Excel 文件。");
      return;
    }

    if (file.size > MAX_FILE_SIZE_BYTES) {
      event.target.value = "";
      setSelectedFile(null);
      setError("文件大小不能超过 10 MB。");
      return;
    }

    setSelectedFile(file);
  }

  async function handleSubmit(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    if (!selectedFile) {
      setError("请先选择 Excel 文件。");
      return;
    }

    setIsUploading(true);
    setError(null);

    try {
      onAnalyzed(await analyzeGrowth(selectedFile));
    } catch (uploadError) {
      setError(
        uploadError instanceof Error
          ? uploadError.message
          : "增长分析失败，请稍后重试。",
      );
    } finally {
      setIsUploading(false);
    }
  }

  return (
    <section
      className={compact ? "upload-panel upload-panel-compact" : "upload-panel"}
      aria-labelledby={compact ? undefined : "upload-title"}
    >
      {!compact ? (
        <div className="upload-intro">
          <p className="section-kicker">Business data</p>
          <h2 id="upload-title">上传业务数据，开启智能增长分析</h2>
          <p>
            GrowthLens AI 将自动识别数据结构，完成质量校验、指标计算、漏斗诊断与渠道对比。
          </p>
        </div>
      ) : null}

      <form className="upload-form" onSubmit={handleSubmit}>
        <label className="file-picker">
          <span className="file-picker-label">
            {selectedFile?.name ?? currentFileName ?? "选择业务数据文件"}
          </span>
          <span className="file-picker-action">
            {compact ? "更换数据" : "选择文件"}
          </span>
          <input
            accept={ACCEPTED_FILE_EXTENSION}
            aria-label="选择 Excel 文件"
            disabled={isUploading}
            onChange={handleFileChange}
            type="file"
          />
        </label>
        <button
          className="primary-button"
          disabled={!selectedFile || isUploading}
          type="submit"
        >
          {isUploading ? "正在生成分析…" : compact ? "更新分析" : "开始增长分析"}
        </button>
      </form>

      {error ? (
        <div className="feedback feedback-error" role="alert">
          {error}
        </div>
      ) : null}

      {!compact ? (
        <p className="upload-hint">
          数据模板：
          <a download="growth_analysis_template.xlsx" href={DATA_TEMPLATE_PATH}>
            下载标准 Excel 模板
          </a>
          <span> · 支持 .xlsx · 最大 10 MB</span>
        </p>
      ) : null}
    </section>
  );
}
