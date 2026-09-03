"use client";

import React, { useEffect, useState } from "react";
import { Header } from "../components/Header";
import { KPICards } from "../components/KPICards";
import { RecoveryFunnel } from "../components/RecoveryFunnel";
import { DemoScenariosBar } from "../components/DemoScenariosBar";
import { CasesTable } from "../components/CasesTable";
import { CaseDetailModal } from "../components/CaseDetailModal";
import { SafeguardsView } from "../components/SafeguardsView";
import { AnalyticsView } from "../components/AnalyticsView";
import { RecoverAIApiClient } from "../lib/api";
import { CANONICAL_ANALYTICS, CANONICAL_CASES, CANONICAL_OVERVIEW, CANONICAL_SAFEGUARDS } from "../lib/demo-data";
import { AnalyticsResponse, OverviewData, RecoveryCaseItem, SafeguardsResponse } from "../lib/types";
import { RefreshCw, AlertCircle } from "lucide-react";

export default function HomePage() {
  const [currentTab, setCurrentTab] = useState<"dashboard" | "cases" | "safeguards" | "analytics">("dashboard");
  const [isLiveApi, setIsLiveApi] = useState(false);
  const [isLoading, setIsLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  // Data states
  const [overview, setOverview] = useState<OverviewData>(CANONICAL_OVERVIEW);
  const [cases, setCases] = useState<RecoveryCaseItem[]>(CANONICAL_CASES);
  const [safeguards, setSafeguards] = useState<SafeguardsResponse>(CANONICAL_SAFEGUARDS);
  const [analytics, setAnalytics] = useState<AnalyticsResponse>(CANONICAL_ANALYTICS);

  // Selected case for investigation modal
  const [selectedCase, setSelectedCase] = useState<RecoveryCaseItem | null>(null);
  const [activeScenario, setActiveScenario] = useState<string | null>("all");

  const loadData = async () => {
    setIsLoading(true);
    setError(null);
    try {
      const [ovRes, casesRes, safeRes, anaRes] = await Promise.all([
        RecoverAIApiClient.getOverview(),
        RecoverAIApiClient.getCases({ page_size: 50 }),
        RecoverAIApiClient.getSafeguards(),
        RecoverAIApiClient.getAnalytics(),
      ]);

      setOverview(ovRes.data);
      setCases(casesRes.data.items);
      setSafeguards(safeRes.data);
      setAnalytics(anaRes.data);
      setIsLiveApi(ovRes.isLive);
    } catch (err: any) {
      console.warn("Using canonical fallback data", err);
      setIsLiveApi(false);
    } finally {
      setIsLoading(false);
    }
  };

  useEffect(() => {
    loadData();
  }, []);

  // Quick-Demo scenario selector
  const handleSelectScenario = (scenarioId: string) => {
    setActiveScenario(scenarioId);

    if (scenarioId === "all") {
      setCases(CANONICAL_CASES);
      return;
    }

    if (scenarioId === "temporary_success") {
      const match = CANONICAL_CASES.find((c) => c.decision_proposal.action_type === "RETRY_PAYMENT");
      if (match) {
        setCases([match, ...CANONICAL_CASES.filter((c) => c.case_id !== match.case_id)]);
        setSelectedCase(match);
      }
    } else if (scenarioId === "insufficient_funds") {
      const match = CANONICAL_CASES.find((c) => c.decision_proposal.action_type === "RETRY_LATER");
      if (match) {
        setCases([match, ...CANONICAL_CASES.filter((c) => c.case_id !== match.case_id)]);
        setSelectedCase(match);
      }
    } else if (scenarioId === "high_value") {
      const match = CANONICAL_CASES.find((c) => c.decision_proposal.action_type === "HUMAN_REVIEW");
      if (match) {
        setCases([match, ...CANONICAL_CASES.filter((c) => c.case_id !== match.case_id)]);
        setSelectedCase(match);
      }
    } else if (scenarioId === "unsafe_blocked") {
      const match = CANONICAL_CASES.find((c) => c.decision_proposal.action_type === "NO_ACTION");
      if (match) {
        setCases([match, ...CANONICAL_CASES.filter((c) => c.case_id !== match.case_id)]);
        setSelectedCase(match);
      }
    }
  };

  return (
    <div className="min-h-screen bg-canvas text-slate-100 flex flex-col font-sans">
      {/* Top Header */}
      <Header currentTab={currentTab} onSelectTab={setCurrentTab} isLiveApi={isLiveApi} />

      {/* Main Workspace */}
      <main className="flex-1 max-w-7xl w-full mx-auto px-4 sm:px-6 lg:px-8 py-8 space-y-8">
        {/* Error Alert if any */}
        {error && (
          <div className="p-4 rounded-lg bg-rose-500/10 border border-rose-500/30 flex items-center justify-between text-rose-300 text-sm">
            <div className="flex items-center space-x-2">
              <AlertCircle className="w-5 h-5 text-rose-400" />
              <span>{error}</span>
            </div>
            <button
              onClick={loadData}
              className="px-3 py-1 rounded bg-rose-500/20 hover:bg-rose-500/30 text-xs font-semibold"
            >
              Retry
            </button>
          </div>
        )}

        {/* Tab 1: Dashboard View */}
        {currentTab === "dashboard" && (
          <div className="space-y-8">
            {/* Top 6 KPI Cards */}
            <KPICards kpis={overview.kpis} />

            {/* 6-Stage Recovery Funnel */}
            <RecoveryFunnel funnel={overview.funnel} />

            {/* 4-Scenario Quick Demo Bar */}
            <DemoScenariosBar onSelectScenario={handleSelectScenario} activeScenario={activeScenario} />

            {/* Recent Cases Table */}
            <div>
              <div className="flex items-center justify-between mb-4">
                <div>
                  <h3 className="text-base font-semibold text-white tracking-tight">
                    Active Revenue Recovery Cases
                  </h3>
                  <p className="text-xs text-slate-400">
                    Inspecting real-time transaction failures, AI diagnosis inferences, and gateway verdicts
                  </p>
                </div>

                <button
                  onClick={loadData}
                  disabled={isLoading}
                  className="flex items-center space-x-1.5 px-3 py-1.5 rounded bg-surface border border-surface-border text-xs text-slate-300 hover:text-white hover:bg-surface-elevated transition-colors"
                >
                  <RefreshCw className={`w-3.5 h-3.5 ${isLoading ? "animate-spin text-brand-cyan" : ""}`} />
                  <span>Refresh Feed</span>
                </button>
              </div>

              <CasesTable
                cases={cases}
                onSelectCase={(item) => setSelectedCase(item)}
                isLoading={isLoading}
              />
            </div>
          </div>
        )}

        {/* Tab 2: Recovery Cases View */}
        {currentTab === "cases" && (
          <div className="space-y-6">
            <div className="flex items-center justify-between">
              <div>
                <h2 className="text-xl font-bold text-white tracking-tight">
                  Recovery Cases Directory
                </h2>
                <p className="text-xs text-slate-400">
                  Search, filter, and inspect payment transactions across all 7 lifecycle phases
                </p>
              </div>
            </div>

            <CasesTable
              cases={cases}
              onSelectCase={(item) => setSelectedCase(item)}
              isLoading={isLoading}
            />
          </div>
        )}

        {/* Tab 3: Safeguards & Audit View */}
        {currentTab === "safeguards" && <SafeguardsView safeguards={safeguards} />}

        {/* Tab 4: Analytics View */}
        {currentTab === "analytics" && <AnalyticsView analytics={analytics} />}
      </main>

      {/* Case Investigation Modal */}
      <CaseDetailModal caseItem={selectedCase} onClose={() => setSelectedCase(null)} />

      {/* Footer */}
      <footer className="border-t border-surface-border bg-canvas/90 py-6 mt-12 text-xs text-slate-400">
        <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 flex flex-col sm:flex-row items-center justify-between gap-4">
          <div className="flex items-center space-x-2">
            <span className="font-semibold text-slate-300">RecoverAI</span>
            <span>•</span>
            <span>AI Revenue Recovery Track</span>
            <span>•</span>
            <span className="text-slate-400 font-mono">Razorpay Buildathon</span>
          </div>

          <div className="text-[11px] text-slate-400 font-mono">
            Environment: Simulation Mode (rzp_test_ simulated) • Zero Live Credentials
          </div>
        </div>
      </footer>
    </div>
  );
}
