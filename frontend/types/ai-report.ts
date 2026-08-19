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
  experiment?: string | null;
  target_metric: string;
}

export interface GrowthOpportunity {
  target: string;
  evidence: ReportEvidence[];
  recommendation: string;
}

export interface GrowthExplanation {
  growth_driver:
    | "traffic"
    | "conversion"
    | "combined"
    | "mixed"
    | "unavailable";
  why: string;
  main_contribution: string;
  evidence: ReportEvidence[];
}

export interface AIReport {
  core_conclusion: string;
  growth_explanation?: GrowthExplanation | null;
  key_issues: KeyIssue[];
  priority_actions: PriorityAction[];
  opportunities: GrowthOpportunity[];
  limitations: string[];
}
