import React from 'react';
import { Database, Table, FileText, Sparkles } from 'lucide-react';

export default function Legend() {
  return (
    <div className="absolute bottom-6 left-6 z-10 bg-slate-900/80 backdrop-blur-md border border-slate-800/80 rounded-xl p-3 shadow-xl space-y-2 text-xs">
      <div className="font-semibold text-slate-400 text-[11px] uppercase tracking-wider mb-1">
        Architecture Layers
      </div>
      <div className="flex items-center gap-4 text-slate-300">
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
      <div className="pt-1.5 border-t border-slate-800/60 flex items-center gap-2 text-[11px] text-slate-400">
        <Sparkles className="w-3 h-3 text-amber-400" />
        <span>Click any column to trace end-to-end lineage paths & formulas</span>
      </div>
    </div>
  );
}
