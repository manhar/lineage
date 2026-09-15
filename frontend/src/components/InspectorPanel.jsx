import React, { useState } from 'react';
import { 
  X, 
  ArrowUpRight, 
  ArrowDownRight, 
  Code2, 
  Layers, 
  Copy, 
  Check, 
  ChevronRight,
  GitMerge,
  ShieldAlert
} from 'lucide-react';

export default function InspectorPanel({ details, onClose, isLoading, theme = 'dark', onOpenImpactAnalysis }) {
  const [activeTab, setActiveTab] = useState('upstream');
  const [copied, setCopied] = useState(false);

  if (!details && !isLoading) return null;

  const isDark = theme === 'dark';

  const handleCopy = (code) => {
    if (!code) return;
    navigator.clipboard.writeText(code);
    setCopied(true);
    setTimeout(() => setCopied(false), 2000);
  };

  const upstreamPaths = details?.upstreamPaths || [];
  const downstreamPaths = details?.downstreamPaths || [];
  const contributors = details?.directContributors || [];

  return (
    <aside className={`w-96 backdrop-blur-xl border-l shadow-2xl flex flex-col h-full z-30 transition-all duration-300 ${
      isDark ? 'bg-slate-900/95 border-slate-800 text-slate-100' : 'bg-white/95 border-slate-200 text-slate-800'
    }`}>
      {/* Header */}
      <div className={`p-4 border-b flex items-center justify-between ${
        isDark ? 'border-slate-800 bg-slate-950/60' : 'border-slate-200 bg-slate-50/80'
      }`}>
        <div className="flex items-center gap-2.5">
          <div className="p-2 rounded-lg bg-indigo-500/10 border border-indigo-500/30 text-indigo-500">
            <Layers className="w-5 h-5" />
          </div>
          <div>
            <h2 className={`text-xs uppercase tracking-wider font-semibold ${isDark ? 'text-slate-400' : 'text-slate-500'}`}>
              Column Inspector
            </h2>
            <p className={`text-sm font-bold truncate max-w-[200px] ${isDark ? 'text-slate-100' : 'text-slate-900'}`} title={details?.columnName}>
              {details?.columnName || 'Loading...'}
            </p>
          </div>
        </div>
        <button 
          onClick={onClose}
          className={`p-1.5 rounded-lg transition-colors ${
            isDark ? 'text-slate-400 hover:text-slate-100 hover:bg-slate-800' : 'text-slate-500 hover:text-slate-800 hover:bg-slate-100'
          }`}
          title="Close Inspector"
        >
          <X className="w-5 h-5" />
        </button>
      </div>

      {isLoading ? (
        <div className={`p-8 flex flex-col items-center justify-center flex-1 space-y-3 ${isDark ? 'text-slate-400' : 'text-slate-500'}`}>
          <div className="w-6 h-6 border-2 border-indigo-500 border-t-transparent rounded-full animate-spin"></div>
          <p className="text-xs font-medium">Fetching column lineage & transformation details...</p>
        </div>
      ) : (
        <div className="flex-1 overflow-y-auto p-4 space-y-5">
          {/* Metadata Card */}
          <div className={`rounded-xl p-3.5 border space-y-2 text-xs ${
            isDark ? 'bg-slate-950/50 border-slate-800' : 'bg-slate-50 border-slate-200'
          }`}>
            <div className={`flex justify-between items-center pb-2 border-b ${isDark ? 'border-slate-800/60' : 'border-slate-200'}`}>
              <span className={isDark ? 'text-slate-400' : 'text-slate-500'}>Table Name</span>
              <span className={`font-semibold ${isDark ? 'text-slate-200' : 'text-slate-800'}`}>{details.tableName}</span>
            </div>
            <div className={`flex justify-between items-center pb-2 border-b ${isDark ? 'border-slate-800/60' : 'border-slate-200'}`}>
              <span className={isDark ? 'text-slate-400' : 'text-slate-500'}>Database / Container</span>
              <span className="font-medium text-indigo-500">{details.databaseName}</span>
            </div>
            <div className="flex justify-between items-center">
              <span className={isDark ? 'text-slate-400' : 'text-slate-500'}>Data Type</span>
              <span className={`font-mono px-2 py-0.5 rounded text-[11px] ${
                isDark ? 'bg-slate-800/80 text-cyan-300' : 'bg-slate-200 text-slate-800 font-semibold'
              }`}>
                {details.dataType}
              </span>
            </div>
          </div>

          {/* Quick Impact Analysis Trigger Card */}
          {onOpenImpactAnalysis && details && (
            <div className={`p-3 rounded-xl border flex items-center justify-between gap-3 ${
              isDark ? 'bg-indigo-950/30 border-indigo-800/40' : 'bg-indigo-50 border-indigo-200'
            }`}>
              <div className="flex items-center gap-2.5">
                <ShieldAlert className="w-5 h-5 text-indigo-500 shrink-0" />
                <div>
                  <h3 className={`text-xs font-bold ${isDark ? 'text-indigo-200' : 'text-indigo-900'}`}>
                    Simulate Change Impact
                  </h3>
                  <p className={`text-[11px] ${isDark ? 'text-indigo-300/80' : 'text-indigo-700/80'}`}>
                    View affected downstream reports & models
                  </p>
                </div>
              </div>
              <button
                type="button"
                onClick={() => onOpenImpactAnalysis(details.selectedColumnId, details.selectedNodeId)}
                className="px-2.5 py-1.5 bg-indigo-600 hover:bg-indigo-500 text-white rounded-lg text-xs font-semibold shadow-sm transition-colors whitespace-nowrap"
              >
                Analyze
              </button>
            </div>
          )}

          {/* Multi-Source Contributors Card (if derived from multiple columns) */}
          {contributors.length > 1 && (
            <div className="bg-amber-500/10 rounded-xl p-3.5 border border-amber-500/30 space-y-2.5">
              <div className="flex items-center gap-1.5 text-xs font-bold text-amber-500">
                <GitMerge className="w-4 h-4 text-amber-500" />
                <span>Multi-Source Derived Column ({contributors.length} Sources)</span>
              </div>
              <p className={`text-[11px] ${isDark ? 'text-slate-300' : 'text-slate-600'}`}>
                This metric is calculated by combining {contributors.length} source columns:
              </p>
              <div className="space-y-1.5">
                {contributors.map((c, idx) => (
                  <div key={idx} className={`flex items-center justify-between px-2.5 py-1.5 rounded-lg border text-xs ${
                    isDark ? 'bg-slate-950/80 border-slate-800' : 'bg-white border-slate-200'
                  }`}>
                    <div className="flex items-center gap-2 overflow-hidden">
                      <span className="w-4 h-4 rounded-full bg-amber-500/20 text-amber-500 flex items-center justify-center text-[10px] font-bold shrink-0">
                        {idx + 1}
                      </span>
                      <span className={`font-semibold truncate ${isDark ? 'text-slate-100' : 'text-slate-800'}`} title={c.columnName}>
                        {c.columnName}
                      </span>
                      <span className={`text-[10px] px-1.5 py-0.5 rounded truncate ${
                        isDark ? 'text-slate-400 bg-slate-800/80' : 'text-slate-500 bg-slate-100'
                      }`}>
                        {c.tableName}
                      </span>
                    </div>
                    <span className={`text-[10px] font-mono ${isDark ? 'text-cyan-300' : 'text-indigo-600'}`}>
                      {c.dataType}
                    </span>
                  </div>
                ))}
              </div>
            </div>
          )}

          {/* Transformation Formula Block */}
          <div className="space-y-2">
            <div className="flex items-center justify-between">
              <div className={`flex items-center gap-1.5 text-xs font-semibold ${isDark ? 'text-slate-300' : 'text-slate-700'}`}>
                <Code2 className="w-4 h-4 text-indigo-500" />
                <span>Transformation Formula ({details.transformationType || 'Direct'})</span>
              </div>
              {details.expression && (
                <button
                  onClick={() => handleCopy(details.expression)}
                  className={`flex items-center gap-1 text-[11px] transition-colors ${
                    isDark ? 'text-slate-400 hover:text-indigo-300' : 'text-slate-500 hover:text-indigo-600'
                  }`}
                >
                  {copied ? <Check className="w-3.5 h-3.5 text-emerald-500" /> : <Copy className="w-3.5 h-3.5" />}
                  <span>{copied ? 'Copied' : 'Copy'}</span>
                </button>
              )}
            </div>

            <div className={`rounded-xl p-3.5 border relative font-mono text-xs overflow-x-auto leading-relaxed ${
              isDark ? 'bg-slate-950 border-slate-800/80 text-indigo-200' : 'bg-slate-50 border-slate-200 text-indigo-900'
            }`}>
              <code>{details.expression || '-- Direct mapping without calculation'}</code>
            </div>
          </div>

          {/* Upstream / Downstream Tabs */}
          <div className="space-y-3">
            <div className={`grid grid-cols-2 p-1 rounded-lg border text-xs font-semibold ${
              isDark ? 'bg-slate-950 border-slate-800' : 'bg-slate-100 border-slate-200'
            }`}>
              <button
                onClick={() => setActiveTab('upstream')}
                className={`py-1.5 rounded-md flex items-center justify-center gap-1.5 transition-all ${
                  activeTab === 'upstream'
                    ? 'bg-indigo-600 text-white shadow-sm'
                    : isDark ? 'text-slate-400 hover:text-slate-200' : 'text-slate-600 hover:text-slate-800'
                }`}
              >
                <ArrowUpRight className="w-4 h-4" />
                <span>Upstream ({upstreamPaths.length})</span>
              </button>
              <button
                onClick={() => setActiveTab('downstream')}
                className={`py-1.5 rounded-md flex items-center justify-center gap-1.5 transition-all ${
                  activeTab === 'downstream'
                    ? 'bg-indigo-600 text-white shadow-sm'
                    : isDark ? 'text-slate-400 hover:text-slate-200' : 'text-slate-600 hover:text-slate-800'
                }`}
              >
                <ArrowDownRight className="w-4 h-4" />
                <span>Downstream ({downstreamPaths.length})</span>
              </button>
            </div>

            {/* Path Stepper Trees */}
            <div className="space-y-3">
              {activeTab === 'upstream' && (
                upstreamPaths.length === 0 ? (
                  <p className="text-xs text-slate-400 italic text-center py-4">No upstream sources found (Root Source System)</p>
                ) : (
                  upstreamPaths.map((path, pIdx) => (
                    <div key={pIdx} className={`rounded-xl p-3 border space-y-2 ${
                      isDark ? 'bg-slate-950/40 border-slate-800' : 'bg-slate-50 border-slate-200'
                    }`}>
                      <div className={`text-[11px] font-semibold border-b pb-1 flex items-center justify-between ${
                        isDark ? 'text-slate-400 border-slate-800/60' : 'text-slate-500 border-slate-200'
                      }`}>
                        <span>Trace Path #{pIdx + 1}</span>
                        <span className="text-indigo-500 font-bold">{path.length} Steps</span>
                      </div>
                      <div className="space-y-2 pt-1">
                        {path.map((step, sIdx) => (
                          <div key={sIdx} className="flex items-center gap-2 text-xs">
                            <div className={`w-5 h-5 rounded-full flex items-center justify-center text-[10px] font-bold shrink-0 ${
                              isDark ? 'bg-slate-800 text-slate-300' : 'bg-slate-200 text-slate-700'
                            }`}>
                              {sIdx + 1}
                            </div>
                            <div className="overflow-hidden flex-1">
                              <p className={`font-semibold truncate ${isDark ? 'text-slate-200' : 'text-slate-800'}`}>
                                {step.nodeName}.{step.columnName}
                              </p>
                              <p className={`text-[10px] font-mono ${isDark ? 'text-slate-400' : 'text-slate-500'}`}>
                                {step.dataType} • {step.transformationType || 'Direct'}
                              </p>
                            </div>
                            {sIdx < path.length - 1 && (
                              <ChevronRight className="w-4 h-4 text-slate-400 shrink-0" />
                            )}
                          </div>
                        ))}
                      </div>
                    </div>
                  ))
                )
              )}

              {activeTab === 'downstream' && (
                downstreamPaths.length === 0 ? (
                  <p className="text-xs text-slate-400 italic text-center py-4">No downstream consumers found (Terminal Visual/Report)</p>
                ) : (
                  downstreamPaths.map((path, pIdx) => (
                    <div key={pIdx} className={`rounded-xl p-3 border space-y-2 ${
                      isDark ? 'bg-slate-950/40 border-slate-800' : 'bg-slate-50 border-slate-200'
                    }`}>
                      <div className={`text-[11px] font-semibold border-b pb-1 flex items-center justify-between ${
                        isDark ? 'text-slate-400 border-slate-800/60' : 'text-slate-500 border-slate-200'
                      }`}>
                        <span>Trace Path #{pIdx + 1}</span>
                        <span className="text-indigo-500 font-bold">{path.length} Steps</span>
                      </div>
                      <div className="space-y-2 pt-1">
                        {path.map((step, sIdx) => (
                          <div key={sIdx} className="flex items-center gap-2 text-xs">
                            <div className={`w-5 h-5 rounded-full flex items-center justify-center text-[10px] font-bold shrink-0 ${
                              isDark ? 'bg-slate-800 text-slate-300' : 'bg-slate-200 text-slate-700'
                            }`}>
                              {sIdx + 1}
                            </div>
                            <div className="overflow-hidden flex-1">
                              <p className={`font-semibold truncate ${isDark ? 'text-slate-200' : 'text-slate-800'}`}>
                                {step.nodeName}.{step.columnName}
                              </p>
                              <p className={`text-[10px] font-mono ${isDark ? 'text-slate-400' : 'text-slate-500'}`}>
                                {step.dataType} • {step.transformationType || 'Direct'}
                              </p>
                            </div>
                            {sIdx < path.length - 1 && (
                              <ChevronRight className="w-4 h-4 text-slate-400 shrink-0" />
                            )}
                          </div>
                        ))}
                      </div>
                    </div>
                  ))
                )
              )}
            </div>
          </div>
        </div>
      )}
    </aside>
  );
}
