"use client";

import React from "react";
import { ArrowRight, CheckCircle2, ShieldCheck, Cpu, AlertTriangle, PlayCircle } from "lucide-react";
import { FunnelStage } from "../lib/types";
import { formatPaise } from "../lib/formatting";

interface RecoveryFunnelProps {
  funnel: FunnelStage[];
}

export const RecoveryFunnel: React.FC<RecoveryFunnelProps> = ({ funnel }) => {
  const getStageIcon = (stage: string) => {
    switch (stage) {
      case "Failed Payments":
        return <AlertTriangle className="w-4 h-4 text-rose-400" />;
      case "Revenue at Risk":
        return <AlertTriangle className="w-4 h-4 text-amber-400" />;
      case "AI Diagnosed":
        return <Cpu className="w-4 h-4 text-brand-cyan" />;
      case "Gateway Authorized":
        return <ShieldCheck className="w-4 h-4 text-emerald-400" />;
      case "Execution Attempted":
        return <PlayCircle className="w-4 h-4 text-cyan-400" />;
      case "Confirmed Recovered":
        return <CheckCircle2 className="w-4 h-4 text-brand-emerald" />;
      default:
        return null;
    }
  };

  const getStageColor = (idx: number, isLast: boolean) => {
    if (isLast) return "border-brand-emerald/40 bg-brand-emerald/5";
    if (idx >= 3) return "border-brand-cyan/40 bg-brand-cyan/5";
    return "border-surface-border bg-surface";
  };

  return (
    <div className="bg-surface rounded-lg p-6 border border-surface-border">
      <div className="flex flex-col sm:flex-row sm:items-center justify-between pb-4 border-b border-surface-border mb-6">
        <div>
          <h2 className="text-base font-semibold text-white tracking-tight flex items-center space-x-2">
            <span>Deterministic Revenue Recovery Pipeline</span>
          </h2>
          <p className="text-xs text-slate-400 mt-0.5">
            End-to-end trace from failed payment detection to gateway authorization and confirmed settlement
          </p>
        </div>
        <div className="mt-2 sm:mt-0 flex items-center space-x-2 text-xs text-slate-400">
          <span className="inline-block w-2 h-2 rounded-full bg-brand-emerald"></span>
          <span>Conversion: ₹5.61L confirmed recovery (65.9% yield)</span>
        </div>
      </div>

      {/* Horizontal Connected Stepper */}
      <div className="grid grid-cols-1 md:grid-cols-6 gap-3 relative">
        {funnel.map((item, idx) => {
          const isLast = idx === funnel.length - 1;
          return (
            <div
              key={item.stage}
              className={`rounded-lg p-4 border transition-all relative ${getStageColor(idx, isLast)} ${
                isLast ? "glow-emerald" : ""
              }`}
            >
              <div className="flex items-center justify-between mb-2">
                <span className="text-[11px] font-mono text-slate-400 uppercase font-semibold tracking-wider">
                  Step 0{idx + 1}
                </span>
                {getStageIcon(item.stage)}
              </div>

              <div className="text-xs font-semibold text-slate-200 mb-1">{item.stage}</div>
              <div className="text-lg font-bold text-white font-mono">{formatPaise(item.amount_minor)}</div>

              <div className="flex items-center justify-between text-[11px] text-slate-400 mt-2 pt-2 border-t border-slate-800">
                <span>{item.count} cases</span>
                <span className="font-semibold text-slate-300">{item.percentage}%</span>
              </div>
            </div>
          );
        })}
      </div>
    </div>
  );
};
