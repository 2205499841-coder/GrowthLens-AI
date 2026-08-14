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

export interface DatasetPlaceholderResult {
  dataset_type: "aggregate_metrics" | "unsupported";
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
  | DatasetPlaceholderResult;
