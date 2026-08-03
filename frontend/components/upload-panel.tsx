"use client";

import { ChangeEvent, FormEvent, useState } from "react";

import { analyzeGrowth } from "@/lib/api";
import type { GrowthAnalysisResult } from "@/types/analysis";

const ACCEPTED_FILE_EXTENSION = ".xlsx";
const MAX_FILE_SIZE_BYTES = 10 * 1024 * 1024;
const DEMO_FILE_PATH = "/sample_data/portrait_growth_demo.xlsx";

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
          <p className="section-kicker">Excel 数据源</p>
          <h2 id="upload-title">上传写真业务数据，生成增长 Dashboard</h2>
          <p>
            系统将在单次请求内完成数据清洗、指标计算和漏斗分析，不保存业务原始文件。
          </p>
        </div>
      ) : null}

      <form className="upload-form" onSubmit={handleSubmit}>
        <label className="file-picker">
          <span className="file-picker-label">
            {selectedFile?.name ?? currentFileName ?? "选择 .xlsx 文件"}
          </span>
          <span className="file-picker-action">
            {compact ? "更换文件" : "浏览文件"}
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
          {isUploading ? "正在分析…" : compact ? "重新分析" : "生成 Dashboard"}
        </button>
      </form>

      {error ? (
        <div className="feedback feedback-error" role="alert">
          {error}
        </div>
      ) : null}

      {!compact ? (
        <p className="upload-hint">
          演示文件：
          <a download href={DEMO_FILE_PATH}>
            下载 portrait_growth_demo.xlsx
          </a>
          <span> · 最大 10 MB</span>
        </p>
      ) : null}
    </section>
  );
}
