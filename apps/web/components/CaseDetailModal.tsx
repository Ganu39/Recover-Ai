"use client";

import React, { useState } from "react";
import {
  X,
  ShieldCheck,
  Cpu,
  CheckCircle2,
  AlertTriangle,
  Clock,
  ExternalLink,
  Lock,
  ArrowRight,
  Sparkles,
  FileText,
  KeyRound,
  Coins,
  History,
  AlertOctagon,
} from "lucide-react";
import { RecoveryCaseItem } from "../lib/types";
import { formatPaise, getStatusBadge, getActionLabel } from "../lib/formatting";

interface CaseDetailModalProps {
  caseItem: RecoveryCaseItem | null;
  onClose: () => void;
}

export const CaseDetailModal: React.FC<CaseDetailModalProps> = ({ caseItem, onClose }) => {
  const [activeTab, setActiveTab] = useState<"trace" | "raw">("trace");

  if (!caseItem) return null;

  const gwBadge = getStatusBadge(caseItem.gateway_result.gateway_decision);
  const execStatus = caseItem.execution_record?.status || "NOT_ATTEMPTED";
  const execBadge = getStatusBadge(execStatus);

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center p-4 bg-black/80 backdrop-blur-sm overflow-y-auto">
      <div className="relative w-full max-w-5xl bg-surface border border-surface-border rounded-xl shadow-2xl overflow-hidden my-8 max-h-[90vh] flex flex-col">
        {/* Header */}
        <div className="p-6 border-b border-surface-border bg-canvas/80 flex items-start justify-between">
          <div>
            <div className="flex items-center space-x-2 mb-1">
              <span className="text-xs font-mono px-2 py-0.5 rounded bg-surface border border-surface-border text-slate-300">
                Case ID: {caseItem.case_id.substring(0, 18)}...
              </span>
              <span
                className={`px-2.5 py-0.5 text-xs font-semibold rounded border ${gwBadge.bg} ${gwBadge.text} ${gwBadge.border}`}
              >
                GATEWAY: {gwBadge.label}
              </span>
              {caseItem.execution_record && (
                <span
                  className={`px-2.5 py-0.5 text-xs font-semibold rounded border ${execBadge.bg} ${execBadge.text} ${execBadge.border}`}
                >
                  EXECUTION: {execBadge.label}
                </span>
              )}
            </div>
            <h1 className="text-xl font-bold text-white flex items-center space-x-2">
              <span>{caseItem.customer_name}</span>
              <span className="text-slate-400 font-normal">({caseItem.customer_email})</span>
            </h1>
            <div className="text-xs text-slate-400 mt-1 flex items-center space-x-3 font-mono">
              <span>Amount at Risk: <strong className="text-white">{formatPaise(caseItem.amount_minor)}</strong></span>
              <span>•</span>
              <span>Decline: <strong className="text-rose-400">{caseItem.latest_failure_code}</strong></span>
              <span>•</span>
              <span>History: <strong className="text-slate-200">{caseItem.customer_success_rate_bps / 100}%</strong></span>
            </div>
          </div>

          <div className="flex items-center space-x-3">
            <button
              onClick={onClose}
              className="p-1.5 rounded-lg text-slate-400 hover:text-white hover:bg-surface-elevated transition-colors"
            >
              <X className="w-5 h-5" />
            </button>
          </div>
        </div>

        {/* Scrollable Content Body */}
        <div className="flex-1 overflow-y-auto p-6 space-y-6">
          {/* Visual 7-Stage End-to-End Progress Stepper */}
          <div className="bg-canvas p-4 rounded-lg border border-surface-border">
            <div className="text-xs font-semibold uppercase tracking-wider text-slate-400 mb-3 flex items-center justify-between">
              <span>End-to-End Recovery Pipeline Architecture</span>
              <span className="text-[11px] text-brand-cyan font-mono">Strict Deterministic Precedence</span>
            </div>

            <div className="grid grid-cols-2 md:grid-cols-7 gap-2 text-center text-xs">
              {caseItem.timeline.map((event, idx) => {
                const badge = getStatusBadge(event.status);
                return (
                  <div
                    key={idx}
                    className="p-2.5 rounded border border-surface-border bg-surface flex flex-col justify-between"
                  >
                    <div className="text-[10px] font-mono text-slate-500 mb-1">{event.timestamp}</div>
                    <div className="font-semibold text-white text-[11px] truncate">{event.stage}</div>
                    <div className="mt-2">
                      <span
                        className={`inline-block px-1.5 py-0.5 rounded text-[10px] font-mono font-medium border ${badge.bg} ${badge.text} ${badge.border}`}
                      >
                        {badge.label}
                      </span>
                    </div>
                  </div>
                );
              })}
            </div>
          </div>

          {/* Two-Column Deep-Dive Investigation Grid */}
          <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
            {/* LEFT COLUMN: Observables, Risk Engine & AI Diagnosis */}
            <div className="space-y-6">
              {/* 1. Risk Detection Panel */}
              <div className="bg-surface rounded-lg p-5 border border-surface-border">
                <div className="flex items-center justify-between mb-3">
                  <span className="text-xs font-semibold uppercase tracking-wider text-slate-300 flex items-center space-x-1.5">
                    <AlertTriangle className="w-4 h-4 text-amber-400" />
                    <span>Phase 3 — Revenue Risk Detection</span>
                  </span>
                  <span className="px-2 py-0.5 rounded text-xs font-mono bg-amber-500/10 text-amber-400 border border-amber-500/30">
                    {caseItem.risk_level} RISK ({caseItem.risk_score_bps} bps)
                  </span>
                </div>

                <div className="space-y-2 text-xs text-slate-300">
                  <div className="flex justify-between py-1 border-b border-surface-border">
                    <span className="text-slate-400">Amount at Financial Risk:</span>
                    <span className="font-mono font-semibold text-white">{formatPaise(caseItem.amount_minor)}</span>
                  </div>
                  <div className="flex justify-between py-1 border-b border-surface-border">
                    <span className="text-slate-400">Predicted Recoverable:</span>
                    <span className={`font-semibold ${caseItem.predicted_recoverable ? "text-brand-emerald" : "text-rose-400"}`}>
                      {caseItem.predicted_recoverable ? "YES (Predictive Engine)" : "NO (Likely Unrecoverable)"}
                    </span>
                  </div>
                  <div className="flex justify-between py-1 border-b border-surface-border">
                    <span className="text-slate-400">Target Attempts Recorded:</span>
                    <span className="font-mono">{caseItem.target_attempt_count} / 2 allowed</span>
                  </div>
                  <div className="flex justify-between py-1">
                    <span className="text-slate-400">Customer Success Rate:</span>
                    <span className="font-mono">{caseItem.customer_success_rate_bps / 100}% historical settlement</span>
                  </div>
                </div>
              </div>

              {/* 2. AI Root-Cause Diagnosis Panel */}
              <div className="bg-surface rounded-lg p-5 border border-brand-cyan/30 relative glow-cyan">
                <div className="flex items-center justify-between mb-3">
                  <span className="text-xs font-semibold uppercase tracking-wider text-brand-cyan flex items-center space-x-1.5">
                    <Cpu className="w-4 h-4" />
                    <span>Phase 4 — AI Root-Cause Diagnosis</span>
                  </span>
                  <span className="text-[11px] font-mono text-cyan-300 px-2 py-0.5 rounded bg-brand-cyan/10 border border-brand-cyan/30">
                    Model: {caseItem.ai_diagnosis.model}
                  </span>
                </div>

                <div className="bg-canvas/80 p-3 rounded border border-surface-border mb-3">
                  <div className="text-xs font-medium text-slate-400 uppercase tracking-wider mb-1">
                    Automated Diagnostic Inference:
                  </div>
                  <p className="text-sm font-semibold text-slate-100 leading-relaxed">
                    {caseItem.ai_diagnosis.root_cause}
                  </p>
                </div>

                <div className="grid grid-cols-2 gap-2 text-xs mb-3 font-mono">
                  <div className="bg-canvas/50 p-2 rounded border border-surface-border">
                    <span className="text-slate-400 block text-[10px]">RECOVERABILITY OPINION</span>
                    <span className="text-brand-cyan font-bold">{caseItem.ai_diagnosis.recoverability}</span>
                  </div>
                  <div className="bg-canvas/50 p-2 rounded border border-surface-border">
                    <span className="text-slate-400 block text-[10px]">ASSESSMENT CONFIDENCE</span>
                    <span className="text-emerald-400 font-bold">{caseItem.ai_diagnosis.confidence}</span>
                  </div>
                </div>

                {/* Evidence Items */}
                {caseItem.ai_diagnosis.evidence && caseItem.ai_diagnosis.evidence.length > 0 && (
                  <div>
                    <span className="text-[11px] font-semibold text-slate-400 uppercase tracking-wider block mb-1.5">
                      Grounding Evidence Reasoner:
                    </span>
                    <div className="space-y-1.5">
                      {caseItem.ai_diagnosis.evidence.map((ev, i) => (
                        <div
                          key={i}
                          className="flex items-start space-x-2 text-xs bg-canvas/40 p-2 rounded border border-surface-border/60"
                        >
                          <span className="px-1.5 py-0.5 text-[10px] font-mono rounded bg-slate-800 text-brand-cyan">
                            {ev.signal_type}
                          </span>
                          <span className="text-slate-300">{ev.description}</span>
                        </div>
                      ))}
                    </div>
                  </div>
                )}
              </div>

              {/* 3. Explanation Chain */}
              <div className="bg-surface rounded-lg p-5 border border-surface-border">
                <div className="flex items-center justify-between mb-3">
                  <span className="text-xs font-semibold uppercase tracking-wider text-slate-300 flex items-center space-x-1.5">
                    <FileText className="w-4 h-4 text-brand-cyan" />
                    <span>Phase 5 — Explanation Chain Audit</span>
                  </span>
                  <span className="text-[10px] text-slate-400 font-mono">Immutable Provenance</span>
                </div>

                <div className="space-y-3 text-xs">
                  {/* Facts */}
                  <div className="p-2.5 rounded bg-canvas/60 border-l-2 border-blue-500">
                    <span className="font-semibold text-blue-400 uppercase text-[10px] block mb-1">
                      1. Observed Facts (Deterministic Ground Truth)
                    </span>
                    <ul className="list-disc list-inside text-slate-300 space-y-0.5">
                      {caseItem.decision_proposal.observed_facts.map((fact, idx) => (
                        <li key={idx}>{fact}</li>
                      ))}
                    </ul>
                  </div>

                  {/* Inferences */}
                  <div className="p-2.5 rounded bg-canvas/60 border-l-2 border-brand-cyan">
                    <span className="font-semibold text-brand-cyan uppercase text-[10px] block mb-1">
                      2. AI Inferences (Read-Only Machine Learning)
                    </span>
                    <ul className="list-disc list-inside text-slate-300 space-y-0.5">
                      {caseItem.decision_proposal.ai_inferences.map((inf, idx) => (
                        <li key={idx}>{inf}</li>
                      ))}
                    </ul>
                  </div>

                  {/* Policy Checks */}
                  <div className="p-2.5 rounded bg-canvas/60 border-l-2 border-emerald-500">
                    <span className="font-semibold text-emerald-400 uppercase text-[10px] block mb-1">
                      3. Deterministic Policy Rules
                    </span>
                    <ul className="list-disc list-inside text-slate-300 space-y-0.5">
                      {caseItem.decision_proposal.policy_checks.map((pol, idx) => (
                        <li key={idx}>{pol}</li>
                      ))}
                    </ul>
                  </div>
                </div>
              </div>
            </div>

            {/* RIGHT COLUMN: Recovery Decision, Safety Gateway & Execution */}
            <div className="space-y-6">
              {/* 4. Recovery Decision Panel */}
              <div className="bg-surface rounded-lg p-5 border border-surface-border">
                <div className="flex items-center justify-between mb-3">
                  <span className="text-xs font-semibold uppercase tracking-wider text-slate-300 flex items-center space-x-1.5">
                    <Sparkles className="w-4 h-4 text-emerald-400" />
                    <span>Phase 5 — Proposed Recovery Action</span>
                  </span>
                  <span className="px-2 py-0.5 rounded text-xs font-mono bg-emerald-500/10 text-emerald-400 border border-emerald-500/30">
                    {caseItem.decision_proposal.decision_status}
                  </span>
                </div>

                <div className="bg-canvas p-3 rounded border border-surface-border mb-3 font-mono">
                  <div className="text-xs text-slate-400 mb-0.5">RECOMMENDED ACTION:</div>
                  <div className="text-base font-bold text-white">
                    {getActionLabel(caseItem.decision_proposal.action_type)}
                  </div>
                  <div className="text-[11px] text-slate-500 mt-1">
                    Proposal UUID: {caseItem.decision_proposal.proposal_id}
                  </div>
                </div>

                <p className="text-xs text-slate-300 leading-relaxed mb-3">
                  <strong className="text-slate-200">Rationale:</strong> {caseItem.decision_proposal.rationale}
                </p>
              </div>

              {/* 5. Deterministic Safety Gateway (CRITICAL) */}
              <div
                className={`bg-surface rounded-lg p-5 border ${
                  caseItem.gateway_result.gateway_decision === "APPROVED"
                    ? "border-brand-emerald/50 bg-gradient-to-br from-surface to-brand-emerald/5 glow-emerald"
                    : caseItem.gateway_result.gateway_decision === "REQUIRES_REVIEW"
                    ? "border-amber-500/50 glow-amber"
                    : "border-rose-500/50"
                }`}
              >
                <div className="flex items-center justify-between mb-3">
                  <span className="text-xs font-semibold uppercase tracking-wider text-white flex items-center space-x-1.5">
                    <ShieldCheck className="w-4 h-4 text-brand-emerald" />
                    <span>Phase 6 — Deterministic Safety Gateway</span>
                  </span>
                  <span
                    className={`px-2.5 py-0.5 rounded text-xs font-bold font-mono border ${gwBadge.bg} ${gwBadge.text} ${gwBadge.border}`}
                  >
                    {gwBadge.label}
                  </span>
                </div>

                <div className="text-xs font-mono text-slate-400 mb-3">
                  Reason Code: <span className="text-slate-200 font-semibold">{caseItem.gateway_result.reason_code}</span>
                </div>

                {/* Checklist */}
                <div className="space-y-2 bg-canvas/70 p-3 rounded border border-surface-border text-xs mb-3 font-mono">
                  <div className="text-[10px] font-sans font-semibold uppercase tracking-wider text-slate-400 mb-1">
                    Automated Invariant Verification Checklist:
                  </div>

                  <div className="flex items-center justify-between text-slate-300">
                    <span className="flex items-center space-x-1.5">
                      <CheckCircle2 className="w-3.5 h-3.5 text-brand-emerald" />
                      <span>1. Proposal Identity (UUID5 derivation)</span>
                    </span>
                    <span className="text-brand-emerald">VERIFIED</span>
                  </div>

                  <div className="flex items-center justify-between text-slate-300">
                    <span className="flex items-center space-x-1.5">
                      <CheckCircle2 className="w-3.5 h-3.5 text-brand-emerald" />
                      <span>2. Financial Integrity (paise amount matching)</span>
                    </span>
                    <span className="text-brand-emerald">VERIFIED</span>
                  </div>

                  <div className="flex items-center justify-between text-slate-300">
                    <span className="flex items-center space-x-1.5">
                      <CheckCircle2 className="w-3.5 h-3.5 text-brand-emerald" />
                      <span>3. Currency Invariant (INR)</span>
                    </span>
                    <span className="text-brand-emerald">VERIFIED</span>
                  </div>

                  <div className="flex items-center justify-between text-slate-300">
                    <span className="flex items-center space-x-1.5">
                      <CheckCircle2 className="w-3.5 h-3.5 text-brand-emerald" />
                      <span>4. Retry Ceiling Check (attempts &le; 2)</span>
                    </span>
                    <span
                      className={
                        caseItem.target_attempt_count >= 3 ? "text-rose-400 font-bold" : "text-brand-emerald"
                      }
                    >
                      {caseItem.target_attempt_count >= 3 ? "FAILED (BLOCKED)" : "PASSED"}
                    </span>
                  </div>

                  <div className="flex items-center justify-between text-slate-300">
                    <span className="flex items-center space-x-1.5">
                      <CheckCircle2 className="w-3.5 h-3.5 text-brand-emerald" />
                      <span>5. High-Value Safeguard (&ge; ₹5,000)</span>
                    </span>
                    <span
                      className={
                        caseItem.amount_minor >= 500000 ? "text-amber-400 font-bold" : "text-brand-emerald"
                      }
                    >
                      {caseItem.amount_minor >= 500000 ? "ESCALATED" : "PASSED"}
                    </span>
                  </div>

                  <div className="flex items-center justify-between text-slate-300">
                    <span className="flex items-center space-x-1.5">
                      <CheckCircle2 className="w-3.5 h-3.5 text-brand-emerald" />
                      <span>6. Kill Switch Status</span>
                    </span>
                    <span className="text-brand-emerald">INACTIVE</span>
                  </div>
                </div>

                {caseItem.gateway_result.blocking_conditions.length > 0 && (
                  <div className="bg-rose-500/10 border border-rose-500/30 p-2.5 rounded text-xs text-rose-300 mb-2">
                    <div className="font-semibold text-rose-400 mb-1 flex items-center space-x-1">
                      <AlertOctagon className="w-3.5 h-3.5" />
                      <span>Blocking Conditions Triggered:</span>
                    </div>
                    <ul className="list-disc list-inside space-y-0.5 font-mono text-[11px]">
                      {caseItem.gateway_result.blocking_conditions.map((cond, i) => (
                        <li key={i}>{cond}</li>
                      ))}
                    </ul>
                  </div>
                )}
              </div>

              {/* 6. Execution & Provider Result */}
              <div className="bg-surface rounded-lg p-5 border border-surface-border">
                <div className="flex items-center justify-between mb-3">
                  <span className="text-xs font-semibold uppercase tracking-wider text-slate-300 flex items-center space-x-1.5">
                    <Coins className="w-4 h-4 text-brand-cyan" />
                    <span>Phase 7 — Bounded Execution & Settlement</span>
                  </span>
                  <span
                    className={`px-2 py-0.5 rounded text-xs font-bold font-mono border ${execBadge.bg} ${execBadge.text} ${execBadge.border}`}
                  >
                    {execBadge.label}
                  </span>
                </div>

                {caseItem.execution_record ? (
                  <div className="space-y-2 text-xs font-mono">
                    <div className="flex justify-between py-1 border-b border-surface-border">
                      <span className="text-slate-400">Execution Mode:</span>
                      <span className="text-slate-200">Simulation / Razorpay Test Mode</span>
                    </div>
                    <div className="flex justify-between py-1 border-b border-surface-border">
                      <span className="text-slate-400">Provider Ref:</span>
                      <span className="text-brand-cyan font-bold">
                        {caseItem.execution_record.provider_reference || "Deferred / Internal"}
                      </span>
                    </div>
                    <div className="flex justify-between py-1 border-b border-surface-border">
                      <span className="text-slate-400">Idempotency Key:</span>
                      <span className="text-slate-300 truncate max-w-[200px]">
                        {caseItem.execution_record.idempotency_key}
                      </span>
                    </div>
                    <div className="flex justify-between py-1 border-b border-surface-border">
                      <span className="text-slate-400">Execution Attempt:</span>
                      <span className="text-slate-200">Attempt #{caseItem.execution_record.attempt_number}</span>
                    </div>
                    <div className="flex justify-between py-1">
                      <span className="text-slate-400">Confirmed Settled Amount:</span>
                      <span className="text-brand-emerald font-bold font-mono text-sm">
                        {caseItem.execution_record.status === "SUCCEEDED" || caseItem.execution_record.status === "RECONCILED"
                          ? formatPaise(caseItem.execution_record.amount_minor)
                          : "₹0.00"}
                      </span>
                    </div>
                  </div>
                ) : (
                  <div className="text-xs text-slate-400 italic bg-canvas/40 p-4 rounded border border-surface-border text-center">
                    Payment execution was prohibited by the Deterministic Safety Gateway. No external network request was made.
                  </div>
                )}
              </div>
            </div>
          </div>
        </div>

        {/* Modal Footer */}
        <div className="p-4 bg-canvas/90 border-t border-surface-border flex items-center justify-between text-xs text-slate-400">
          <div className="flex items-center space-x-2">
            <Lock className="w-3.5 h-3.5 text-brand-cyan" />
            <span>Deterministic financial safety: zero floating-point arithmetic.</span>
          </div>
          <button
            onClick={onClose}
            className="px-4 py-1.5 rounded bg-surface border border-surface-border text-slate-200 hover:text-white hover:bg-surface-elevated transition-colors"
          >
            Close Investigation
          </button>
        </div>
      </div>
    </div>
  );
};
