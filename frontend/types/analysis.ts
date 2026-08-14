import type { DataIngestionSummary } from "@/types/ingestion";

export interface AnalysisMetadata {
  file_name: string;
  data_start_date: string | null;
  data_end_date: string | null;
}

export interface DataQualitySummary {
  original_user_count: number;
  valid_user_count: number;
  removed_count: number;
  anomaly_count: number;
  data_completeness: number;
  issue_counts: Record<string, number>;
}

export interface UserCounts {
  registered_users: number;
  viewed_users: number | null;
  lead_users: number | null;
  appointment_users: number | null;
  visit_users: number | null;
  paid_users: number;
}

export interface ConversionRates {
  view_rate: number | null;
  lead_rate: number | null;
  appointment_rate: number | null;
  visit_rate: number | null;
  paid_rate: number;
}

export interface RevenueMetrics {
  gmv: number;
  average_order_value: number;
}

export interface GrowthMetrics {
  user_counts: UserCounts;
  conversion_rates: ConversionRates;
  revenue: RevenueMetrics;
}

export interface FunnelStage {
  key: string;
  label: string;
  user_count: number;
  conversion_rate_from_previous: number;
  dropoff_count: number;
  dropoff_rate: number;
}

export interface SchemaMappingSummary {
  mapping: Record<string, string>;
  source: "fixed" | "ai";
}

export type AnalysisType =
  | "user_growth"
  | "ecommerce_conversion"
  | "content_growth";

export type BusinessType =
  | "general"
  | "local_service"
  | "ecommerce"
  | "content";

export interface AnalysisContext {
  analysis_type: AnalysisType;
  business_type: BusinessType;
  recommended_metrics: string[];
}

export interface GrowthAnalysisResult {
  dataset_type: "user_level";
  analysis_status: "ready";
  metadata: AnalysisMetadata;
  data_ingestion: DataIngestionSummary;
  schema_mapping?: SchemaMappingSummary;
  analysis_context?: AnalysisContext;
  data_quality: DataQualitySummary;
  metrics: GrowthMetrics;
  funnel: {
    stages: FunnelStage[];
  };
  channels: Record<string, GrowthMetrics>;
}

export type AggregateMetricUnit =
  | "count"
  | "ratio"
  | "currency"
  | "currency_per_order"
  | "absolute"
  | "percentage_point";

export interface AggregateKpi {
  metric_key: string;
  label: string;
  value: number;
  unit: AggregateMetricUnit;
  aggregation: "sum" | "weighted_rate" | "non_additive";
  source: "total_row" | "single_row" | "safe_sum" | "derived";
}

export interface AggregateFunnelStage {
  metric_key: string;
  label: string;
  user_count: number;
  conversion_rate_from_previous: number | null;
  dropoff_count: number | null;
  yoy: number | null;
  mom: number | null;
  yoy_unit:
    | "ratio_change"
    | "percentage_point"
    | "absolute_change"
    | null;
  mom_unit:
    | "ratio_change"
    | "percentage_point"
    | "absolute_change"
    | null;
}

export interface DimensionPerformance {
  dimension_value: string;
  traffic_users: number | null;
  appointment_users: number | null;
  payment_users: number | null;
  conversion_rate: number | null;
  gmv: number | null;
  average_order_value: number | null;
  yoy: number | null;
  mom: number | null;
  yoy_unit:
    | "ratio_change"
    | "percentage_point"
    | "absolute_change"
    | null;
  mom_unit:
    | "ratio_change"
    | "percentage_point"
    | "absolute_change"
    | null;
}

export interface AggregateDiagnostic {
  diagnostic_type:
    | "high_traffic_low_conversion"
    | "high_conversion_low_traffic"
    | "yoy_decline"
    | "mom_decline"
    | "funnel_dropoff"
    | "gmv_payment_mismatch";
  title: string;
  evidence: string;
  severity: "high" | "medium" | "low";
  dimension_value: string | null;
  metric_key: string | null;
}

export interface AggregateOpportunity {
  opportunity_type:
    | "scale_high_conversion"
    | "high_gmv"
    | "conversion_improvement";
  title: string;
  evidence: string;
  dimension_value: string;
  metric_key: string;
}

export interface AggregateAnalysisResult {
  dataset_type: "aggregate_metrics";
  analysis_status: "ready" | "partial";
  metadata: AnalysisMetadata;
  dataset: {
    dataset_type: "aggregate_metrics";
    analysis_status: "ready" | "partial";
    sheet_name: string;
    header_rows: number[];
    grain: string[];
    report_period: string | null;
    filters: Record<string, string>;
  };
  dimensions: Array<{
    source_column: string;
    label: string;
    semantic_key: string;
    confidence: "high" | "medium" | "low";
  }>;
  metrics: Array<{
    source_column: string;
    label: string;
    metric_key: string;
    role:
      | "count_metric"
      | "rate_metric"
      | "amount_metric"
      | "comparison_metric";
    unit: AggregateMetricUnit;
    aggregation: "sum" | "weighted_rate" | "non_additive";
    confidence: "high" | "medium" | "low";
  }>;
  funnel_stages: Array<{
    metric_key: string;
    label: string;
    stage_order: number;
    source_column: string;
    confidence: "high" | "medium" | "low";
  }>;
  comparisons: Array<{
    source_column: string;
    label: string;
    comparison_type:
      | "yoy"
      | "mom"
      | "absolute_change"
      | "percentage_point_change";
    period: "yoy" | "mom" | null;
    unit:
      | "ratio_change"
      | "percentage_point"
      | "absolute_change"
      | "absolute_value";
    value_kind: "delta" | "baseline";
    target_metric_key: string | null;
    confidence: "high" | "medium" | "low";
  }>;
  data_quality: {
    row_count: number;
    detail_row_count: number;
    total_row_detected: boolean;
    recognized_column_count: number;
    unrecognized_columns: string[];
    warnings: string[];
  };
  kpis: AggregateKpi[];
  funnel: {
    scope_dimension_value: string | null;
    stages: AggregateFunnelStage[];
  };
  dimension_performance: DimensionPerformance[];
  diagnostics: AggregateDiagnostic[];
  opportunities: AggregateOpportunity[];
}

export interface DatasetPlaceholderResult {
  dataset_type: "unsupported";
  analysis_status: "unavailable";
  metadata: AnalysisMetadata;
  message: string;
  data_ingestion: null;
  schema_mapping: null;
  analysis_context: null;
  data_quality: null;
  metrics: null;
  funnel: null;
  channels: null;
}

export type AnalysisResult =
  | GrowthAnalysisResult
  | AggregateAnalysisResult
  | DatasetPlaceholderResult;
