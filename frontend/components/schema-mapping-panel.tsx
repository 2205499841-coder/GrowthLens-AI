import type { SchemaMappingSummary } from "@/types/analysis";


const STANDARD_FIELDS = [
  { key: "user_id", label: "用户标识" },
  { key: "channel", label: "来源渠道" },
  { key: "register_time", label: "注册时间" },
  { key: "view_time", label: "浏览时间" },
  { key: "lead_time", label: "线索时间" },
  { key: "appointment_time", label: "预约时间" },
  { key: "visit_time", label: "到店时间" },
  { key: "pay_time", label: "支付时间" },
  { key: "order_amount", label: "支付金额" },
] as const;

interface SchemaMappingPanelProps {
  fallbackMapping: Record<string, string>;
  schemaMapping?: SchemaMappingSummary;
}

export function SchemaMappingPanel({
  fallbackMapping,
  schemaMapping,
}: SchemaMappingPanelProps) {
  const source = schemaMapping?.source ?? "fixed";
  const mapping = schemaMapping?.mapping ?? fallbackMapping;
  const isAI = source === "ai";
  const sourceTitle = isAI ? "AI智能字段识别" : "标准模板识别";
  const sourceDescription = isAI
    ? "DeepSeek 已根据字段语义完成标准口径匹配"
    : "系统已通过标准字段与预设别名完成匹配";

  return (
    <article className={`schema-panel schema-panel-${source}`}>
      <div className="schema-source-summary">
        <span className="schema-source-mark" aria-hidden="true">
          {isAI ? "AI" : "FX"}
        </span>
        <div>
          <div className="schema-source-title-row">
            <h3>{sourceTitle}</h3>
            <span className="schema-source-badge">source: {source}</span>
          </div>
          <p>{sourceDescription}</p>
        </div>
      </div>

      <div className="schema-mapping-grid">
        {STANDARD_FIELDS.map((field) => (
          <div className="schema-mapping-item" key={field.key}>
            <div className="schema-standard-field">
              <code>{field.key}</code>
              <span>{field.label}</span>
            </div>
            <span className="schema-mapping-arrow" aria-hidden="true">
              →
            </span>
            <strong>{mapping[field.key] ?? "未识别"}</strong>
          </div>
        ))}
      </div>
    </article>
  );
}
