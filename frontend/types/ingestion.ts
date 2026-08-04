export interface DataIngestionSummary {
  used_sheet_name: string;
  detected_sheet_names: string[];
  recognized_field_count: number;
  total_required_field_count: number;
  missing_fields: string[];
  row_count: number;
  data_quality_status: "ready";
  field_mapping: Record<string, string>;
}
