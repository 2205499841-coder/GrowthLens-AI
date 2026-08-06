import type { ReactNode } from "react";

import { AIGrowthDiagnosis } from "@/components/ai-growth-diagnosis";
import { AIReportSection } from "@/components/ai-report-section";
import { AnalysisContextPanel } from "@/components/analysis-context-panel";
import { ChannelBarChart } from "@/components/channel-bar-chart";
import { SchemaMappingPanel } from "@/components/schema-mapping-panel";
import {
  formatCurrency,
  formatCurrencyPrecise,
  formatInteger,
  formatPercent,
} from "@/lib/formatters";
import type {
  FunnelStage,
  GrowthAnalysisResult,
  GrowthMetrics,
} from "@/types/analysis";
import type { AIReport } from "@/types/ai-report";

interface DashboardViewProps {
  aiReport: AIReport | null;
  onAIReportGenerated: (report: AIReport) => void;
  result: GrowthAnalysisResult;
}

interface SummaryCard {
  label: string;
  value: string;
  note?: string;
  tone?: "default" | "warning";
}

export function DashboardView({
  aiReport,
  onAIReportGenerated,
  result,
}: DashboardViewProps) {
  const quality = result.data_quality;
  const metrics = result.metrics;
  const channels = Object.entries(result.channels);

  const qualityCards: SummaryCard[] = [
    {
      label: "原始用户数",
      value: formatInteger(quality.original_user_count),
      note: "数据源记录总量",
    },
    {
      label: "有效用户数",
      value: formatInteger(quality.valid_user_count),
      note: "完成标准化与去重",
    },
    {
      label: "删除数量",
      value: formatInteger(quality.removed_count),
      note: "无效及重复记录",
    },
    {
      label: "数据完整度",
      value: formatPercent(quality.data_completeness),
      note: "业务必填字段覆盖",
    },
    {
      label: "异常数据",
      value: formatInteger(quality.anomaly_count),
      note: "需要关注的质量问题",
      tone: quality.anomaly_count > 0 ? "warning" : "default",
    },
  ];

  const metricCards: SummaryCard[] = [
    {
      label: "注册用户数",
      value: formatInteger(metrics.user_counts.registered_users),
      note: "漏斗起始用户",
    },
    {
      label: "成交用户数",
      value: formatInteger(metrics.user_counts.paid_users),
      note: "完成有效支付",
    },
    {
      label: "GMV",
      value: formatCurrency(metrics.revenue.gmv),
      note: "有效成交金额",
    },
    {
      label: "客单价",
      value: formatCurrencyPrecise(metrics.revenue.average_order_value),
      note: "GMV / 成交用户",
    },
    {
      label: "成交率",
      value: formatPercent(metrics.conversion_rates.paid_rate),
      note: "成交用户 / 到店用户",
    },
  ];

  return (
    <div className="dashboard-content">
      {aiReport ? (
        <DashboardSection
          eyebrow="AI growth diagnosis"
          title="AI 增长诊断"
          description="汇总当前增长阶段、核心问题与优先行动，帮助快速进入决策。"
        >
          <AIGrowthDiagnosis report={aiReport} />
        </DashboardSection>
      ) : null}

      <DashboardSection
        eyebrow="Data understanding"
        title="AI 数据理解"
        description="自动识别业务场景与字段语义，建立统一、可信的增长分析口径。"
      >
        <div className="data-understanding-stack">
          <AnalysisContextPanel context={result.analysis_context} />
          <SchemaMappingPanel
            fallbackMapping={result.data_ingestion.field_mapping}
            schemaMapping={result.schema_mapping}
          />
        </div>
      </DashboardSection>

      <DashboardSection
        eyebrow="Data quality"
        title="数据质量摘要"
        description="识别缺失、重复与异常记录，评估当前数据的分析可信度。"
      >
        <SummaryGrid cards={qualityCards} variant="quality" />
      </DashboardSection>

      <DashboardSection
        eyebrow="Performance overview"
        title="核心增长指标"
        description="聚合用户规模、转化效率与收入表现，掌握业务增长基本盘。"
      >
        <SummaryGrid cards={metricCards} variant="metrics" />
      </DashboardSection>

      <DashboardSection
        eyebrow="User journey"
        title="用户增长漏斗"
        description="追踪关键业务阶段的转化与流失，快速定位增长瓶颈。"
      >
        <Funnel stages={result.funnel.stages} />
      </DashboardSection>

      <DashboardSection
        eyebrow="Channel performance"
        title="渠道分析"
        description="对比渠道规模、转化效率与收入贡献，识别高潜增长机会。"
      >
        <div className="chart-grid">
          <ChannelBarChart
            channels={channels}
            metric="registered_users"
          />
          <ChannelBarChart channels={channels} metric="paid_rate" />
        </div>
        <ChannelTable channels={channels} />
      </DashboardSection>

      <AIReportSection
        analysis={result}
        onReportGenerated={onAIReportGenerated}
        key={[
          result.metadata.file_name,
          result.data_quality.valid_user_count,
          result.metrics.revenue.gmv,
        ].join("-")}
      />
    </div>
  );
}

function DashboardSection({
  children,
  description,
  eyebrow,
  title,
}: {
  children: ReactNode;
  description: string;
  eyebrow: string;
  title: string;
}) {
  return (
    <section className="dashboard-section">
      <div className="section-heading">
        <div>
          <p className="section-kicker">{eyebrow}</p>
          <h2>{title}</h2>
        </div>
        <p>{description}</p>
      </div>
      {children}
    </section>
  );
}

function SummaryGrid({
  cards,
  variant,
}: {
  cards: SummaryCard[];
  variant: "quality" | "metrics";
}) {
  return (
    <div className={`summary-grid summary-grid-${variant}`}>
      {cards.map((card) => (
        <article
          className={`summary-card summary-card-${card.tone ?? "default"}`}
          key={card.label}
        >
          <p>{card.label}</p>
          <strong>{card.value}</strong>
          {card.note ? <span>{card.note}</span> : null}
        </article>
      ))}
    </div>
  );
}

function Funnel({ stages }: { stages: FunnelStage[] }) {
  const baseline = stages[0]?.user_count || 1;

  return (
    <div className="funnel-panel">
      <div className="funnel-scale">
        <span>阶段</span>
        <span>用户规模</span>
        <span>阶段表现</span>
      </div>
      <div className="funnel-list">
        {stages.map((stage, index) => {
          const width = Math.max((stage.user_count / baseline) * 100, 28);
          return (
            <div className="funnel-row" key={stage.key}>
              <div className="funnel-stage-label">
                <span>{String(index + 1).padStart(2, "0")}</span>
                <strong>{stage.label}</strong>
              </div>
              <div className="funnel-bar-area">
                <div
                  className="funnel-bar"
                  style={{ width: `${width}%` }}
                >
                  <strong>{formatInteger(stage.user_count)}</strong>
                  <span>用户</span>
                </div>
              </div>
              <div className="funnel-stats">
                <div>
                  <span>转化率</span>
                  <strong>
                    {index === 0
                      ? "起始"
                      : formatPercent(
                          stage.conversion_rate_from_previous,
                        )}
                  </strong>
                </div>
                <div>
                  <span>流失</span>
                  <strong>
                    {index === 0
                      ? "—"
                      : formatInteger(stage.dropoff_count)}
                  </strong>
                </div>
              </div>
            </div>
          );
        })}
      </div>
    </div>
  );
}

function ChannelTable({
  channels,
}: {
  channels: Array<[string, GrowthMetrics]>;
}) {
  return (
    <article className="table-card">
      <div className="table-heading">
        <div>
          <h3>渠道明细</h3>
          <p>精确值用于渠道投放与后续运营复盘</p>
        </div>
        <span>{channels.length} 个渠道</span>
      </div>
      <div className="table-scroll">
        <table>
          <thead>
            <tr>
              <th>渠道名称</th>
              <th>注册用户</th>
              <th>预约用户</th>
              <th>到店率</th>
              <th>成交率</th>
              <th>GMV</th>
            </tr>
          </thead>
          <tbody>
            {channels.map(([channel, channelMetrics]) => (
              <tr key={channel}>
                <td>
                  <span className="channel-name">
                    <span className="channel-dot" />
                    {channel}
                  </span>
                </td>
                <td>
                  {formatInteger(
                    channelMetrics.user_counts.registered_users,
                  )}
                </td>
                <td>
                  {formatInteger(
                    channelMetrics.user_counts.appointment_users,
                  )}
                </td>
                <td>
                  {formatPercent(
                    channelMetrics.conversion_rates.visit_rate,
                  )}
                </td>
                <td>
                  <span className="rate-pill">
                    {formatPercent(
                      channelMetrics.conversion_rates.paid_rate,
                    )}
                  </span>
                </td>
                <td>{formatCurrency(channelMetrics.revenue.gmv)}</td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>
    </article>
  );
}
