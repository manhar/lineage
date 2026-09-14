import React, { useState } from 'react';
import { 
  X, 
  ArrowLeftRight, 
  ArrowUpRight, 
  ArrowDownRight, 
  Code2, 
  Database, 
  Layers, 
  Copy, 
  Check, 
  Sparkles,
  ChevronRight,
  GitMerge
} from 'lucide-react';

export default function InspectorPanel({ details, onClose, isLoading }) {
  const [activeTab, setActiveTab] = useState('upstream');
  const [copied, setCopied] = useState(false);

  if (!details && !isLoading) return null;

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
    <aside className="w-96 bg-slate-900/95 backdrop-blur-xl border-l border-slate-800 shadow-2xl flex flex-col h-full z-30 transition-all duration-300">
      {/* Header */}
      <div className="p-4 border-b border-slate-800 flex items-center justify-between bg-slate-950/60">
        <div className="flex items-center gap-2.5">
          <div className="p-2 rounded-lg bg-indigo-500/10 border border-indigo-500/30 text-indigo-400">
            <Layers className="w-5 h-5" />
          </div>
          <div>
            <h2 className="text-xs uppercase tracking-wider font-semibold text-slate-400">Column Inspector</h2>
            <p className="text-sm font-bold text-slate-100 truncate max-w-[200px]" title={details?.columnName}>
              {details?.columnName || 'Loading...'}
            </p>
          </div>
        </div>
        <button 
          onClick={onClose}
          className="p-1.5 text-slate-400 hover:text-slate-100 rounded-lg hover:bg-slate-800 transition-colors"
          title="Close Inspector"
        >
          <X className="w-5 h-5" />
        </button>
      </div>

      {isLoading ? (
        <div className="p-8 flex flex-col items-center justify-center flex-1 space-y-3 text-slate-400">
          <div className="w-6 h-6 border-2 border-indigo-500 border-t-transparent rounded-full animate-spin"></div>
          <p className="text-xs font-medium">Fetching column lineage & transformation details...</p>
        </div>
      ) : (
        <div className="flex-1 overflow-y-auto p-4 space-y-5">
          {/* Metadata Card */}
          <div className="bg-slate-950/50 rounded-xl p-3.5 border border-slate-800 space-y-2 text-xs">
            <div className="flex justify-between items-center pb-2 border-b border-slate-800/60">
              <span className="text-slate-400">Table Name</span>
              <span className="font-semibold text-slate-200">{details.tableName}</span>
            </div>
            <div className="flex justify-between items-center pb-2 border-b border-slate-800/60">
              <span className="text-slate-400">Database / Container</span>
              <span className="font-medium text-indigo-300">{details.databaseName}</span>
            </div>
            <div className="flex justify-between items-center">
              <span className="text-slate-400">Data Type</span>
              <span className="font-mono bg-slate-800/80 px-2 py-0.5 rounded text-cyan-300 text-[11px]">
                {details.dataType}
              </span>
            </div>
          </div>

          {/* Multi-Source Contributors Card (if derived from multiple columns) */}
          {contributors.length > 1 && (
            <div className="bg-amber-500/10 rounded-xl p-3.5 border border-amber-500/30 space-y-2.5">
              <div className="flex items-center gap-1.5 text-xs font-bold text-amber-300">
                <GitMerge className="w-4 h-4 text-amber-400" />
                <span>Multi-Source Derived Column ({contributors.length} Sources)</span>
              </div>
              <p className="text-[11px] text-slate-300">
                This metric is calculated by combining {contributors.length} source columns:
              </p>
              <div className="space-y-1.5">
                {contributors.map((c, idx) => (
                  <div key={idx} className="flex items-center justify-between bg-slate-950/80 px-2.5 py-1.5 rounded-lg border border-slate-850 text-xs">
                    <div className="flex items-center gap-2 overflow-hidden">
                      <span className="w-4 h-4 rounded-full bg-amber-500/20 text-amber-400 flex items-center justify-center text-[10px] font-bold shrink-0">
                        {idx + 1}
                      </span>
                      <span className="font-semibold text-slate-100 truncate" title={c.columnName}>
                        {c.columnName}
                      </span>
                      <span className="text-[10px] text-slate-400 bg-slate-800/80 px-1.5 py-0.5 rounded truncate">
                        {c.tableName}
                      </span>
                    </div>
                    <span className="text-[10px] font-mono text-cyan-300">
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
              <div className="flex items-center gap-1.5 text-xs font-semibold text-slate-300">
                <Code2 className="w-4 h-4 text-indigo-400" />
                <span>Transformation Formula ({details.transformationType || 'Direct'})</span>
              </div>
              {details.expression && (
                <button
                  onClick={() => handleCopy(details.expression)}
                  className="flex items-center gap-1 text-[11px] text-slate-400 hover:text-indigo-300 transition-colors"
                >
                  {copied ? <Check className="w-3.5 h-3.5 text-emerald-400" /> : <Copy className="w-3.5 h-3.5" />}
                  <span>{copied ? 'Copied' : 'Copy'}</span>
                </button>
              )}
            </div>

            <div className="bg-slate-950 rounded-xl p-3.5 border border-slate-800/80 relative font-mono text-xs text-indigo-200 overflow-x-auto leading-relaxed">
              <code>{details.expression || '-- Direct mapping without calculation'}</code>
            </div>
          </div>

          {/* Upstream / Downstream Tabs */}
          <div className="space-y-3">
            <div className="grid grid-cols-2 p-1 bg-slate-950 rounded-lg border border-slate-800 text-xs font-semibold">
              <button
                onClick={() => setActiveTab('upstream')}
                className={`py-1.5 rounded-md flex items-center justify-center gap-1.5 transition-all ${
                  activeTab === 'upstream'
                    ? 'bg-indigo-600 text-white shadow-sm'
                    : 'text-slate-400 hover:text-slate-200'
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
                    : 'text-slate-400 hover:text-slate-200'
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
                  <p className="text-xs text-slate-500 italic text-center py-4">No upstream sources found (Root Source System)</p>
                ) : (
                  upstreamPaths.map((path, pIdx) => (
                    <div key={pIdx} className="bg-slate-950/40 rounded-xl p-3 border border-slate-800 space-y-2">
                      <div className="text-[11px] font-semibold text-slate-400 border-b border-slate-800/60 pb-1 flex items-center justify-between">
                        <span>Trace Path #{pIdx + 1}</span>
                        <span className="text-indigo-400">{path.length} Steps</span>
                      </div>
                      <div className="space-y-2 pt-1">
                        {path.map((step, sIdx) => (
                          <div key={sIdx} className="flex items-center gap-2 text-xs">
                            <div className="w-5 h-5 rounded-full bg-slate-800 flex items-center justify-center text-[10px] font-bold text-slate-300 shrink-0">
                              {sIdx + 1}
                            </div>
                            <div className="overflow-hidden flex-1">
                              <p className="font-semibold text-slate-200 truncate">{step.nodeName}.{step.columnName}</p>
                              <p className="text-[10px] text-slate-400 font-mono">{step.dataType} • {step.transformationType || 'Direct'}</p>
                            </div>
                            {sIdx < path.length - 1 && (
                              <ChevronRight className="w-4 h-4 text-slate-600 shrink-0" />
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
                  <p className="text-xs text-slate-500 italic text-center py-4">No downstream consumers found (Terminal Visual/Report)</p>
                ) : (
                  downstreamPaths.map((path, pIdx) => (
                    <div key={pIdx} className="bg-slate-950/40 rounded-xl p-3 border border-slate-800 space-y-2">
                      <div className="text-[11px] font-semibold text-slate-400 border-b border-slate-800/60 pb-1 flex items-center justify-between">
                        <span>Trace Path #{pIdx + 1}</span>
                        <span className="text-indigo-400">{path.length} Steps</span>
                      </div>
                      <div className="space-y-2 pt-1">
                        {path.map((step, sIdx) => (
                          <div key={sIdx} className="flex items-center gap-2 text-xs">
                            <div className="w-5 h-5 rounded-full bg-slate-800 flex items-center justify-center text-[10px] font-bold text-slate-300 shrink-0">
                              {sIdx + 1}
                            </div>
                            <div className="overflow-hidden flex-1">
                              <p className="font-semibold text-slate-200 truncate">{step.nodeName}.{step.columnName}</p>
                              <p className="text-[10px] text-slate-400 font-mono">{step.dataType} • {step.transformationType || 'Direct'}</p>
                            </div>
                            {sIdx < path.length - 1 && (
                              <ChevronRight className="w-4 h-4 text-slate-600 shrink-0" />
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
