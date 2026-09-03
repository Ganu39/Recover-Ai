"use client";

import React from "react";
import { ShieldCheck, Cpu, Activity, BarChart3, Database, Layers } from "lucide-react";

interface HeaderProps {
  currentTab: "dashboard" | "cases" | "safeguards" | "analytics";
  onSelectTab: (tab: "dashboard" | "cases" | "safeguards" | "analytics") => void;
  isLiveApi: boolean;
}

export const Header: React.FC<HeaderProps> = ({ currentTab, onSelectTab, isLiveApi }) => {
  return (
    <header className="border-b border-surface-border bg-canvas/90 backdrop-blur sticky top-0 z-40">
      {/* Top Banner Bar */}
      <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8">
        <div className="flex items-center justify-between h-16">
          {/* Brand */}
          <div className="flex items-center space-x-3">
            <div className="w-9 h-9 rounded bg-brand-cyan/20 border border-brand-cyan/40 flex items-center justify-center text-brand-cyan shadow-sm glow-cyan">
              <Cpu className="w-5 h-5" />
            </div>
            <div>
              <div className="flex items-center space-x-2">
                <span className="text-xl font-bold tracking-tight text-white">RecoverAI</span>
                <span className="px-2 py-0.5 text-[10px] uppercase tracking-wider font-semibold rounded bg-brand-cyan/10 text-brand-cyan border border-brand-cyan/30">
                  Razorpay Buildathon
                </span>
              </div>
              <p className="text-xs text-slate-400 font-medium">AI Revenue Recovery Command Center</p>
            </div>
          </div>

          {/* Center Badges */}
          <div className="hidden md:flex items-center space-x-3">
            <div className="flex items-center space-x-1.5 px-3 py-1 rounded bg-surface border border-surface-border text-xs text-slate-300">
              <span className="relative flex h-2 w-2">
                <span className="animate-ping absolute inline-flex h-full w-full rounded-full bg-brand-emerald opacity-75"></span>
                <span className="relative inline-flex rounded-full h-2 w-2 bg-brand-emerald"></span>
              </span>
              <span className="font-medium text-slate-200">Simulation / Razorpay Test Mode</span>
            </div>

            <div className="flex items-center space-x-1.5 px-3 py-1 rounded bg-surface border border-surface-border text-xs text-slate-300">
              <ShieldCheck className="w-3.5 h-3.5 text-brand-emerald" />
              <span>0 bps Unsafe Executions</span>
            </div>

            <div className="flex items-center space-x-1.5 px-2.5 py-1 rounded bg-surface border border-surface-border text-xs">
              <span className={`w-2 h-2 rounded-full ${isLiveApi ? "bg-emerald-400" : "bg-cyan-400"}`} />
              <span className="text-slate-300 font-mono text-[11px]">
                {isLiveApi ? "FastAPI Connected" : "Local Benchmark Cache"}
              </span>
            </div>
          </div>

          {/* Navigation Tabs */}
          <nav className="flex space-x-1">
            <button
              onClick={() => onSelectTab("dashboard")}
              className={`flex items-center space-x-1.5 px-3 py-1.5 rounded text-sm font-medium transition-colors ${
                currentTab === "dashboard"
                  ? "bg-brand-cyan/20 text-brand-cyan border border-brand-cyan/40"
                  : "text-slate-400 hover:text-white hover:bg-surface"
              }`}
            >
              <Activity className="w-4 h-4" />
              <span>Dashboard</span>
            </button>

            <button
              onClick={() => onSelectTab("cases")}
              className={`flex items-center space-x-1.5 px-3 py-1.5 rounded text-sm font-medium transition-colors ${
                currentTab === "cases"
                  ? "bg-brand-cyan/20 text-brand-cyan border border-brand-cyan/40"
                  : "text-slate-400 hover:text-white hover:bg-surface"
              }`}
            >
              <Layers className="w-4 h-4" />
              <span>Recovery Cases</span>
            </button>

            <button
              onClick={() => onSelectTab("safeguards")}
              className={`flex items-center space-x-1.5 px-3 py-1.5 rounded text-sm font-medium transition-colors ${
                currentTab === "safeguards"
                  ? "bg-brand-cyan/20 text-brand-cyan border border-brand-cyan/40"
                  : "text-slate-400 hover:text-white hover:bg-surface"
              }`}
            >
              <ShieldCheck className="w-4 h-4" />
              <span>Safeguards & Audit</span>
            </button>

            <button
              onClick={() => onSelectTab("analytics")}
              className={`flex items-center space-x-1.5 px-3 py-1.5 rounded text-sm font-medium transition-colors ${
                currentTab === "analytics"
                  ? "bg-brand-cyan/20 text-brand-cyan border border-brand-cyan/40"
                  : "text-slate-400 hover:text-white hover:bg-surface"
              }`}
            >
              <BarChart3 className="w-4 h-4" />
              <span>Analytics</span>
            </button>
          </nav>
        </div>
      </div>
    </header>
  );
};
