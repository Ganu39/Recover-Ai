"use client";

import React from "react";
import { CheckCircle2, Clock, AlertTriangle, ShieldAlert, Sparkles } from "lucide-react";

interface DemoScenariosBarProps {
  onSelectScenario: (scenarioId: string) => void;
  activeScenario: string | null;
}

export const DemoScenariosBar: React.FC<DemoScenariosBarProps> = ({
  onSelectScenario,
  activeScenario,
}) => {
  const scenarios = [
    {
      id: "all",
      label: "All Scenarios",
      desc: "View full canonical benchmark (1,676 cases)",
      icon: <Sparkles className="w-4 h-4 text-slate-300" />,
      tag: "All Cases",
      color: "border-surface-border text-slate-300",
      badge: "1,676 Total",
    },
    {
      id: "temporary_success",
      label: "1. Recoverable Network Timeout",
      desc: "High history + transient decline → Smart Retry → Succeeded",
      icon: <CheckCircle2 className="w-4 h-4 text-emerald-400" />,
      tag: "RETRY_PAYMENT",
      color: "border-brand-emerald/40 text-emerald-300 bg-brand-emerald/5",
      badge: "Succeeded",
    },
    {
      id: "insufficient_funds",
      label: "2. Insufficient Funds (Cooldown)",
      desc: "Temporary balance deficit → Deferred 24h Cooldown",
      icon: <Clock className="w-4 h-4 text-cyan-400" />,
      tag: "RETRY_LATER",
      color: "border-brand-cyan/40 text-cyan-300 bg-brand-cyan/5",
      badge: "Deferred",
    },
    {
      id: "high_value",
      label: "3. High-Value Escalation",
      desc: "₹12,500 exceeds ₹5k threshold → Mandatory Human Review",
      icon: <AlertTriangle className="w-4 h-4 text-amber-400" />,
      tag: "HUMAN_REVIEW",
      color: "border-amber-500/40 text-amber-300 bg-amber-500/5",
      badge: "Requires Review",
    },
    {
      id: "unsafe_blocked",
      label: "4. Exhausted Retry Block",
      desc: "3 attempts exhausted → Gateway BLOCKS card spamming",
      icon: <ShieldAlert className="w-4 h-4 text-rose-400" />,
      tag: "NO_ACTION",
      color: "border-rose-500/40 text-rose-300 bg-rose-500/5",
      badge: "Safety Blocked",
    },
    {
      id: "razorpay_live_flow",
      label: "5. Razorpay Test Mode",
      desc: "Live Orders API (POST /v1/orders) → HMAC Webhook → Reconciled",
      icon: <Sparkles className="w-4 h-4 text-brand-cyan" />,
      tag: "RAZORPAY_TEST_MODE",
      color: "border-brand-cyan/40 text-cyan-300 bg-brand-cyan/10",
      badge: "Razorpay Demo",
    },
  ];

  return (
    <div className="bg-surface rounded-lg p-4 border border-surface-border mb-6">
      <div className="flex items-center justify-between mb-3">
        <div className="flex items-center space-x-2">
          <span className="w-2 h-2 rounded-full bg-brand-cyan animate-pulse"></span>
          <span className="text-xs font-semibold uppercase tracking-wider text-slate-300">
            Buildathon Judge Quick-Demo Flow
          </span>
        </div>
        <span className="text-[11px] text-slate-400 font-medium">
          Click any representative scenario to inspect full end-to-end evidence
        </span>
      </div>

      <div className="grid grid-cols-1 md:grid-cols-5 gap-2.5">
        {scenarios.map((s) => {
          const isSelected = activeScenario === s.id;
          return (
            <button
              key={s.id}
              onClick={() => onSelectScenario(s.id)}
              className={`text-left p-3 rounded-md border transition-all flex flex-col justify-between ${
                isSelected
                  ? "ring-2 ring-brand-cyan bg-surface-elevated border-brand-cyan"
                  : "bg-surface hover:bg-surface-elevated border-surface-border"
              }`}
            >
              <div>
                <div className="flex items-center justify-between mb-1.5">
                  <div className="flex items-center space-x-1.5">{s.icon}</div>
                  <span className="text-[10px] font-mono px-1.5 py-0.5 rounded bg-slate-800 text-slate-300">
                    {s.badge}
                  </span>
                </div>
                <div className="text-xs font-semibold text-white truncate">{s.label}</div>
                <p className="text-[11px] text-slate-400 mt-1 line-clamp-2 leading-relaxed">{s.desc}</p>
              </div>
            </button>
          );
        })}
      </div>
    </div>
  );
};
