"use client";

import React from "react";
import { AlertCircle, ArrowUpRight, CheckCircle2, Clock, DollarSign, ShieldAlert, Sparkles } from "lucide-react";
import { KPIOverview } from "../lib/types";

interface KPICardsProps {
  kpis: KPIOverview;
}

export const KPICards: React.FC<KPICardsProps> = ({ kpis }) => {
  return (
    <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-6 gap-4">
      {/* 1. Revenue at Risk */}
      <div className="bg-surface rounded-lg p-5 border border-surface-border flex flex-col justify-between relative overflow-hidden">
        <div className="flex items-center justify-between text-slate-400 mb-2">
          <span className="text-xs font-semibold uppercase tracking-wider">Revenue at Risk</span>
          <AlertCircle className="w-4 h-4 text-rose-400" />
        </div>
        <div>
          <div className="text-2xl font-bold tracking-tight text-white font-mono">
            {kpis.amount_at_risk_display}
          </div>
          <div className="text-xs text-slate-400 mt-1 flex items-center space-x-1">
            <span className="font-semibold text-slate-300">{kpis.total_cases_count}</span>
            <span>failed transactions</span>
          </div>
        </div>
        <div className="w-full bg-slate-800 h-1 rounded mt-4">
          <div className="bg-rose-500 h-1 rounded" style={{ width: "100%" }}></div>
        </div>
      </div>

      {/* 2. Recoverable Revenue */}
      <div className="bg-surface rounded-lg p-5 border border-surface-border flex flex-col justify-between relative overflow-hidden">
        <div className="flex items-center justify-between text-slate-400 mb-2">
          <span className="text-xs font-semibold uppercase tracking-wider">Authorized Recoverable</span>
          <Sparkles className="w-4 h-4 text-brand-cyan" />
        </div>
        <div>
          <div className="text-2xl font-bold tracking-tight text-brand-cyan font-mono">
            {kpis.authorized_amount_display}
          </div>
          <div className="text-xs text-slate-400 mt-1 flex items-center space-x-1">
            <span className="font-semibold text-cyan-300">{kpis.authorized_cases_count}</span>
            <span>authorized cases</span>
          </div>
        </div>
        <div className="w-full bg-slate-800 h-1 rounded mt-4">
          <div className="bg-brand-cyan h-1 rounded" style={{ width: "41%" }}></div>
        </div>
      </div>

      {/* 3. Confirmed Recovered */}
      <div className="bg-surface rounded-lg p-5 border border-brand-emerald/40 bg-gradient-to-br from-surface via-surface to-brand-emerald/10 flex flex-col justify-between relative overflow-hidden glow-emerald">
        <div className="flex items-center justify-between text-slate-400 mb-2">
          <span className="text-xs font-semibold uppercase tracking-wider text-emerald-300">
            Confirmed Recovered
          </span>
          <CheckCircle2 className="w-4 h-4 text-brand-emerald" />
        </div>
        <div>
          <div className="text-2xl font-bold tracking-tight text-brand-emerald font-mono">
            {kpis.recovered_amount_display}
          </div>
          <div className="text-xs text-slate-300 mt-1 flex items-center space-x-1">
            <span className="font-semibold text-emerald-400">{kpis.recovered_cases_count}</span>
            <span>reconciled payments</span>
          </div>
        </div>
        <div className="w-full bg-slate-800 h-1 rounded mt-4">
          <div className="bg-brand-emerald h-1 rounded" style={{ width: "66%" }}></div>
        </div>
      </div>

      {/* 4. Recovery Conversion Rate */}
      <div className="bg-surface rounded-lg p-5 border border-surface-border flex flex-col justify-between relative overflow-hidden">
        <div className="flex items-center justify-between text-slate-400 mb-2">
          <span className="text-xs font-semibold uppercase tracking-wider">Recovery Yield</span>
          <ArrowUpRight className="w-4 h-4 text-brand-emerald" />
        </div>
        <div>
          <div className="text-2xl font-bold tracking-tight text-white font-mono">
            {kpis.recovery_rate_display}
          </div>
          <div className="text-xs text-slate-400 mt-1 flex items-center space-x-1">
            <span>of authorized recoverable</span>
          </div>
        </div>
        <div className="w-full bg-slate-800 h-1 rounded mt-4">
          <div className="bg-emerald-400 h-1 rounded" style={{ width: "65.9%" }}></div>
        </div>
      </div>

      {/* 5. Cooldown (Deferred) */}
      <div className="bg-surface rounded-lg p-5 border border-surface-border flex flex-col justify-between relative overflow-hidden">
        <div className="flex items-center justify-between text-slate-400 mb-2">
          <span className="text-xs font-semibold uppercase tracking-wider">Deferred Cooldown</span>
          <Clock className="w-4 h-4 text-cyan-400" />
        </div>
        <div>
          <div className="text-2xl font-bold tracking-tight text-slate-200 font-mono">
            {kpis.deferred_amount_display}
          </div>
          <div className="text-xs text-slate-400 mt-1 flex items-center space-x-1">
            <span className="font-semibold text-slate-300">{kpis.deferred_cases_count}</span>
            <span>insufficient funds cooldown</span>
          </div>
        </div>
        <div className="w-full bg-slate-800 h-1 rounded mt-4">
          <div className="bg-cyan-500 h-1 rounded" style={{ width: "34%" }}></div>
        </div>
      </div>

      {/* 6. Safeguard Hard Blocks */}
      <div className="bg-surface rounded-lg p-5 border border-surface-border flex flex-col justify-between relative overflow-hidden">
        <div className="flex items-center justify-between text-slate-400 mb-2">
          <span className="text-xs font-semibold uppercase tracking-wider">Safety Hard Blocks</span>
          <ShieldAlert className="w-4 h-4 text-brand-amber" />
        </div>
        <div>
          <div className="text-2xl font-bold tracking-tight text-brand-amber font-mono">
            {kpis.blocked_cases_count}
          </div>
          <div className="text-xs text-slate-400 mt-1 flex items-center space-x-1">
            <span className="font-semibold text-amber-400">{kpis.blocked_amount_display}</span>
            <span>spam retries stopped</span>
          </div>
        </div>
        <div className="w-full bg-slate-800 h-1 rounded mt-4">
          <div className="bg-brand-amber h-1 rounded" style={{ width: "43%" }}></div>
        </div>
      </div>
    </div>
  );
};
