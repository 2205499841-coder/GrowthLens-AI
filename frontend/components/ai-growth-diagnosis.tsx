import type { AIReport } from "@/types/ai-report";

export function AIGrowthDiagnosis({ report }: { report: AIReport }) {
  const primaryFinding = report.key_findings[0];
  const priorityAction = report.growth_actions[0];

  return (
    <div className="ai-diagnosis-grid">
      <DiagnosisCard
        index="01"
        label="当前增长阶段"
        tone="summary"
        value={report.summary}
      />
      <DiagnosisCard
        index="02"
        label="核心问题"
        value={primaryFinding?.issue ?? report.summary}
      />
      <DiagnosisCard
        index="03"
        label="关键证据"
        value={primaryFinding?.evidence ?? "当前报告暂未提供关键证据。"}
      />
      <DiagnosisCard
        index="04"
        label="优先建议"
        meta={priorityAction?.target_metric}
        tone="action"
        value={
          priorityAction?.action ??
          primaryFinding?.recommendation ??
          "当前报告暂未提供优先建议。"
        }
      />
    </div>
  );
}

function DiagnosisCard({
  index,
  label,
  meta,
  tone = "default",
  value,
}: {
  index: string;
  label: string;
  meta?: string;
  tone?: "default" | "summary" | "action";
  value: string;
}) {
  return (
    <article className={`ai-diagnosis-card ai-diagnosis-card-${tone}`}>
      <div className="ai-diagnosis-label">
        <span>{index}</span>
        <strong>{label}</strong>
      </div>
      <p>{value}</p>
      {meta ? <span className="ai-diagnosis-meta">目标：{meta}</span> : null}
    </article>
  );
}
