export type Confidence = "high" | "medium" | "low";
export type ExpectedDirection = "increase" | "decrease" | "maintain";

export interface KeyInsight {
  title: string;
  evidence: string;
  interpretation: string;
  confidence: Confidence;
}

export interface ChannelOpportunity {
  channel: string;
  opportunity: string;
  evidence: string;
  confidence: Confidence;
}

export interface GrowthAction {
  action: string;
  target_metric: string;
  expected_direction: ExpectedDirection;
}

export interface AIReport {
  summary: string;
  key_insights: KeyInsight[];
  channel_opportunities: ChannelOpportunity[];
  growth_actions: GrowthAction[];
  limitations: string[];
}
