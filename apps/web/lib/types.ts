/**
 * Canonical frontend TypeScript contracts for RecoverAI.
 * Directly maps to backend FastAPI schemas.
 */

export interface KPIOverview {
  amount_at_risk_minor: number;
  amount_at_risk_display: string;
  authorized_amount_minor: number;
  authorized_amount_display: string;
  recovered_amount_minor: number;
  recovered_amount_display: string;
  deferred_amount_minor: number;
  deferred_amount_display: string;
  blocked_amount_minor: number;
  blocked_amount_display: string;
  review_amount_minor: number;
  review_amount_display: string;
  recovery_rate_bps: number;
  recovery_rate_display: string;
  total_cases_count: number;
  authorized_cases_count: number;
  blocked_cases_count: number;
  review_cases_count: number;
  attempted_cases_count: number;
  recovered_cases_count: number;
  deferred_cases_count: number;
}

export interface FunnelStage {
  stage: string;
  count: number;
  amount_minor: number;
  percentage: number;
}

export interface SafeguardsSummary {
  kill_switch_active: boolean;
  unauthorized_execution_rate_bps: number;
  duplicate_execution_rate_bps: number;
  financial_integrity_violation_rate_bps: number;
  blocked_cases_count: number;
  review_cases_count: number;
}

export interface OverviewData {
  environment: string;
  system_status: string;
  kpis: KPIOverview;
  funnel: FunnelStage[];
  safeguards_summary: SafeguardsSummary;
}

export interface TimelineEvent {
  stage: string;
  timestamp: string;
  title: string;
  description: string;
  status: string;
}

export interface AIDiagnosisData {
  root_cause: string;
  recoverability: string;
  recoverability_reason?: string;
  confidence: string;
  failure_category: string;
  evidence: Array<{
    signal_type: string;
    description: string;
    relevance: string;
  }>;
  observed_facts: string[];
  model: string;
  prompt_version: string;
}

export interface DecisionProposalData {
  proposal_id: string;
  action_type: string;
  decision_status: string;
  rationale: string;
  observed_facts: string[];
  ai_inferences: string[];
  policy_checks: string[];
}

export interface GatewayResultData {
  gateway_decision: string;
  reason_code: string;
  eligible_for_execution_layer: boolean;
  checks_evaluated: string[];
  checks_passed: string[];
  blocking_conditions: string[];
  audit_reference: string;
}

export interface ExecutionRecordData {
  execution_id: string;
  status: string;
  attempt_number: number;
  provider_reference: string | null;
  idempotency_key: string;
  amount_minor: number;
  created_at: string;
}

export interface RecoveryCaseItem {
  case_id: string;
  target_type: string;
  target_id: string;
  customer_id: string;
  customer_name: string;
  customer_email: string;
  amount_minor: number;
  currency: string;
  latest_failure_code: string;
  target_attempt_count: number;
  customer_success_rate_bps: number;
  subscription_status: string | null;
  risk_level: string;
  risk_score_bps: number;
  predicted_recoverable: boolean;
  ai_diagnosis: AIDiagnosisData;
  decision_proposal: DecisionProposalData;
  gateway_result: GatewayResultData;
  execution_record: ExecutionRecordData | null;
  timeline: TimelineEvent[];
}

export interface CasesResponse {
  total: number;
  page: number;
  page_size: number;
  items: RecoveryCaseItem[];
}

export interface SafeguardsResponse {
  kill_switch_active: boolean;
  payment_mode: string;
  gateway_version: string;
  policy_version: string;
  decision_version: string;
  retry_policy: {
    max_attempts_cap: number;
    high_value_threshold_minor: number;
    high_value_display: string;
    cooldown_period_seconds: number;
  };
  critical_safety_metrics: {
    unauthorized_execution_rate_bps: number;
    duplicate_execution_rate_bps: number;
    financial_integrity_violation_rate_bps: number;
    unsafe_authorization_rate_bps: number;
  };
  blocked_reasons_distribution: Record<string, number>;
}

export interface AnalyticsResponse {
  benchmark_summary: {
    total_evaluated_minor: number;
    total_evaluated_display: string;
    authorized_minor: number;
    authorized_display: string;
    recovered_minor: number;
    recovered_display: string;
    deferred_minor: number;
    deferred_display: string;
    blocked_minor: number;
    blocked_display: string;
    requires_review_minor: number;
    requires_review_display: string;
  };
  conversion_rates: {
    gross_recovery_rate_bps: number;
    gross_recovery_display: string;
    authorized_conversion_rate_bps: number;
    authorized_conversion_display: string;
  };
  action_breakdown: Array<{
    action: string;
    count: number;
    amount_minor: number;
    status: string;
  }>;
}
