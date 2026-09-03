"use client";

import React, { useState } from "react";
import { Search, ChevronRight, Filter, ShieldCheck, AlertTriangle, CheckCircle2, Clock } from "lucide-react";
import { RecoveryCaseItem } from "../lib/types";
import { formatPaise, getStatusBadge, getActionLabel } from "../lib/formatting";

interface CasesTableProps {
  cases: RecoveryCaseItem[];
  onSelectCase: (caseItem: RecoveryCaseItem) => void;
  isLoading?: boolean;
}

export const CasesTable: React.FC<CasesTableProps> = ({ cases, onSelectCase, isLoading = false }) => {
  const [searchTerm, setSearchTerm] = useState("");
  const [actionFilter, setActionFilter] = useState("ALL");
  const [gatewayFilter, setGatewayFilter] = useState("ALL");

  const filteredCases = cases.filter((item) => {
    const q = searchTerm.toLowerCase();
    const matchesSearch =
      !searchTerm ||
      item.customer_name.toLowerCase().includes(q) ||
      item.customer_email.toLowerCase().includes(q) ||
      item.latest_failure_code.toLowerCase().includes(q) ||
      item.case_id.toLowerCase().includes(q);

    const matchesAction =
      actionFilter === "ALL" || item.decision_proposal.action_type === actionFilter;

    const matchesGateway =
      gatewayFilter === "ALL" || item.gateway_result.gateway_decision === gatewayFilter;

    return matchesSearch && matchesAction && matchesGateway;
  });

  return (
    <div className="bg-surface rounded-lg border border-surface-border overflow-hidden">
      {/* Table Header Controls */}
      <div className="p-4 border-b border-surface-border flex flex-col md:flex-row md:items-center justify-between gap-3">
        <div className="flex items-center space-x-2 flex-1 max-w-md">
          <div className="relative w-full">
            <Search className="w-4 h-4 text-slate-400 absolute left-3 top-1/2 -translate-y-1/2" />
            <input
              type="text"
              placeholder="Search by customer, email, decline code, or case ID..."
              value={searchTerm}
              onChange={(e) => setSearchTerm(e.target.value)}
              className="w-full pl-9 pr-4 py-2 bg-canvas text-xs text-white placeholder-slate-500 rounded border border-surface-border focus:outline-none focus:border-brand-cyan transition-colors font-mono"
            />
          </div>
        </div>

        {/* Filters */}
        <div className="flex items-center space-x-2">
          <div className="flex items-center space-x-1.5 text-xs text-slate-400">
            <Filter className="w-3.5 h-3.5" />
            <span>Action:</span>
          </div>
          <select
            value={actionFilter}
            onChange={(e) => setActionFilter(e.target.value)}
            className="bg-canvas border border-surface-border rounded text-xs text-slate-200 px-2.5 py-1.5 focus:outline-none focus:border-brand-cyan"
          >
            <option value="ALL">All Actions</option>
            <option value="RETRY_PAYMENT">Smart Retry</option>
            <option value="RETRY_LATER">Retry Later (Cooldown)</option>
            <option value="REQUEST_PAYMENT_METHOD_UPDATE">Payment Method Update</option>
            <option value="SUBSCRIPTION_RECOVERY_WORKFLOW">Subscription Workflow</option>
            <option value="HUMAN_REVIEW">Human Review</option>
            <option value="NO_ACTION">No Action (Blocked)</option>
          </select>

          <div className="flex items-center space-x-1.5 text-xs text-slate-400 ml-2">
            <span>Gateway:</span>
          </div>
          <select
            value={gatewayFilter}
            onChange={(e) => setGatewayFilter(e.target.value)}
            className="bg-canvas border border-surface-border rounded text-xs text-slate-200 px-2.5 py-1.5 focus:outline-none focus:border-brand-cyan"
          >
            <option value="ALL">All Verdicts</option>
            <option value="APPROVED">APPROVED</option>
            <option value="BLOCKED">BLOCKED</option>
            <option value="REQUIRES_REVIEW">REQUIRES_REVIEW</option>
          </select>
        </div>
      </div>

      {/* Table */}
      <div className="overflow-x-auto">
        <table className="w-full text-left text-xs">
          <thead className="bg-canvas/60 text-slate-400 font-semibold uppercase tracking-wider border-b border-surface-border">
            <tr>
              <th className="py-3 px-4">Customer</th>
              <th className="py-3 px-4">Amount at Risk</th>
              <th className="py-3 px-4">Decline Code</th>
              <th className="py-3 px-4">AI Root-Cause Diagnosis</th>
              <th className="py-3 px-4">Action Proposal</th>
              <th className="py-3 px-4">Safety Gateway</th>
              <th className="py-3 px-4">Execution Result</th>
              <th className="py-3 px-4 text-right">Audit</th>
            </tr>
          </thead>
          <tbody className="divide-y divide-surface-border font-mono">
            {isLoading ? (
              <tr>
                <td colSpan={8} className="py-12 text-center text-slate-400">
                  <div className="flex items-center justify-center space-x-2">
                    <span className="w-4 h-4 border-2 border-brand-cyan border-t-transparent rounded-full animate-spin"></span>
                    <span className="font-sans">Loading recovery cases from API...</span>
                  </div>
                </td>
              </tr>
            ) : filteredCases.length === 0 ? (
              <tr>
                <td colSpan={8} className="py-12 text-center text-slate-400 font-sans">
                  No recovery cases match the selected filter criteria.
                </td>
              </tr>
            ) : (
              filteredCases.map((item) => {
                const gwBadge = getStatusBadge(item.gateway_result.gateway_decision);
                const execStatus = item.execution_record?.status || "NOT_ATTEMPTED";
                const execBadge = getStatusBadge(execStatus);

                return (
                  <tr
                    key={item.case_id}
                    onClick={() => onSelectCase(item)}
                    className="hover:bg-surface-elevated/80 transition-colors cursor-pointer group"
                  >
                    {/* Customer */}
                    <td className="py-3.5 px-4 font-sans">
                      <div className="font-semibold text-white group-hover:text-brand-cyan transition-colors">
                        {item.customer_name}
                      </div>
                      <div className="text-[11px] text-slate-400 font-mono truncate max-w-[150px]">
                        {item.customer_email}
                      </div>
                    </td>

                    {/* Amount */}
                    <td className="py-3.5 px-4">
                      <div className="font-bold text-white">{formatPaise(item.amount_minor)}</div>
                      <div className="text-[10px] text-slate-400">
                        {item.customer_success_rate_bps / 100}% customer history
                      </div>
                    </td>

                    {/* Decline Code */}
                    <td className="py-3.5 px-4">
                      <span className="px-2 py-0.5 rounded bg-slate-800 text-rose-300 border border-rose-500/20 text-[11px]">
                        {item.latest_failure_code}
                      </span>
                      <div className="text-[10px] text-slate-500 mt-0.5">Attempt {item.target_attempt_count}/2</div>
                    </td>

                    {/* AI Diagnosis */}
                    <td className="py-3.5 px-4 font-sans max-w-xs">
                      <div className="text-xs text-slate-200 line-clamp-1">
                        {item.ai_diagnosis.root_cause}
                      </div>
                      <div className="flex items-center space-x-1 mt-0.5 text-[10px] text-brand-cyan">
                        <span>Confidence: {item.ai_diagnosis.confidence}</span>
                        <span>•</span>
                        <span>{item.ai_diagnosis.recoverability}</span>
                      </div>
                    </td>

                    {/* Proposal Action */}
                    <td className="py-3.5 px-4 font-sans">
                      <span className="font-medium text-slate-200 text-xs">
                        {getActionLabel(item.decision_proposal.action_type)}
                      </span>
                      <div className="text-[10px] text-slate-400 font-mono">
                        {item.decision_proposal.decision_status}
                      </div>
                    </td>

                    {/* Gateway */}
                    <td className="py-3.5 px-4">
                      <span
                        className={`inline-flex items-center px-2 py-0.5 rounded text-[11px] font-semibold border ${gwBadge.bg} ${gwBadge.text} ${gwBadge.border}`}
                      >
                        {gwBadge.label}
                      </span>
                      <div className="text-[10px] text-slate-400 mt-0.5 font-sans truncate max-w-[120px]">
                        {item.gateway_result.reason_code}
                      </div>
                    </td>

                    {/* Execution */}
                    <td className="py-3.5 px-4">
                      {item.execution_record ? (
                        <div>
                          <span
                            className={`inline-flex items-center px-2 py-0.5 rounded text-[11px] font-semibold border ${execBadge.bg} ${execBadge.text} ${execBadge.border}`}
                          >
                            {execBadge.label}
                          </span>
                          <div className="text-[10px] text-slate-400 mt-0.5 font-mono">
                            {item.execution_record.provider_reference || "No ref"}
                          </div>
                        </div>
                      ) : (
                        <span className="text-[11px] text-slate-500 italic">No Execution</span>
                      )}
                    </td>

                    {/* Action */}
                    <td className="py-3.5 px-4 text-right">
                      <button
                        onClick={(e) => {
                          e.stopPropagation();
                          onSelectCase(item);
                        }}
                        className="inline-flex items-center space-x-1 text-xs text-brand-cyan hover:text-cyan-300 font-sans group-hover:translate-x-0.5 transition-transform"
                      >
                        <span>Investigate</span>
                        <ChevronRight className="w-3.5 h-3.5" />
                      </button>
                    </td>
                  </tr>
                );
              })
            )}
          </tbody>
        </table>
      </div>

      {/* Footer */}
      <div className="p-3 bg-canvas/40 border-t border-surface-border text-xs text-slate-400 flex items-center justify-between">
        <div>
          Showing <span className="font-semibold text-slate-200">{filteredCases.length}</span> recovery cases
        </div>
        <div className="text-[11px] text-slate-400">
          Click any row to open the complete 7-stage Case Investigation & Safety Gateway Trace
        </div>
      </div>
    </div>
  );
};
