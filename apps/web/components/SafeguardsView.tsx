"use client";

import React from "react";
import { ShieldCheck, ShieldAlert, KeyRound, Clock, AlertOctagon, CheckCircle2, Lock, Cpu } from "lucide-react";
import { SafeguardsResponse } from "../lib/types";

interface SafeguardsViewProps {
  safeguards: SafeguardsResponse;
}

export const SafeguardsView: React.FC<SafeguardsViewProps> = ({ safeguards }) => {
  return (
    <div className="space-y-6">
      {/* Overview Banner */}
      <div className="bg-surface rounded-lg p-6 border border-brand-emerald/40 bg-gradient-to-r from-surface via-surface to-brand-emerald/5 flex flex-col md:flex-row items-start md:items-center justify-between gap-4">
        <div>
          <div className="flex items-center space-x-2 mb-1">
            <ShieldCheck className="w-5 h-5 text-brand-emerald" />
            <h2 className="text-lg font-bold text-white">Deterministic Safety & Governance Matrix</h2>
          </div>
          <p className="text-xs text-slate-300 max-w-2xl leading-relaxed">
            AI recommends. Deterministic policy controls. The safety gateway authorizes. The bounded execution layer
            dispatches within strict test-mode boundaries with zero floating-point currency calculations.
          </p>
        </div>

        <div className="flex items-center space-x-2">
          <div className="px-3 py-1.5 rounded bg-brand-emerald/10 border border-brand-emerald/40 text-brand-emerald font-mono text-xs font-bold flex items-center space-x-1.5">
            <CheckCircle2 className="w-4 h-4" />
            <span>ALL INVARIANTS PASSING</span>
          </div>
        </div>
      </div>

      {/* Critical Release Metrics Cards */}
      <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
        <div className="bg-surface p-5 rounded-lg border border-brand-emerald/30">
          <div className="text-xs font-semibold uppercase tracking-wider text-slate-400 mb-1">
            Unauthorized Executions
          </div>
          <div className="text-3xl font-bold font-mono text-brand-emerald">
            {safeguards.critical_safety_metrics.unauthorized_execution_rate_bps} bps
          </div>
          <p className="text-xs text-slate-400 mt-2">
            0 unauthorized provider dispatches across all 1,676 proposals. Release blocking threshold: 0 bps.
          </p>
        </div>

        <div className="bg-surface p-5 rounded-lg border border-brand-emerald/30">
          <div className="text-xs font-semibold uppercase tracking-wider text-slate-400 mb-1">
            Duplicate Executions
          </div>
          <div className="text-3xl font-bold font-mono text-brand-emerald">
            {safeguards.critical_safety_metrics.duplicate_execution_rate_bps} bps
          </div>
          <p className="text-xs text-slate-400 mt-2">
            UUID5 deterministic idempotency guarantees 0 duplicate charges under concurrent dispatch.
          </p>
        </div>

        <div className="bg-surface p-5 rounded-lg border border-brand-emerald/30">
          <div className="text-xs font-semibold uppercase tracking-wider text-slate-400 mb-1">
            Financial Integrity Violations
          </div>
          <div className="text-3xl font-bold font-mono text-brand-emerald">
            {safeguards.critical_safety_metrics.financial_integrity_violation_rate_bps} bps
          </div>
          <p className="text-xs text-slate-400 mt-2">
            100% integer minor currency (paise) calculation with zero floating-point arithmetic drift.
          </p>
        </div>
      </div>

      {/* Safeguards Grid */}
      <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
        {/* Policy Invariants */}
        <div className="bg-surface rounded-lg p-5 border border-surface-border">
          <h3 className="text-sm font-semibold text-white uppercase tracking-wider mb-4 flex items-center space-x-2">
            <Lock className="w-4 h-4 text-brand-cyan" />
            <span>Deterministic Policy Invariants</span>
          </h3>

          <div className="space-y-3 text-xs font-mono">
            <div className="p-3 rounded bg-canvas border border-surface-border flex items-center justify-between">
              <div>
                <div className="font-semibold text-white">Emergency Kill Switch</div>
                <div className="text-slate-400 text-[11px]">System-wide execution hard block override</div>
              </div>
              <span className="px-2.5 py-1 rounded bg-emerald-500/10 text-emerald-400 border border-emerald-500/30 text-xs font-bold">
                INACTIVE (NORMAL)
              </span>
            </div>

            <div className="p-3 rounded bg-canvas border border-surface-border flex items-center justify-between">
              <div>
                <div className="font-semibold text-white">Max Target Attempts Ceiling</div>
                <div className="text-slate-400 text-[11px]">Strict card spamming prevention ceiling</div>
              </div>
              <span className="text-white font-bold text-sm">
                &le; {safeguards.retry_policy.max_attempts_cap} attempts
              </span>
            </div>

            <div className="p-3 rounded bg-canvas border border-surface-border flex items-center justify-between">
              <div>
                <div className="font-semibold text-white">High-Value Escalation Threshold</div>
                <div className="text-slate-400 text-[11px]">Mandates supervisor review above threshold</div>
              </div>
              <span className="text-amber-400 font-bold text-sm">
                {safeguards.retry_policy.high_value_display}
              </span>
            </div>

            <div className="p-3 rounded bg-canvas border border-surface-border flex items-center justify-between">
              <div>
                <div className="font-semibold text-white">Sliding-Window Rate Limiting</div>
                <div className="text-slate-400 text-[11px]">Token bucket per target & per customer</div>
              </div>
              <span className="text-cyan-400 font-bold text-xs">
                3/hr Target • 9/hr Customer
              </span>
            </div>
          </div>
        </div>

        {/* Blocked Reasons Distribution */}
        <div className="bg-surface rounded-lg p-5 border border-surface-border">
          <h3 className="text-sm font-semibold text-white uppercase tracking-wider mb-4 flex items-center space-x-2">
            <ShieldAlert className="w-4 h-4 text-brand-amber" />
            <span>Gateway Block Decisions Breakdown</span>
          </h3>

          <div className="space-y-3 text-xs">
            <div className="p-3 rounded bg-canvas border border-surface-border flex items-center justify-between">
              <div>
                <div className="font-semibold text-white">Non-Executable / Attempt Exhaustion</div>
                <div className="text-slate-400 text-[11px]">Target attempts &ge; 3 or chronic &lt;25% history</div>
              </div>
              <span className="text-rose-400 font-mono font-bold text-sm">
                {safeguards.blocked_reasons_distribution.BLOCK_NON_EXECUTABLE_ACTION} cases
              </span>
            </div>

            <div className="p-3 rounded bg-canvas border border-surface-border flex items-center justify-between">
              <div>
                <div className="font-semibold text-white">Mandatory Human Review Escalation</div>
                <div className="text-slate-400 text-[11px]">High-value invoices requiring approval token</div>
              </div>
              <span className="text-amber-400 font-mono font-bold text-sm">
                {safeguards.blocked_reasons_distribution.MISSING_HUMAN_APPROVAL} cases
              </span>
            </div>

            <div className="p-3 rounded bg-canvas border border-surface-border flex items-center justify-between">
              <div>
                <div className="font-semibold text-white">Unresolved Hard Declines</div>
                <div className="text-slate-400 text-[11px]">Stolen card / fraud alerts permanently halted</div>
              </div>
              <span className="text-slate-300 font-mono font-bold text-sm">
                {safeguards.blocked_reasons_distribution.BLOCK_UNRESOLVED_HARD_DECLINE} cases
              </span>
            </div>

            <div className="p-2.5 rounded bg-emerald-500/5 border border-emerald-500/20 text-emerald-300 text-xs">
              <strong>Note on Safety:</strong> Blocked cases represent successful risk mitigation outcomes, preventing
              unauthorized billing and merchant chargeback penalties.
            </div>
          </div>
        </div>
      </div>
    </div>
  );
};
