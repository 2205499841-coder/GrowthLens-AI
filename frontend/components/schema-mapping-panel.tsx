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
  const mapping = schemaMapping?.mapping ?? fallbackMapping;
  const recognizedFieldCount = Object.values(mapping).filter(Boolean).length;

  return (
    <details className="schema-panel">
      <summary className="schema-source-summary">
        <div>
          <h3>字段识别详情</h3>
          <p>查看业务字段与分析口径的对应关系</p>
        </div>
        <span className="schema-source-badge">
          已识别 {recognizedFieldCount} 个字段
        </span>
      </summary>

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
            <strong>{mapping[field.key] ?? "暂未匹配"}</strong>
          </div>
        ))}
      </div>
    </details>
  );
}
