"use client";

import { ChangeEvent, FormEvent, useState } from "react";

import { parseExcel } from "@/lib/api";
import type { ExcelParseResult } from "@/types/upload";

const ACCEPTED_FILE_EXTENSION = ".xlsx";
const MAX_FILE_SIZE_BYTES = 10 * 1024 * 1024;

export function UploadPanel() {
  const [selectedFile, setSelectedFile] = useState<File | null>(null);
  const [result, setResult] = useState<ExcelParseResult | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [isUploading, setIsUploading] = useState(false);

  function handleFileChange(event: ChangeEvent<HTMLInputElement>) {
    const file = event.target.files?.[0] ?? null;
    setResult(null);
    setError(null);

    if (!file) {
      setSelectedFile(null);
      return;
    }

    if (!file.name.toLowerCase().endsWith(ACCEPTED_FILE_EXTENSION)) {
      setSelectedFile(null);
      setError("当前仅支持 .xlsx 格式的 Excel 文件。");
      return;
    }

    if (file.size > MAX_FILE_SIZE_BYTES) {
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
    setResult(null);

    try {
      setResult(await parseExcel(selectedFile));
    } catch (uploadError) {
      setError(
        uploadError instanceof Error
          ? uploadError.message
          : "Excel 解析失败，请稍后重试。",
      );
    } finally {
      setIsUploading(false);
    }
  }

  return (
    <section className="upload-card" aria-labelledby="upload-title">
      <div>
        <p className="section-label">Step 1</p>
        <h2 id="upload-title">上传写真业务数据</h2>
        <p className="section-copy">
          使用固定字段模板上传 Excel。当前读取第一个工作表，文件不会被持久化保存。
        </p>
      </div>

      <form className="upload-form" onSubmit={handleSubmit}>
        <label className="file-picker">
          <span>{selectedFile ? selectedFile.name : "选择 .xlsx 文件"}</span>
          <input
            accept={ACCEPTED_FILE_EXTENSION}
            aria-label="选择 Excel 文件"
            onChange={handleFileChange}
            type="file"
          />
        </label>
        <button disabled={!selectedFile || isUploading} type="submit">
          {isUploading ? "正在解析…" : "上传并解析"}
        </button>
      </form>

      {error ? (
        <div className="feedback feedback-error" role="alert">
          {error}
        </div>
      ) : null}

      {result ? (
        <div className="parse-result" aria-live="polite">
          <div className="result-heading">
            <div>
              <p className="section-label">解析成功</p>
              <h3>{result.file_name}</h3>
            </div>
            <span className="success-badge">可进入数据清洗</span>
          </div>
          <dl className="result-grid">
            <div>
              <dt>工作表</dt>
              <dd>{result.sheet_name}</dd>
            </div>
            <div>
              <dt>数据行</dt>
              <dd>{result.row_count.toLocaleString("zh-CN")}</dd>
            </div>
            <div>
              <dt>字段数</dt>
              <dd>{result.column_count}</dd>
            </div>
          </dl>
          <div className="column-list">
            {result.columns.map((column) => (
              <span key={column.name}>{column.name}</span>
            ))}
          </div>
        </div>
      ) : null}
    </section>
  );
}
