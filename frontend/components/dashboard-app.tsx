"use client";

import { useState } from "react";

import { DashboardView } from "@/components/dashboard-view";
import { UploadPanel } from "@/components/upload-panel";
import { formatDateRange, formatInteger } from "@/lib/formatters";
import type { GrowthAnalysisResult } from "@/types/analysis";

export function DashboardApp() {
  const [result, setResult] = useState<GrowthAnalysisResult | null>(null);

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
          <div className="header-status">
            <span className="status-dot" />
            智能分析服务已就绪
          </div>
        </div>

        {result ? (
          <>
            <div className="analysis-heading">
              <div>
                <p className="section-kicker">Growth intelligence dashboard</p>
                <h1>业务增长分析全景</h1>
                <p>
                  整合数据质量、核心指标、转化漏斗与渠道表现，快速识别关键增长机会。
                </p>
              </div>
              <UploadPanel
                compact
                currentFileName={result.metadata.file_name}
                onAnalyzed={setResult}
              />
            </div>
            <div className="dataset-strip">
              <DatasetItem
                label="数据文件"
                value={result.metadata.file_name}
              />
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
              <DatasetItem label="分析状态" value="洞察已就绪" status />
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
            <UploadPanel onAnalyzed={setResult} />
          </div>
        )}
      </header>

      {result ? <DashboardView result={result} /> : null}

      <footer className="app-footer">
        <span>GrowthLens AI · AI 增长分析平台</span>
        <span>安全处理业务数据，不持久化保存原始文件</span>
      </footer>
    </main>
  );
}

function DatasetItem({
  label,
  status = false,
  value,
}: {
  label: string;
  status?: boolean;
  value: string;
}) {
  return (
    <div className="dataset-item">
      <span>{label}</span>
      <strong className={status ? "dataset-status" : undefined}>
        {status ? <span className="status-dot" /> : null}
        {value}
      </strong>
    </div>
  );
}
