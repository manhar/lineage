import React from 'react';
import { Network, Database, Table, FileText, RefreshCw, Sparkles, Activity } from 'lucide-react';

export default function Header({ summary, activeTraceCount, onResetView, onRefresh }) {
  return (
    <header className="h-16 bg-slate-900/80 backdrop-blur-xl border-b border-slate-800 px-6 flex items-center justify-between z-20">
      {/* Brand Title */}
      <div className="flex items-center gap-3">
        <div className="w-9 h-9 rounded-xl bg-gradient-to-tr from-indigo-600 to-purple-500 flex items-center justify-center shadow-lg shadow-indigo-500/20">
          <Network className="w-5 h-5 text-white" />
        </div>
        <div>
          <h1 className="text-base font-extrabold tracking-tight text-white flex items-center gap-2">
            Power BI Lineage Explorer
            <span className="text-[10px] font-semibold bg-indigo-500/20 text-indigo-300 border border-indigo-500/30 px-2 py-0.5 rounded-full uppercase tracking-wider">
              Column-Level
            </span>
          </h1>
          <p className="text-xs text-slate-400">Interactive end-to-end data flow & transformation viewer</p>
        </div>
      </div>

      {/* Center Stats Bar */}
      <div className="hidden md:flex items-center gap-4 bg-slate-950/60 border border-slate-800/80 px-4 py-1.5 rounded-full text-xs">
        <div className="flex items-center gap-1.5">
          <Database className="w-3.5 h-3.5 text-amber-400" />
          <span className="text-slate-400">Entities:</span>
          <span className="font-bold text-slate-200">{summary?.totalNodes || 0}</span>
        </div>
        <div className="w-px h-3 bg-slate-800" />
        <div className="flex items-center gap-1.5">
          <Activity className="w-3.5 h-3.5 text-indigo-400" />
          <span className="text-slate-400">Column Edges:</span>
          <span className="font-bold text-slate-200">{summary?.totalColumnEdges || 0}</span>
        </div>
        <div className="w-px h-3 bg-slate-800" />
        <div className="flex items-center gap-1.5">
          <Sparkles className="w-3.5 h-3.5 text-emerald-400" />
          <span className="text-slate-400">Active Highlighting:</span>
          <span className="font-bold text-indigo-300">{activeTraceCount > 0 ? `${activeTraceCount} Nodes` : 'None'}</span>
        </div>
      </div>

      {/* Action Buttons */}
      <div className="flex items-center gap-2">
        <button
          onClick={onResetView}
          className="px-3 py-1.5 text-xs font-semibold bg-slate-800 hover:bg-slate-700 text-slate-200 rounded-lg border border-slate-700 transition-colors flex items-center gap-1.5 shadow-sm"
        >
          Reset Focus
        </button>
        <button
          onClick={onRefresh}
          className="p-2 text-slate-300 hover:text-white bg-indigo-600 hover:bg-indigo-500 rounded-lg transition-colors shadow-lg shadow-indigo-600/20"
          title="Refresh Lineage Data"
        >
          <RefreshCw className="w-4 h-4" />
        </button>
      </div>
    </header>
  );
}
