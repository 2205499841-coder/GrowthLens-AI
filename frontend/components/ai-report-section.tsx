"use client";

import { useState } from "react";

import { generateAIReport } from "@/lib/api";
import type { GrowthAnalysisResult } from "@/types/analysis";
import type {
  AIReport,
  Confidence,
  ExpectedDirection,
} from "@/types/ai-report";

interface AIReportSectionProps {
  analysis: GrowthAnalysisResult;
}

const CONFIDENCE_LABELS: Record<Confidence, string> = {
  high: "高置信度",
  medium: "中置信度",
  low: "低置信度",
};

const DIRECTION_LABELS: Record<ExpectedDirection, string> = {
  increase: "预期提升",
  decrease: "预期降低",
  maintain: "保持稳定",
};

export function AIReportSection({
  analysis,
}: AIReportSectionProps) {
  const [report, setReport] = useState<AIReport | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [isLoading, setIsLoading] = useState(false);

  async function handleGenerate() {
    setIsLoading(true);
    setError(null);

    try {
      const nextReport = await generateAIReport(analysis);
      setReport(nextReport);
    } catch (requestError) {
      setError(
        requestError instanceof Error
          ? requestError.message
          : "AI 增长报告生成失败，请稍后重试。",
      );
    } finally {
      setIsLoading(false);
    }
  }

  return (
    <section className="dashboard-section ai-report-section">
      <div className="section-heading ai-section-heading">
        <div>
          <div className="ai-kicker-row">
            <p className="section-kicker">AI growth report</p>
            <span className="provider-badge">AI Provider</span>
          </div>
          <h2>AI 增长报告</h2>
        </div>
        <div className="ai-heading-actions">
          <p>
            AI 只解释后端聚合指标，不读取 Excel 原始明细，也不重新计算数据。
          </p>
          <button
            className="ai-generate-button"
            disabled={isLoading}
            onClick={handleGenerate}
            type="button"
          >
            {isLoading
              ? "正在生成报告…"
              : report
                ? "重新生成"
                : "生成 AI 报告"}
          </button>
        </div>
      </div>

      {error ? (
        <div className="feedback feedback-error ai-feedback">
          {error}
        </div>
      ) : null}

      {!report ? (
        <AIReportPlaceholder isLoading={isLoading} />
      ) : (
        <AIReportContent report={report} />
      )}
    </section>
  );
}

function AIReportPlaceholder({ isLoading }: { isLoading: boolean }) {
  return (
    <div
      aria-busy={isLoading}
      className={`ai-report-placeholder${isLoading ? " is-loading" : ""}`}
    >
      <div className="ai-placeholder-mark">AI</div>
      <div>
        <h3>{isLoading ? "正在组织增长洞察" : "基于当前结果生成业务解释"}</h3>
        <p>
          {isLoading
            ? "正在校验数据依据、渠道名称与洞察置信度。"
            : "报告将包含整体总结、核心洞察、渠道机会和可执行增长建议。"}
        </p>
      </div>
      <span>结构化 JSON 输出</span>
    </div>
  );
}

function AIReportContent({ report }: { report: AIReport }) {
  return (
    <div className="ai-report-panel">
      <div className="ai-summary">
        <span>AI 一句话总结</span>
        <p>{report.summary}</p>
      </div>

      <div className="ai-report-block">
        <ReportBlockHeading
          index="01"
          title="核心洞察"
          description="数据依据与原因假设分开呈现"
        />
        <div className="insight-grid">
          {report.key_insights.map((insight) => (
            <article className="insight-card" key={insight.title}>
              <div className="insight-card-header">
                <span
                  className={`confidence-badge confidence-${insight.confidence}`}
                >
                  {CONFIDENCE_LABELS[insight.confidence]}
                </span>
                <span className="insight-icon">↗</span>
              </div>
              <h4>{insight.title}</h4>
              <div className="insight-detail">
                <span>数据依据</span>
                <p>{insight.evidence}</p>
              </div>
              <div className="insight-detail interpretation">
                <span>原因假设</span>
                <p>{insight.interpretation}</p>
              </div>
            </article>
          ))}
        </div>
      </div>

      <div className="ai-report-columns">
        <div className="ai-report-block">
          <ReportBlockHeading
            index="02"
            title="渠道机会"
            description="仅引用当前分析中的真实渠道"
          />
          <div className="opportunity-list">
            {report.channel_opportunities.map((item) => (
              <article className="opportunity-item" key={item.channel}>
                <div className="opportunity-channel">
                  <span className="channel-dot" />
                  <strong>{item.channel}</strong>
                  <span
                    className={`confidence-dot confidence-dot-${item.confidence}`}
                    title={CONFIDENCE_LABELS[item.confidence]}
                  />
                </div>
                <p>{item.opportunity}</p>
                <small>{item.evidence}</small>
              </article>
            ))}
          </div>
        </div>

        <div className="ai-report-block">
          <ReportBlockHeading
            index="03"
            title="增长行动建议"
            description="建议方向，不替代业务实验验证"
          />
          <ol className="action-list">
            {report.growth_actions.map((item, index) => (
              <li key={`${item.target_metric}-${index}`}>
                <span>{String(index + 1).padStart(2, "0")}</span>
                <div>
                  <p>{item.action}</p>
                  <div className="action-meta">
                    <strong>{item.target_metric}</strong>
                    <span>
                      {DIRECTION_LABELS[item.expected_direction]}
                    </span>
                  </div>
                </div>
              </li>
            ))}
          </ol>
        </div>
      </div>

      <div className="ai-limitations">
        <strong>数据限制</strong>
        <ul>
          {report.limitations.map((limitation) => (
            <li key={limitation}>{limitation}</li>
          ))}
        </ul>
      </div>
    </div>
  );
}

function ReportBlockHeading({
  description,
  index,
  title,
}: {
  description: string;
  index: string;
  title: string;
}) {
  return (
    <div className="report-block-heading">
      <span>{index}</span>
      <div>
        <h3>{title}</h3>
        <p>{description}</p>
      </div>
    </div>
  );
}
