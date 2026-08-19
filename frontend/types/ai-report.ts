export type ConfidenceLevel = "high" | "medium" | "low";

export interface ReportEvidence {
  evidence_ref: string[];
  display_values: string[];
  interpretation: string;
}

export interface KeyIssue {
  issue: string;
  evidence: ReportEvidence[];
  impact: string;
  confidence: ConfidenceLevel;
}

export interface PriorityAction {
  action: string;
  applicable_to: string;
  reason: string;
  target_metric: string;
}

export interface GrowthOpportunity {
  target: string;
  evidence: ReportEvidence[];
  recommendation: string;
}

export interface AIReport {
  core_conclusion: string;
  key_issues: KeyIssue[];
  priority_actions: PriorityAction[];
  opportunities: GrowthOpportunity[];
  limitations: string[];
}
