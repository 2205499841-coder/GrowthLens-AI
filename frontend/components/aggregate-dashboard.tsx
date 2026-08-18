import type { ReactNode } from "react";

import {
  formatCurrency,
  formatCurrencyPrecise,
  formatInteger,
  formatOptionalInteger,
  formatOptionalPercent,
  formatPercent,
} from "@/lib/formatters";
import type {
  AggregateAnalysisResult,
  AggregateBusinessInsight,
  AggregateFunnelStage,
  AggregateKpi,
  DimensionFunnelDiagnosis,
  DimensionPerformance,
} from "@/types/analysis";


export function AggregateDashboard({
  result,
}: {
  result: AggregateAnalysisResult;
}) {
  const dimensionLabel = result.dimensions[0]?.label ?? "业务维度";
  const hasReliableOverallScope = result.data_quality.total_row_detected;

  return (
    <div className="dashboard-content aggregate-dashboard">
      {result.analysis_status === "partial" ? (
        <div className="aggregate-quality-notice">
          <strong>已生成部分可用分析</strong>
          <span>
            部分字段或表格结构尚未可靠识别，以下结果仅展示可确认的数据。
          </span>
        </div>
      ) : null}

      {!hasReliableOverallScope ? (
        <div className="aggregate-scope-notice">
          当前报表未提供可安全汇总的整体口径，以下优先展示{dimensionLabel}维度分析。
        </div>
      ) : null}

      {hasReliableOverallScope && result.kpis.length ? (
        <AggregateSection
          eyebrow="Performance overview"
          title="核心经营指标"
          description="根据当前报表可用字段动态展示；缺失指标不会以 0 代替。"
        >
          <div className="aggregate-kpi-grid">
            {result.kpis.map((kpi) => (
              <article className="summary-card aggregate-kpi-card" key={kpi.metric_key}>
                <p>{kpi.label}</p>
                <strong>{formatKpi(kpi)}</strong>
                <span>{kpiSourceLabel(kpi.source)}</span>
              </article>
            ))}
          </div>
        </AggregateSection>
      ) : null}

      {hasReliableOverallScope && result.funnel.stages.length ? (
        <AggregateSection
          eyebrow="Dynamic funnel"
          title="动态转化漏斗"
          description="按已识别字段的业务语义排序，允许跳过报表中不存在的节点。"
        >
          <AggregateFunnel stages={result.funnel.stages} />
        </AggregateSection>
      ) : null}

      <AggregateSection
        eyebrow="Dimension performance"
        title={`${dimensionLabel}表现`}
        description="保留明细行的真实值；整体转化率不对各维度转化率做简单平均。"
      >
        <PerformanceTable
          dimensionLabel={dimensionLabel}
          rows={result.dimension_performance}
        />
      </AggregateSection>

      <AggregateSection
        eyebrow="Funnel diagnosis"
        title={`${dimensionLabel}漏斗诊断摘要`}
        description="聚焦最终支付转化、阶段变化和主要正负向节点。"
      >
        <CategoryDiagnosisTable
          dimensionLabel={dimensionLabel}
          rows={result.dimension_funnel_diagnostics}
        />
      </AggregateSection>

      <AggregateSection
        eyebrow="Business insights"
        title="重点经营洞察"
        description="将同一维度的趋势、正向节点与风险信号合并，每个维度仅保留一条结论。"
      >
        <BusinessInsights
          dimensionLabel={dimensionLabel}
          insights={result.business_insights}
        />
      </AggregateSection>
    </div>
  );
}


function AggregateSection({
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


function AggregateFunnel({ stages }: { stages: AggregateFunnelStage[] }) {
  if (!stages.length) {
    return <EmptyPanel text="当前报表未识别到可计算的整体漏斗。" />;
  }
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
          const width = Math.max((stage.user_count / baseline) * 100, 24);
          return (
            <div className="funnel-row" key={stage.metric_key}>
              <div className="funnel-stage-label">
                <span>{String(index + 1).padStart(2, "0")}</span>
                <strong>{stage.label}</strong>
              </div>
              <div className="funnel-bar-area">
                <div className="funnel-bar" style={{ width: `${Math.min(width, 100)}%` }}>
                  <strong>{formatInteger(stage.user_count)}</strong>
                  <span>用户</span>
                </div>
              </div>
              <div className="funnel-stats">
                <div>
                  <span>转化率</span>
                  <strong>
                    {stage.conversion_rate_from_previous === null
                      ? "起始"
                      : formatPercent(stage.conversion_rate_from_previous)}
                  </strong>
                </div>
                <div>
                  <span>流失</span>
                  <strong>
                    {stage.dropoff_count === null
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


function PerformanceTable({
  dimensionLabel,
  rows,
}: {
  dimensionLabel: string;
  rows: DimensionPerformance[];
}) {
  if (!rows.length) {
    return <EmptyPanel text="当前报表未识别到可展示的维度明细。" />;
  }
  const availability = {
    traffic: rows.some((row) => row.traffic_users !== null),
    appointment: rows.some((row) => row.appointment_users !== null),
    payment: rows.some((row) => row.payment_users !== null),
    conversion: rows.some((row) => row.conversion_rate !== null),
    gmv: rows.some((row) => row.gmv !== null),
    averageOrder: rows.some((row) => row.average_order_value !== null),
    yoy: rows.some((row) => row.yoy !== null),
    mom: rows.some((row) => row.mom !== null),
  };
  const supplementalDefinitions = Array.from(
    new Map(
      rows
        .flatMap((row) => row.supplemental_outcomes)
        .map((metric) => [metric.metric_key, metric] as const),
    ).values(),
  );

  return (
    <article className="table-card aggregate-table-card">
      <div className="table-heading">
        <div>
          <h3>维度表现明细</h3>
          <p>仅展示报表中实际存在或可由分子分母计算的指标</p>
        </div>
        <span>{rows.length} 个明细项</span>
      </div>
      <div className="table-scroll">
        <table>
          <thead>
            <tr>
              <th>{dimensionLabel}</th>
              {availability.traffic ? <th>浏览用户</th> : null}
              {availability.appointment ? <th>预约用户</th> : null}
              {availability.payment ? <th>支付用户</th> : null}
              {supplementalDefinitions.map((metric) => (
                <th key={metric.metric_key}>{metric.label}</th>
              ))}
              {availability.conversion ? <th>支付转化率</th> : null}
              {availability.gmv ? <th>GMV</th> : null}
              {availability.averageOrder ? <th>客单价</th> : null}
              {availability.yoy ? <th>同比</th> : null}
              {availability.mom ? <th>环比</th> : null}
            </tr>
          </thead>
          <tbody>
            {rows.map((row) => (
              <tr key={row.dimension_value}>
                <td><strong>{row.dimension_value}</strong></td>
                {availability.traffic ? <td>{formatOptionalInteger(row.traffic_users)}</td> : null}
                {availability.appointment ? <td>{formatOptionalInteger(row.appointment_users)}</td> : null}
                {availability.payment ? <td>{formatOptionalInteger(row.payment_users)}</td> : null}
                {supplementalDefinitions.map((definition) => {
                  const metric = row.supplemental_outcomes.find(
                    (item) => item.metric_key === definition.metric_key,
                  );
                  return (
                    <td key={definition.metric_key}>
                      {metric ? formatInteger(metric.value) : "不可用"}
                    </td>
                  );
                })}
                {availability.conversion ? <td>{formatOptionalPercent(row.conversion_rate)}</td> : null}
                {availability.gmv ? <td>{formatOptionalCurrency(row.gmv)}</td> : null}
                {availability.averageOrder ? <td>{formatOptionalCurrencyPrecise(row.average_order_value)}</td> : null}
                {availability.yoy ? <td>{formatComparison(row.yoy, row.yoy_unit)}</td> : null}
                {availability.mom ? <td>{formatComparison(row.mom, row.mom_unit)}</td> : null}
              </tr>
            ))}
          </tbody>
        </table>
      </div>
    </article>
  );
}


function CategoryDiagnosisTable({
  dimensionLabel,
  rows,
}: {
  dimensionLabel: string;
  rows: DimensionFunnelDiagnosis[];
}) {
  if (!rows.length) {
    return <EmptyPanel text="当前报表没有可生成的维度漏斗摘要。" />;
  }
  return (
    <article className="table-card aggregate-table-card">
      <div className="table-scroll">
        <table className="diagnosis-summary-table">
          <thead>
            <tr>
              <th>{dimensionLabel}</th>
              <th>支付转化率</th>
              <th>同比</th>
              <th>环比</th>
              <th>最大改善节点</th>
              <th>最大拖累节点</th>
              <th>诊断级别</th>
            </tr>
          </thead>
          <tbody>
            {rows.map((row) => (
              <tr key={row.dimension_value}>
                <td><strong>{row.dimension_value}</strong></td>
                <td>{formatOptionalPercent(row.final_conversion_rate)}</td>
                <td>
                  {formatComparison(
                    row.final_conversion_yoy,
                    row.final_conversion_yoy_unit,
                  )}
                </td>
                <td>
                  {formatComparison(
                    row.final_conversion_mom,
                    row.final_conversion_mom_unit,
                  )}
                </td>
                <td>{formatMovement(row.best_improving_stage)}</td>
                <td>{formatMovement(row.largest_declining_stage)}</td>
                <td>
                  <span className={`diagnosis-level level-${row.diagnosis_level}`}>
                    {severityLabel(row.diagnosis_level)}
                  </span>
                </td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>
    </article>
  );
}


function BusinessInsights({
  dimensionLabel,
  insights,
}: {
  dimensionLabel: string;
  insights: AggregateBusinessInsight[];
}) {
  if (!insights.length) {
    return <EmptyPanel text="当前数据未达到高信号经营洞察的触发阈值。" />;
  }
  return (
    <article className="table-card aggregate-table-card">
      <div className="table-scroll">
        <table className="business-insights-table">
          <thead>
            <tr>
              <th>{dimensionLabel}</th>
              <th>核心判断</th>
              <th>关键证据</th>
              <th>优先级</th>
            </tr>
          </thead>
          <tbody>
            {insights.map((item, index) => (
              <tr key={`${item.dimension_value}-${index}`}>
                <td><strong>{item.dimension_value}</strong></td>
                <td className="insight-judgement-cell">{item.core_judgement}</td>
                <td className="insight-evidence-cell">
                  <ul>
                    {item.key_evidence.map((evidence) => (
                      <li key={evidence}>{evidence}</li>
                    ))}
                  </ul>
                </td>
                <td>
                  <span className={`diagnosis-level level-${item.priority}`}>
                    {severityLabel(item.priority)}
                  </span>
                </td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>
    </article>
  );
}


function formatMovement(
  movement: DimensionFunnelDiagnosis["best_improving_stage"],
): string {
  if (!movement) return "不可用";
  const period = movement.comparison === "yoy" ? "同比" : "环比";
  return `${shortStageLabel(movement.from_label)}→${shortStageLabel(movement.to_label)} ${period}${formatComparison(
    movement.delta,
    movement.unit,
  )}`;
}


function shortStageLabel(label: string): string {
  return label.replaceAll("用户", "").trim();
}


function formatKpi(kpi: AggregateKpi): string {
  if (kpi.unit === "count") return formatInteger(kpi.value);
  if (kpi.unit === "ratio" || kpi.unit === "percentage_point") {
    return formatPercent(kpi.value);
  }
  if (kpi.unit === "currency_per_order") {
    return formatCurrencyPrecise(kpi.value);
  }
  if (kpi.unit === "currency") return formatCurrency(kpi.value);
  return kpi.value.toLocaleString("zh-CN");
}


function kpiSourceLabel(source: AggregateKpi["source"]): string {
  const labels = {
    total_row: "来源：报表总计行",
    single_row: "来源：单一明细行",
    safe_sum: "来源：可加总金额",
    derived: "来源：分子 / 分母计算",
  };
  return labels[source];
}


function formatOptionalCurrency(value: number | null): string {
  return value === null ? "不可用" : formatCurrency(value);
}


function formatOptionalCurrencyPrecise(value: number | null): string {
  return value === null ? "不可用" : formatCurrencyPrecise(value);
}


function formatComparison(
  value: number | null,
  unit: DimensionPerformance["yoy_unit"] | DimensionPerformance["mom_unit"],
): string {
  if (value === null) return "不可用";
  const sign = value > 0 ? "+" : "";
  if (unit === "percentage_point") {
    return `${sign}${(value * 100).toFixed(2)} 个百分点`;
  }
  if (unit === "absolute_change") {
    return `${sign}${value.toLocaleString("zh-CN")}`;
  }
  return `${sign}${formatPercent(value)}`;
}


function severityLabel(
  severity: DimensionFunnelDiagnosis["diagnosis_level"],
): string {
  return {
    high_priority: "高优先级",
    attention: "需关注",
    stable: "表现稳定",
    improving: "改善明显",
  }[severity];
}


function EmptyPanel({ text }: { text: string }) {
  return <div className="aggregate-empty-panel">{text}</div>;
}
