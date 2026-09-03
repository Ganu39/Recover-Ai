"use client";

import React from "react";
import { BarChart3, TrendingUp, CheckCircle2, DollarSign, PieChart, Layers } from "lucide-react";
import { AnalyticsResponse } from "../lib/types";
import { formatPaise, getActionLabel } from "../lib/formatting";

interface AnalyticsViewProps {
  analytics: AnalyticsResponse;
}

export const AnalyticsView: React.FC<AnalyticsViewProps> = ({ analytics }) => {
  const { benchmark_summary, conversion_rates, action_breakdown } = analytics;

  return (
    <div className="space-y-6">
      {/* Top Conversion Metrics */}
      <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
        <div className="bg-surface rounded-lg p-6 border border-brand-emerald/40 bg-gradient-to-br from-surface to-brand-emerald/10 glow-emerald">
          <div className="flex items-center justify-between text-slate-300 mb-2">
            <span className="text-xs font-semibold uppercase tracking-wider text-emerald-400">
              Authorized Recovery Yield
            </span>
            <TrendingUp className="w-5 h-5 text-brand-emerald" />
          </div>
          <div className="text-4xl font-bold font-mono text-white mb-2">
            {conversion_rates.authorized_conversion_display}
          </div>
          <p className="text-xs text-slate-300 leading-relaxed">
            Of the ₹8.52L in revenue authorized by the Deterministic Safety Gateway, <strong>₹5.61L</strong> was
            successfully recovered and reconciled into merchant balance.
          </p>
        </div>

        <div className="bg-surface rounded-lg p-6 border border-surface-border">
          <div className="flex items-center justify-between text-slate-300 mb-2">
            <span className="text-xs font-semibold uppercase tracking-wider text-slate-400">
              Gross Portfolio Recovery Yield
            </span>
            <BarChart3 className="w-5 h-5 text-brand-cyan" />
          </div>
          <div className="text-4xl font-bold font-mono text-white mb-2">
            {conversion_rates.gross_recovery_display}
          </div>
          <p className="text-xs text-slate-400 leading-relaxed">
            Net recovered percentage across the total ₹53.11L gross failed payment pool, accounting for non-retryable hard blocks
            and human review holds.
          </p>
        </div>
      </div>

      {/* Financial Exposure Ledger Breakdown */}
      <div className="bg-surface rounded-lg p-6 border border-surface-border">
        <h3 className="text-sm font-semibold text-white uppercase tracking-wider mb-4 flex items-center space-x-2">
          <Layers className="w-4 h-4 text-brand-cyan" />
          <span>Financial Exposure & Allocation Ledger</span>
        </h3>

        <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-3 gap-4 font-mono text-xs">
          <div className="p-4 rounded bg-canvas border border-surface-border">
            <span className="text-slate-400 block text-[11px] mb-1">TOTAL EVALUATED POOL</span>
            <span className="text-xl font-bold text-white">{benchmark_summary.total_evaluated_display}</span>
            <div className="text-[10px] text-slate-500 mt-1">100% of failed payment volume</div>
          </div>

          <div className="p-4 rounded bg-canvas border border-brand-cyan/40">
            <span className="text-cyan-400 block text-[11px] mb-1">GATEWAY AUTHORIZED</span>
            <span className="text-xl font-bold text-brand-cyan">{benchmark_summary.authorized_display}</span>
            <div className="text-[10px] text-slate-400 mt-1">16.1% approved as safe to execute</div>
          </div>

          <div className="p-4 rounded bg-canvas border border-brand-emerald/40 bg-brand-emerald/5">
            <span className="text-emerald-400 block text-[11px] mb-1">CONFIRMED RECOVERED</span>
            <span className="text-xl font-bold text-brand-emerald">{benchmark_summary.recovered_display}</span>
            <div className="text-[10px] text-emerald-400 mt-1">65.9% of authorized converted</div>
          </div>

          <div className="p-4 rounded bg-canvas border border-cyan-500/30">
            <span className="text-cyan-300 block text-[11px] mb-1">DEFERRED IN COOLDOWN</span>
            <span className="text-xl font-bold text-slate-200">{benchmark_summary.deferred_display}</span>
            <div className="text-[10px] text-slate-400 mt-1">Scheduled for payroll replenishment</div>
          </div>

          <div className="p-4 rounded bg-canvas border border-rose-500/30">
            <span className="text-rose-400 block text-[11px] mb-1">POLICY HARD BLOCKS</span>
            <span className="text-xl font-bold text-rose-300">{benchmark_summary.blocked_display}</span>
            <div className="text-[10px] text-slate-400 mt-1">Protected from spam retries</div>
          </div>

          <div className="p-4 rounded bg-canvas border border-amber-500/30">
            <span className="text-amber-400 block text-[11px] mb-1">HUMAN SUPERVISOR QUEUE</span>
            <span className="text-xl font-bold text-amber-300">{benchmark_summary.requires_review_display}</span>
            <div className="text-[10px] text-slate-400 mt-1">High-value enterprise invoices</div>
          </div>
        </div>
      </div>

      {/* Action Distribution Table */}
      <div className="bg-surface rounded-lg p-6 border border-surface-border">
        <h3 className="text-sm font-semibold text-white uppercase tracking-wider mb-4 flex items-center space-x-2">
          <PieChart className="w-4 h-4 text-brand-cyan" />
          <span>Recovery Action Distribution & Economic Volume</span>
        </h3>

        <div className="overflow-x-auto">
          <table className="w-full text-left text-xs font-mono">
            <thead className="bg-canvas text-slate-400 font-semibold uppercase tracking-wider border-b border-surface-border">
              <tr>
                <th className="py-3 px-4">Intervention Action</th>
                <th className="py-3 px-4">Case Count</th>
                <th className="py-3 px-4">Economic Volume</th>
                <th className="py-3 px-4">Pipeline Status</th>
              </tr>
            </thead>
            <tbody className="divide-y divide-surface-border">
              {action_breakdown.map((row) => (
                <tr key={row.action} className="hover:bg-surface-elevated/50 transition-colors">
                  <td className="py-3 px-4 font-sans font-semibold text-white">
                    {getActionLabel(row.action)}
                  </td>
                  <td className="py-3 px-4 text-slate-200">{row.count} cases</td>
                  <td className="py-3 px-4 font-bold text-white">{formatPaise(row.amount_minor)}</td>
                  <td className="py-3 px-4">
                    <span
                      className={`inline-block px-2 py-0.5 rounded text-[11px] font-bold ${
                        row.status === "EXECUTED"
                          ? "bg-emerald-500/10 text-emerald-400 border border-emerald-500/30"
                          : row.status === "DEFERRED"
                          ? "bg-cyan-500/10 text-cyan-400 border border-cyan-500/30"
                          : row.status === "ESCALATED"
                          ? "bg-amber-500/10 text-amber-400 border border-amber-500/30"
                          : "bg-rose-500/10 text-rose-400 border border-rose-500/30"
                      }`}
                    >
                      {row.status}
                    </span>
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      </div>
    </div>
  );
};
