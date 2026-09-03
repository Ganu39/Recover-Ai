/**
 * Frontend API client for RecoverAI.
 * Connects to FastAPI backend and falls back cleanly to canonical frozen benchmark data.
 */

import { CANONICAL_ANALYTICS, CANONICAL_CASES, CANONICAL_OVERVIEW, CANONICAL_SAFEGUARDS } from "./demo-data";
import { AnalyticsResponse, CasesResponse, OverviewData, RecoveryCaseItem, SafeguardsResponse } from "./types";

const API_BASE_URL = process.env.NEXT_PUBLIC_API_URL || "http://localhost:8000";

export class RecoverAIApiClient {
  private static isApiAvailable: boolean | null = null;

  private static async fetchWithFallback<T>(endpoint: string, fallback: T): Promise<{ data: T; isLive: boolean }> {
    try {
      const controller = new AbortController();
      const timeoutId = setTimeout(() => controller.abort(), 1800); // 1.8s timeout
      const res = await fetch(`${API_BASE_URL}${endpoint}`, {
        signal: controller.signal,
        headers: { "Content-Type": "application/json" },
      });
      clearTimeout(timeoutId);

      if (res.ok) {
        const json = await res.json();
        this.isApiAvailable = true;
        return { data: json, isLive: true };
      }
    } catch {
      // Fallback on network failure or timeout
    }

    this.isApiAvailable = false;
    return { data: fallback, isLive: false };
  }

  static async getOverview(): Promise<{ data: OverviewData; isLive: boolean }> {
    return this.fetchWithFallback<OverviewData>("/api/v1/overview", CANONICAL_OVERVIEW);
  }

  static async getCases(params?: {
    search?: string;
    action_type?: string;
    gateway_decision?: string;
    execution_status?: string;
    page?: number;
    page_size?: number;
  }): Promise<{ data: CasesResponse; isLive: boolean }> {
    const query = new URLSearchParams();
    if (params?.search) query.append("search", params.search);
    if (params?.action_type) query.append("action_type", params.action_type);
    if (params?.gateway_decision) query.append("gateway_decision", params.gateway_decision);
    if (params?.execution_status) query.append("execution_status", params.execution_status);
    if (params?.page) query.append("page", params.page.toString());
    if (params?.page_size) query.append("page_size", params.page_size.toString());

    // Local filter fallback
    let filtered = [...CANONICAL_CASES];
    if (params?.search) {
      const q = params.search.toLowerCase();
      filtered = filtered.filter(
        (c) =>
          c.customer_name.toLowerCase().includes(q) ||
          c.customer_email.toLowerCase().includes(q) ||
          c.case_id.toLowerCase().includes(q) ||
          c.latest_failure_code.toLowerCase().includes(q)
      );
    }
    if (params?.action_type) {
      filtered = filtered.filter((c) => c.decision_proposal.action_type === params.action_type);
    }
    if (params?.gateway_decision) {
      filtered = filtered.filter((c) => c.gateway_result.gateway_decision === params.gateway_decision);
    }
    if (params?.execution_status) {
      filtered = filtered.filter((c) => c.execution_record?.status === params.execution_status);
    }

    const fallback: CasesResponse = {
      total: filtered.length,
      page: params?.page || 1,
      page_size: params?.page_size || 25,
      items: filtered,
    };

    const endpoint = `/api/v1/cases${query.toString() ? `?${query.toString()}` : ""}`;
    return this.fetchWithFallback<CasesResponse>(endpoint, fallback);
  }

  static async getCaseDetail(caseId: string): Promise<{ data: RecoveryCaseItem | null; isLive: boolean }> {
    const fallback = CANONICAL_CASES.find((c) => c.case_id === caseId) || CANONICAL_CASES[0];
    const res = await this.fetchWithFallback<RecoveryCaseItem>(`/api/v1/cases/${caseId}`, fallback);
    return res;
  }

  static async getSafeguards(): Promise<{ data: SafeguardsResponse; isLive: boolean }> {
    return this.fetchWithFallback<SafeguardsResponse>("/api/v1/safeguards", CANONICAL_SAFEGUARDS);
  }

  static async getAnalytics(): Promise<{ data: AnalyticsResponse; isLive: boolean }> {
    return this.fetchWithFallback<AnalyticsResponse>("/api/v1/analytics", CANONICAL_ANALYTICS);
  }

  static async runRazorpayDemo(): Promise<{ data: any; isLive: boolean }> {
    try {
      const res = await fetch(`${API_BASE_URL}/api/v1/demo/razorpay-recovery`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
      });
      if (res.ok) {
        const json = await res.json();
        return { data: json, isLive: true };
      }
    } catch (err) {
      console.warn("Demo API error", err);
    }

    return {
      data: {
        demo_type: "RAZORPAY_TEST_MODE_FLOW",
        status: "SUCCESS",
        case_id: "demo-rzp-case-1",
        target_id: "target-rzp-1",
        customer_name: "Aarav Sharma",
        customer_email: "aarav.sharma@example.com",
        amount_minor: 150000,
        amount_display: "₹1,500.00",
        currency: "INR",
        decline_code: "BAD_REQUEST_GATEWAY_TIMEOUT",
        gateway_decision: "APPROVED",
        provider: "Razorpay Test Mode",
        provider_operation: "POST /v1/orders",
        provider_reference: "order_test_805ecf8e-fdf4",
        initial_execution_status: "SUCCEEDED",
        reconciled_status: "RECONCILED",
        confirmed_recovered_minor: 150000,
        confirmed_recovered_display: "₹1,500.00",
        webhook_event: "order.paid",
        webhook_signature_verified: true,
        duplicate_protection_verified: true,
        pipeline_stages: [
          { stage: "1. Transaction Ingest", status: "COMPLETED", details: "Payment declined (Attempt #1)" },
          { stage: "2. Revenue Risk Engine", status: "COMPLETED", details: "₹1,500.00 exposure; 100% history (8500 bps recoverable)" },
          { stage: "3. AI Root-Cause Diagnosis", status: "COMPLETED", details: "Diagnosis: Temporary gateway timeout during authorization" },
          { stage: "4. Recovery Decision Agent", status: "COMPLETED", details: "Proposed RETRY_PAYMENT" },
          { stage: "5. Deterministic Safety Gateway", status: "APPROVED", details: "12/12 Safety Invariants PASSED. Gateway: APPROVED" },
          { stage: "6. Razorpay Test Mode Order Creation", status: "ORDER_CREATED", details: "Created official Order via POST /v1/orders (Awaiting Payment)" },
          { stage: "7. Webhook & State Reconciliation", status: "RECONCILED", details: "Verified HMAC-SHA256 webhook order.paid -> Confirmed Recovered ₹1,500.00" },
        ],
      },
      isLive: false,
    };
  }
}

