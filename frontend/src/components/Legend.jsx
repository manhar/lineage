import React, { useState } from 'react';
import { Database, Table, FileText, Sparkles, Layers, ChevronDown, ChevronUp } from 'lucide-react';

export default function Legend() {
  const [isCollapsed, setIsCollapsed] = useState(false);

  if (isCollapsed) {
    return (
      <button
        onClick={() => setIsCollapsed(false)}
        className="absolute top-6 left-6 z-10 bg-slate-900/85 hover:bg-slate-800/90 backdrop-blur-md border border-slate-800/80 hover:border-slate-700 rounded-lg px-3 py-2 shadow-xl flex items-center gap-2 text-xs text-slate-300 font-medium transition-all group"
        title="Expand Architecture Layers"
      >
        <Layers className="w-3.5 h-3.5 text-indigo-400" />
        <span>Architecture Layers</span>
        <ChevronDown className="w-3.5 h-3.5 text-slate-400 group-hover:text-slate-200 transition-transform" />
      </button>
    );
  }

  return (
    <div className="absolute top-6 left-6 z-10 bg-slate-900/90 backdrop-blur-md border border-slate-800/80 rounded-xl p-3.5 shadow-2xl space-y-2.5 text-xs transition-all">
      {/* Header with minimize button */}
      <div className="flex items-center justify-between gap-6 border-b border-slate-800/60 pb-1.5">
        <div className="flex items-center gap-1.5 font-semibold text-slate-300 text-[11px] uppercase tracking-wider">
          <Layers className="w-3.5 h-3.5 text-indigo-400" />
          <span>Architecture Layers</span>
        </div>
        <button
          onClick={() => setIsCollapsed(true)}
          className="p-1 hover:bg-slate-800 rounded-md text-slate-400 hover:text-slate-200 transition-colors"
          title="Minimize Architecture Layers"
        >
          <ChevronUp className="w-3.5 h-3.5" />
        </button>
      </div>

      {/* Layer badges */}
      <div className="flex items-center gap-4 text-slate-300 pt-0.5">
        <div className="flex items-center gap-1.5">
          <span className="w-2.5 h-2.5 rounded-full bg-amber-400 shadow-sm shadow-amber-400/50"></span>
          <Database className="w-3.5 h-3.5 text-amber-400" />
          <span>Source Systems</span>
        </div>
        <div className="flex items-center gap-1.5">
          <span className="w-2.5 h-2.5 rounded-full bg-indigo-400 shadow-sm shadow-indigo-400/50"></span>
          <Table className="w-3.5 h-3.5 text-indigo-400" />
          <span>Dataset Models</span>
        </div>
        <div className="flex items-center gap-1.5">
          <span className="w-2.5 h-2.5 rounded-full bg-emerald-400 shadow-sm shadow-emerald-400/50"></span>
          <FileText className="w-3.5 h-3.5 text-emerald-400" />
          <span>Report Visuals</span>
        </div>
      </div>

      {/* Quick hint */}
      <div className="pt-1.5 border-t border-slate-800/60 flex items-center gap-2 text-[11px] text-slate-400">
        <Sparkles className="w-3 h-3 text-amber-400 shrink-0" />
        <span>Click any column to trace end-to-end lineage paths & formulas</span>
      </div>
    </div>
  );
}
