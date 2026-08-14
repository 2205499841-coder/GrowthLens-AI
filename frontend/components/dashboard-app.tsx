"use client";

import { useState } from "react";

import { DashboardView } from "@/components/dashboard-view";
import { UploadPanel } from "@/components/upload-panel";
import { formatDateRange, formatInteger } from "@/lib/formatters";
import type { AnalysisResult } from "@/types/analysis";

export function DashboardApp() {
  const [result, setResult] = useState<AnalysisResult | null>(null);

  function handleAnalyzed(nextResult: AnalysisResult) {
    setResult(nextResult);
  }

  return (
    <main className="app-shell">
      <header className="app-header">
        <div className="header-row">
          <div className="brand">
            <span className="brand-mark">GL</span>
            <div>
              <strong>GrowthLens AI</strong>
              <span>AI 业务增长分析平台</span>
            </div>
          </div>
        </div>

        {result ? (
          <>
            <div className="analysis-heading">
              <div>
                <p className="section-kicker">Growth intelligence dashboard</p>
                <h1>
                  {result.dataset_type === "user_level"
                    ? "业务增长分析全景"
                    : "业务数据识别结果"}
                </h1>
                <p>
                  {result.dataset_type === "user_level"
                    ? "整合数据质量、核心指标、转化漏斗与渠道表现，快速识别关键增长机会。"
                    : "GrowthLens 已完成文件结构判断，并保留当前可用的数据状态。"}
                </p>
              </div>
              <UploadPanel
                compact
                currentFileName={result.metadata.file_name}
                onAnalyzed={handleAnalyzed}
              />
            </div>
            <div className="dataset-strip">
              <DatasetItem
                label="数据文件"
                value={result.metadata.file_name}
              />
              <DatasetItem
                label="数据类型"
                value={
                  result.dataset_type === "user_level"
                    ? "用户级行为明细"
                    : result.dataset_type === "aggregate_metrics"
                      ? "聚合经营指标报表"
                      : "暂不支持的数据结构"
                }
              />
              {result.dataset_type === "user_level" ? (
                <>
                  <DatasetItem
                    label="数据覆盖时间"
                    value={formatDateRange(
                      result.metadata.data_start_date,
                      result.metadata.data_end_date,
                    )}
                  />
                  <DatasetItem
                    label="有效用户"
                    value={`${formatInteger(result.data_quality.valid_user_count)} 人`}
                  />
                </>
              ) : (
                <DatasetItem label="分析可用性" value="当前不可用" />
              )}
            </div>
          </>
        ) : (
          <div className="empty-state">
            <div className="empty-state-copy">
              <p className="section-kicker">AI-powered growth intelligence</p>
              <h1>让每一份业务数据，都转化为增长决策</h1>
              <p>
                上传业务 Excel，自动完成数据理解、质量诊断、指标计算、转化漏斗与渠道分析，快速获得可执行的增长洞察。
              </p>
              <div className="feature-chips">
                <span>AI 数据理解</span>
                <span>转化漏斗诊断</span>
                <span>渠道增长策略</span>
              </div>
            </div>
            <UploadPanel onAnalyzed={handleAnalyzed} />
          </div>
        )}
      </header>

      {result?.dataset_type === "user_level" ? (
        <DashboardView result={result} />
      ) : result ? (
        <DatasetPlaceholder result={result} />
      ) : null}

      <footer className="app-footer">
        <span>GrowthLens AI · AI 增长分析平台</span>
        <span>安全处理业务数据，不持久化保存原始文件</span>
      </footer>
    </main>
  );
}

function DatasetItem({
  label,
  value,
}: {
  label: string;
  value: string;
}) {
  return (
    <div className="dataset-item">
      <span>{label}</span>
      <strong>{value}</strong>
    </div>
  );
}

function DatasetPlaceholder({
  result,
}: {
  result: Exclude<AnalysisResult, { dataset_type: "user_level" }>;
}) {
  const isAggregate = result.dataset_type === "aggregate_metrics";

  return (
    <div className="dashboard-content">
      <section className="dataset-placeholder">
        <span>{isAggregate ? "聚合经营指标报表" : "数据结构待确认"}</span>
        <h2>
          {isAggregate
            ? "已完成报表类型识别"
            : "暂时无法生成可靠分析"}
        </h2>
        <p>{result.message}</p>
        <small>
          未识别或尚不可计算的指标不会以 0 代替。
        </small>
      </section>
    </div>
  );
}
