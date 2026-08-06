"use client";

import { useState } from "react";

import { generateAIReport } from "@/lib/api";
import type { GrowthAnalysisResult } from "@/types/analysis";
import type { AIReport, ExpectedDirection } from "@/types/ai-report";

interface AIReportSectionProps {
  analysis: GrowthAnalysisResult;
  onReportGenerated?: (report: AIReport) => void;
}

const DIRECTION_LABELS: Record<ExpectedDirection, string> = {
  increase: "预期提升",
  decrease: "预期降低",
  maintain: "保持稳定",
};

export function AIReportSection({
  analysis,
  onReportGenerated,
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
      onReportGenerated?.(nextReport);
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
            <p className="section-kicker">AI growth intelligence</p>
            <span className="provider-badge">AI 智能诊断</span>
          </div>
          <h2>AI 增长策略报告</h2>
        </div>
        <div className="ai-heading-actions">
          <p>
            基于业务指标、转化漏斗与渠道表现，生成增长诊断和可执行策略。
          </p>
          <button
            className="ai-generate-button"
            disabled={isLoading}
            onClick={handleGenerate}
            type="button"
          >
            {isLoading
              ? "正在生成策略…"
              : report
                ? "更新增长策略"
                : "生成增长策略"}
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
        <h3>
          {isLoading ? "正在研判增长机会" : "生成面向决策的增长诊断"}
        </h3>
        <p>
          {isLoading
            ? "正在结合分析类型、字段语义、漏斗与渠道表现组织业务诊断。"
            : "报告将包含整体诊断、关键问题、渠道策略和可执行增长建议。"}
        </p>
      </div>
      <span>业务诊断 · 行动建议</span>
    </div>
  );
}

function AIReportContent({ report }: { report: AIReport }) {
  return (
    <div className="ai-report-panel">
      <div className="ai-summary">
        <span>增长诊断摘要</span>
        <p>{report.summary}</p>
      </div>

      <div className="ai-report-block">
        <ReportBlockHeading
          index="01"
          title="关键增长发现"
          description="聚焦问题、数据证据与优化方向"
        />
        <div className="insight-grid">
          {report.key_findings.map((finding, index) => (
            <article className="insight-card" key={`${finding.issue}-${index}`}>
              <div className="insight-card-header">
                <span className="finding-badge">
                  诊断 {String(index + 1).padStart(2, "0")}
                </span>
                <span className="insight-icon">↗</span>
              </div>
              <h4>{finding.issue}</h4>
              <div className="insight-detail">
                <span>数据依据</span>
                <p>{finding.evidence}</p>
              </div>
              <div className="insight-detail interpretation">
                <span>优化建议</span>
                <p>{finding.recommendation}</p>
              </div>
            </article>
          ))}
        </div>
      </div>

      <div className="ai-report-columns">
        <div className="ai-report-block">
          <ReportBlockHeading
            index="02"
            title="渠道策略"
            description="根据规模、转化和收入表现差异化诊断"
          />
          <div className="opportunity-list">
            {report.channel_strategy.map((item) => (
              <article className="opportunity-item" key={item.channel}>
                <div className="opportunity-channel">
                  <span className="channel-dot" />
                  <strong>{item.channel}</strong>
                </div>
                <p>{item.strategy}</p>
                <small>{item.diagnosis}</small>
              </article>
            ))}
          </div>
        </div>

        <div className="ai-report-block">
          <ReportBlockHeading
            index="03"
            title="优先行动计划"
            description="明确目标指标与预期改善方向"
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
