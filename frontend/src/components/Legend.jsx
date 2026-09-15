import React, { useState } from 'react';
import { Database, Table, FileText, Sparkles, Layers, ChevronDown, ChevronUp, GitMerge } from 'lucide-react';

export default function Legend({ theme = 'dark' }) {
  const [isCollapsed, setIsCollapsed] = useState(false);
  const isDark = theme === 'dark';

  if (isCollapsed) {
    return (
      <button
        onClick={() => setIsCollapsed(false)}
        className={`absolute top-6 left-6 z-10 backdrop-blur-md border rounded-lg px-3 py-2 shadow-xl flex items-center gap-2 text-xs font-medium transition-all group ${
          isDark 
            ? 'bg-slate-900/85 hover:bg-slate-800/90 border-slate-800/80 hover:border-slate-700 text-slate-300' 
            : 'bg-white/90 hover:bg-white border-slate-200 hover:border-slate-300 text-slate-700 shadow-md'
        }`}
        title="Expand Architecture Layers"
      >
        <Layers className="w-3.5 h-3.5 text-indigo-500" />
        <span>Architecture Layers</span>
        <ChevronDown className="w-3.5 h-3.5 text-slate-400 group-hover:text-slate-600 transition-transform" />
      </button>
    );
  }

  return (
    <div className={`absolute top-6 left-6 z-10 backdrop-blur-md border rounded-xl p-3.5 shadow-2xl space-y-2.5 text-xs transition-all ${
      isDark 
        ? 'bg-slate-900/90 border-slate-800/80 text-slate-200' 
        : 'bg-white/95 border-slate-200 text-slate-800 shadow-lg'
    }`}>
      {/* Header with minimize button */}
      <div className={`flex items-center justify-between gap-6 border-b pb-1.5 ${
        isDark ? 'border-slate-800/60' : 'border-slate-200'
      }`}>
        <div className={`flex items-center gap-1.5 font-semibold text-[11px] uppercase tracking-wider ${
          isDark ? 'text-slate-300' : 'text-slate-600'
        }`}>
          <Layers className="w-3.5 h-3.5 text-indigo-500" />
          <span>Architecture Layers</span>
        </div>
        <button
          onClick={() => setIsCollapsed(true)}
          className={`p-1 rounded-md transition-colors ${
            isDark ? 'hover:bg-slate-800 text-slate-400 hover:text-slate-200' : 'hover:bg-slate-100 text-slate-500 hover:text-slate-800'
          }`}
          title="Minimize Architecture Layers"
        >
          <ChevronUp className="w-3.5 h-3.5" />
        </button>
      </div>

      {/* Layer badges */}
      <div className={`flex items-center gap-4 pt-0.5 ${isDark ? 'text-slate-300' : 'text-slate-700'}`}>
        <div className="flex items-center gap-1.5">
          <span className="w-2.5 h-2.5 rounded-full bg-amber-400 shadow-sm shadow-amber-400/50"></span>
          <Database className="w-3.5 h-3.5 text-amber-500" />
          <span>Teradata Staging</span>
        </div>
        <div className="flex items-center gap-1.5">
          <span className="w-2.5 h-2.5 rounded-full bg-indigo-400 shadow-sm shadow-indigo-400/50"></span>
          <Table className="w-3.5 h-3.5 text-indigo-500" />
          <span>Core & Fabric Models</span>
        </div>
        <div className="flex items-center gap-1.5">
          <span className="w-2.5 h-2.5 rounded-full bg-emerald-400 shadow-sm shadow-emerald-400/50"></span>
          <FileText className="w-3.5 h-3.5 text-emerald-500" />
          <span>Executive Reports</span>
        </div>
      </div>

      {/* Feature hints */}
      <div className={`pt-1.5 border-t flex items-center justify-between text-[11px] gap-3 ${
        isDark ? 'border-slate-800/60 text-slate-400' : 'border-slate-200 text-slate-500'
      }`}>
        <div className="flex items-center gap-1.5">
          <span className="text-[9px] font-bold text-amber-500 bg-amber-500/20 border border-amber-500/30 px-1 py-0.2 rounded flex items-center gap-0.5">
            <GitMerge className="w-2.5 h-2.5" /> 3
          </span>
          <span>Multi-Source Derived Column</span>
        </div>
        <div className="flex items-center gap-1">
          <Sparkles className="w-3 h-3 text-amber-500 shrink-0" />
          <span>Click column to trace</span>
        </div>
      </div>
    </div>
  );
}
