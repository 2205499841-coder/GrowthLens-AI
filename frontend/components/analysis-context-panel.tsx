import type { AnalysisContext } from "@/types/analysis";


const ANALYSIS_TYPE_LABELS = {
  user_growth: "用户增长分析",
  ecommerce_conversion: "电商转化分析",
  content_growth: "内容增长分析",
} as const;

const BUSINESS_TYPE_LABELS = {
  general: "通用业务",
  local_service: "本地生活服务",
  ecommerce: "电商业务",
  content: "内容业务",
} as const;

const DEFAULT_CONTEXT: AnalysisContext = {
  analysis_type: "user_growth",
  business_type: "general",
  recommended_metrics: [
    "注册用户数",
    "浏览率",
    "留资率",
    "预约率",
    "到店率",
    "成交率",
    "GMV",
    "客单价",
  ],
};

export function AnalysisContextPanel({
  context,
}: {
  context?: AnalysisContext;
}) {
  const resolvedContext = context ?? DEFAULT_CONTEXT;

  return (
    <article className="analysis-context-panel">
      <div className="analysis-context-primary">
        <div className="analysis-context-label-row">
          <span className="analysis-context-mark">AI</span>
          <span>智能识别分析场景</span>
        </div>
        <strong>
          {ANALYSIS_TYPE_LABELS[resolvedContext.analysis_type]}
        </strong>
        <code>{resolvedContext.analysis_type}</code>
      </div>

      <div className="analysis-context-business">
        <span>业务类型</span>
        <strong>
          {BUSINESS_TYPE_LABELS[resolvedContext.business_type]}
        </strong>
        <code>{resolvedContext.business_type}</code>
      </div>

      <div className="analysis-context-metrics">
        <span>建议重点关注</span>
        <div>
          {resolvedContext.recommended_metrics.map((metric) => (
            <span key={metric}>{metric}</span>
          ))}
        </div>
      </div>
    </article>
  );
}
