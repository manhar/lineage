import React from 'react';
import { Network, Database, RefreshCw, Sparkles, Activity, Sun, Moon, ShieldAlert } from 'lucide-react';
import SearchBar from './SearchBar';

export default function Header({ 
  nodes = [], 
  summary, 
  activeTraceCount, 
  onSelectNode, 
  onSelectColumn, 
  onResetView, 
  onRefresh,
  theme = 'dark',
  onToggleTheme,
  onOpenImpactAnalysis
}) {
  const isDark = theme === 'dark';

  return (
    <header className={`h-16 backdrop-blur-xl border-b px-6 flex items-center justify-between z-20 gap-4 transition-colors ${
      isDark ? 'bg-slate-900/80 border-slate-800 text-white' : 'bg-white/90 border-slate-200 text-slate-800'
    }`}>
      {/* Brand Title */}
      <div className="flex items-center gap-3 shrink-0">
        <div className="w-9 h-9 rounded-xl bg-gradient-to-tr from-indigo-600 to-purple-500 flex items-center justify-center shadow-lg shadow-indigo-500/20">
          <Network className="w-5 h-5 text-white" />
        </div>
        <div>
          <h1 className="text-base font-extrabold tracking-tight flex items-center gap-2">
            Power BI Lineage Explorer
            <span className={`text-[10px] font-semibold px-2 py-0.5 rounded-full uppercase tracking-wider border ${
              isDark 
                ? 'bg-indigo-500/20 text-indigo-300 border-indigo-500/30' 
                : 'bg-indigo-50 text-indigo-700 border-indigo-200'
            }`}>
              Column-Level
            </span>
          </h1>
          <p className={`text-xs ${isDark ? 'text-slate-400' : 'text-slate-500'}`}>
            Interactive end-to-end data flow & transformation viewer
          </p>
        </div>
      </div>

      {/* Center Search Bar */}
      <div className="flex-1 max-w-md flex justify-center">
        <SearchBar 
          nodes={nodes} 
          onSelectNode={onSelectNode} 
          onSelectColumn={onSelectColumn} 
          theme={theme}
        />
      </div>

      {/* Right Stats & Actions */}
      <div className="flex items-center gap-3 shrink-0">
        <div className={`hidden lg:flex items-center gap-3 border px-3.5 py-1.5 rounded-full text-xs ${
          isDark ? 'bg-slate-950/60 border-slate-800/80' : 'bg-slate-50 border-slate-200'
        }`}>
          <div className="flex items-center gap-1.5">
            <Database className="w-3.5 h-3.5 text-amber-400" />
            <span className={isDark ? 'text-slate-400' : 'text-slate-500'}>Entities:</span>
            <span className={`font-bold ${isDark ? 'text-slate-200' : 'text-slate-700'}`}>{summary?.totalNodes || 0}</span>
          </div>
          <div className={`w-px h-3 ${isDark ? 'bg-slate-800' : 'bg-slate-200'}`} />
          <div className="flex items-center gap-1.5">
            <Activity className="w-3.5 h-3.5 text-indigo-400" />
            <span className={isDark ? 'text-slate-400' : 'text-slate-500'}>Edges:</span>
            <span className={`font-bold ${isDark ? 'text-slate-200' : 'text-slate-700'}`}>{summary?.totalColumnEdges || 0}</span>
          </div>
          <div className={`w-px h-3 ${isDark ? 'bg-slate-800' : 'bg-slate-200'}`} />
          <div className="flex items-center gap-1.5">
            <Sparkles className="w-3.5 h-3.5 text-emerald-400" />
            <span className={isDark ? 'text-slate-400' : 'text-slate-500'}>Active Trace:</span>
            <span className="font-bold text-indigo-400">{activeTraceCount > 0 ? `${activeTraceCount} Nodes` : 'None'}</span>
          </div>
        </div>

        <div className="flex items-center gap-2">
          {/* Impact Analysis Button */}
          <button
            onClick={onOpenImpactAnalysis}
            className={`px-3 py-1.5 text-xs font-semibold rounded-lg border flex items-center gap-1.5 transition-all shadow-sm ${
              isDark 
                ? 'bg-indigo-950/40 hover:bg-indigo-900/60 text-indigo-300 border-indigo-700/50' 
                : 'bg-indigo-50 hover:bg-indigo-100 text-indigo-700 border-indigo-200'
            }`}
            title="Simulate Column Change Impact Analysis"
          >
            <ShieldAlert className="w-3.5 h-3.5 text-indigo-500" />
            <span>Impact Analysis</span>
          </button>

          {/* Reset Focus Button */}
          <button
            onClick={onResetView}
            className={`px-3 py-1.5 text-xs font-semibold rounded-lg border transition-colors flex items-center gap-1.5 shadow-sm ${
              isDark 
                ? 'bg-slate-800 hover:bg-slate-700 text-slate-200 border-slate-700' 
                : 'bg-slate-100 hover:bg-slate-200 text-slate-700 border-slate-300'
            }`}
          >
            Reset Focus
          </button>

          {/* Dark / Light Mode Toggle */}
          <button
            onClick={onToggleTheme}
            className={`p-2 rounded-lg border transition-all ${
              isDark 
                ? 'bg-slate-800 hover:bg-slate-700 text-amber-300 border-slate-700' 
                : 'bg-slate-100 hover:bg-slate-200 text-slate-600 border-slate-300'
            }`}
            title={isDark ? 'Switch to Light Mode (Normal Screen)' : 'Switch to Dark Mode'}
          >
            {isDark ? <Sun className="w-4 h-4" /> : <Moon className="w-4 h-4" />}
          </button>

          {/* Refresh Lineage Data */}
          <button
            onClick={onRefresh}
            className="p-2 text-white bg-indigo-600 hover:bg-indigo-500 rounded-lg transition-colors shadow-lg shadow-indigo-600/20"
            title="Refresh Lineage Data"
          >
            <RefreshCw className="w-4 h-4" />
          </button>
        </div>
      </div>
    </header>
  );
}
