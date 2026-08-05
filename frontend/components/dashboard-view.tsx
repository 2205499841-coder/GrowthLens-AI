import type { ReactNode } from "react";

import { AIReportSection } from "@/components/ai-report-section";
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

interface DashboardViewProps {
  result: GrowthAnalysisResult;
}

interface SummaryCard {
  label: string;
  value: string;
  note?: string;
  tone?: "default" | "warning";
}

export function DashboardView({ result }: DashboardViewProps) {
  const quality = result.data_quality;
  const metrics = result.metrics;
  const channels = Object.entries(result.channels);

  const qualityCards: SummaryCard[] = [
    {
      label: "原始用户数",
      value: formatInteger(quality.original_user_count),
      note: "上传文件原始记录",
    },
    {
      label: "有效用户数",
      value: formatInteger(quality.valid_user_count),
      note: "完成 ID 清洗去重",
    },
    {
      label: "删除数量",
      value: formatInteger(quality.removed_count),
      note: "空 ID 与重复记录",
    },
    {
      label: "数据完整度",
      value: formatPercent(quality.data_completeness),
      note: "业务必填字段覆盖",
    },
    {
      label: "异常数据",
      value: formatInteger(quality.anomaly_count),
      note: "至少命中一项规则",
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
      <DashboardSection
        eyebrow="Data understanding"
        title="AI数据理解"
        description="展示上传字段如何对齐到 GrowthLens 标准分析口径。"
      >
        <SchemaMappingPanel
          fallbackMapping={result.data_ingestion.field_mapping}
          schemaMapping={result.schema_mapping}
        />
      </DashboardSection>

      <DashboardSection
        eyebrow="Data quality"
        title="数据质量摘要"
        description="上传数据经过标准化、去重和业务规则校验后的质量概况。"
      >
        <SummaryGrid cards={qualityCards} variant="quality" />
      </DashboardSection>

      <DashboardSection
        eyebrow="Performance overview"
        title="核心增长指标"
        description="所有指标由后端统一计算，前端仅负责展示分析结果。"
      >
        <SummaryGrid cards={metricCards} variant="metrics" />
      </DashboardSection>

      <DashboardSection
        eyebrow="User journey"
        title="用户增长漏斗"
        description="转化率与流失均按相邻阶段计算，阶段人数保持单调递减。"
      >
        <Funnel stages={result.funnel.stages} />
      </DashboardSection>

      <DashboardSection
        eyebrow="Channel performance"
        title="渠道分析"
        description="同时比较渠道规模、到店后的成交效率与收入贡献。"
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
