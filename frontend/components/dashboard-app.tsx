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
              <span>写真行业增长分析助手</span>
            </div>
          </div>
          <div className="header-status">
            <span className="status-dot" />
            本地分析模式
          </div>
        </div>

        {result ? (
          <>
            <div className="analysis-heading">
              <div>
                <p className="section-kicker">Growth dashboard</p>
                <h1>用户增长分析总览</h1>
                <p>
                  从用户规模、转化漏斗到渠道效率，快速定位写真小程序的增长表现。
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
                label="当前文件"
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
              <DatasetItem label="数据状态" value="分析完成" status />
            </div>
          </>
        ) : (
          <div className="empty-state">
            <div className="empty-state-copy">
              <p className="section-kicker">Growth intelligence workspace</p>
              <h1>让增长数据更快变成运营判断</h1>
              <p>
                上传写真小程序业务 Excel，自动完成数据清洗、指标计算、漏斗分析与渠道对比。
              </p>
              <div className="feature-chips">
                <span>数据质量校验</span>
                <span>六步增长漏斗</span>
                <span>渠道效率对比</span>
              </div>
            </div>
            <UploadPanel onAnalyzed={setResult} />
          </div>
        )}
      </header>

      {result ? <DashboardView result={result} /> : null}

      <footer className="app-footer">
        <span>GrowthLens AI · Portfolio MVP</span>
        <span>数据仅在本次请求中处理，不持久化保存</span>
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
