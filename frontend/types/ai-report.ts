export type ExpectedDirection = "increase" | "decrease" | "maintain";

export interface KeyFinding {
  issue: string;
  evidence: string;
  recommendation: string;
}

export interface ChannelStrategy {
  channel: string;
  diagnosis: string;
  strategy: string;
}

export interface GrowthAction {
  action: string;
  target_metric: string;
  expected_direction: ExpectedDirection;
}

export interface AIReport {
  summary: string;
  key_findings: KeyFinding[];
  channel_strategy: ChannelStrategy[];
  growth_actions: GrowthAction[];
}
