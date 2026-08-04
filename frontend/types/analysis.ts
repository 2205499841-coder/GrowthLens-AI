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
  viewed_users: number;
  lead_users: number;
  appointment_users: number;
  visit_users: number;
  paid_users: number;
}

export interface ConversionRates {
  view_rate: number;
  lead_rate: number;
  appointment_rate: number;
  visit_rate: number;
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

export interface GrowthAnalysisResult {
  metadata: AnalysisMetadata;
  data_ingestion: DataIngestionSummary;
  data_quality: DataQualitySummary;
  metrics: GrowthMetrics;
  funnel: {
    stages: FunnelStage[];
  };
  channels: Record<string, GrowthMetrics>;
}
