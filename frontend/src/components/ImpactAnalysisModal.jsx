import React, { useState, useEffect, useMemo } from 'react';
import { 
  X, AlertTriangle, ShieldAlert, CheckCircle2, 
  Download, Copy, Check, FileText, Database, ArrowRight, 
  Layers, Search, Filter
} from 'lucide-react';

export default function ImpactAnalysisModal({
  isOpen,
  onClose,
  initialColumnId,
  initialNodeId,
  allNodes = [],
  theme = 'dark'
}) {
  const [selectedColumnId, setSelectedColumnId] = useState(initialColumnId || '');
  const [selectedAction, setSelectedAction] = useState('delete'); // 'delete' | 'update' | 'add'
  const [loading, setLoading] = useState(false);
  const [impactData, setImpactData] = useState(null);
  const [error, setError] = useState(null);
  const [searchTerm, setSearchTerm] = useState('');
  const [typeFilter, setTypeFilter] = useState('all');
  const [copied, setCopied] = useState(false);

  // Sync initial column when modal opens
  useEffect(() => {
    if (initialColumnId) {
      setSelectedColumnId(initialColumnId);
    } else if (allNodes.length > 0 && allNodes[0]?.columns?.length > 0) {
      setSelectedColumnId(allNodes[0].columns[0].id);
    }
  }, [initialColumnId, allNodes, isOpen]);

  // Fetch impact analysis data whenever selectedColumnId or selectedAction changes
  useEffect(() => {
    if (!isOpen || !selectedColumnId) return;

    let isMounted = true;
    const fetchImpact = async () => {
      setLoading(true);
      setError(null);
      try {
        const res = await fetch(`/api/impact-analysis?columnId=${encodeURIComponent(selectedColumnId)}&action=${selectedAction}`);
        if (!res.ok) {
          const errBody = await res.json().catch(() => ({}));
          throw new Error(errBody.detail || `HTTP Error ${res.status}`);
        }
        const data = await res.json();
        if (isMounted) setImpactData(data);
      } catch (err) {
        if (isMounted) setError(err.message);
      } finally {
        if (isMounted) setLoading(false);
      }
    };

    fetchImpact();
    return () => { isMounted = false; };
  }, [isOpen, selectedColumnId, selectedAction]);

  // Flattened column list for dropdown selection
  const flatColumns = useMemo(() => {
    const list = [];
    allNodes.forEach(node => {
      node.columns.forEach(col => {
        list.push({
          nodeId: node.id,
          nodeName: node.name,
          container: node.database,
          columnId: col.id,
          columnName: col.name,
          dataType: col.dataType
        });
      });
    });
    return list;
  }, [allNodes]);

  // Filtered impacted objects
  const filteredImpactedObjects = useMemo(() => {
    if (!impactData?.impactedObjects) return [];
    return impactData.impactedObjects.filter(obj => {
      const matchesSearch = 
        obj.nodeName.toLowerCase().includes(searchTerm.toLowerCase()) ||
        obj.columnName.toLowerCase().includes(searchTerm.toLowerCase()) ||
        obj.container.toLowerCase().includes(searchTerm.toLowerCase()) ||
        (obj.affectedExpression && obj.affectedExpression.toLowerCase().includes(searchTerm.toLowerCase()));
      
      const matchesType = typeFilter === 'all' ? true :
        typeFilter === 'report' ? obj.nodeType === 'report' :
        typeFilter === 'model' ? obj.nodeType === 'dataset_table' :
        obj.nodeType.includes('source');

      return matchesSearch && matchesType;
    });
  }, [impactData, searchTerm, typeFilter]);

  // CSV download trigger
  const handleDownloadCsv = () => {
    if (!selectedColumnId) return;
    window.open(`/api/impact-analysis/csv?columnId=${encodeURIComponent(selectedColumnId)}&action=${selectedAction}`, '_blank');
  };

  // Copy Markdown summary
  const handleCopyMarkdown = () => {
    if (!impactData) return;
    const md = `### Lineage Impact Analysis Report
- **Target Column**: \`${impactData.target.columnName}\` (${impactData.target.nodeName})
- **Simulated Change**: \`${impactData.action.toUpperCase()}\`
- **Risk Level**: **${impactData.summary.riskLevel}** (${impactData.summary.riskReason})
- **Impacted Reports**: ${impactData.summary.impactedReportsCount}
- **Impacted Models**: ${impactData.summary.impactedModelsCount}
- **Total Objects Affected**: ${impactData.summary.totalImpactedObjects}

#### Impacted Downstream Objects:
| Object | Layer | Column/Measure | Severity | Impact |
|---|---|---|---|---|
${impactData.impactedObjects.map(o => `| ${o.nodeName} | ${o.nodeType} | ${o.columnName} | ${o.severity} | ${o.impactDescription} |`).join('\n')}`;

    navigator.clipboard.writeText(md);
    setCopied(true);
    setTimeout(() => setCopied(false), 2000);
  };

  if (!isOpen) return null;

  const isDark = theme === 'dark';

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center p-4 bg-black/70 backdrop-blur-sm animate-in fade-in duration-200">
      <div className={`w-full max-w-4xl max-h-[90vh] flex flex-col rounded-2xl border shadow-2xl overflow-hidden transition-colors ${
        isDark 
          ? 'bg-slate-900 border-slate-800 text-slate-100' 
          : 'bg-white border-slate-200 text-slate-800'
      }`}>
        
        {/* Modal Header */}
        <div className={`px-6 py-4 border-b flex items-center justify-between ${
          isDark ? 'border-slate-800 bg-slate-900/80' : 'border-slate-200 bg-slate-50/80'
        }`}>
          <div className="flex items-center gap-3">
            <div className="w-10 h-10 rounded-xl bg-indigo-500/10 border border-indigo-500/20 text-indigo-500 flex items-center justify-center">
              <ShieldAlert className="w-5 h-5" />
            </div>
            <div>
              <h2 className="text-base font-bold flex items-center gap-2">
                Column Change Impact Analysis
                <span className={`text-[10px] font-semibold px-2 py-0.5 rounded-full border uppercase tracking-wider ${
                  isDark ? 'bg-indigo-500/20 text-indigo-300 border-indigo-500/30' : 'bg-indigo-50 text-indigo-700 border-indigo-200'
                }`}>
                  Blast-Radius Engine
                </span>
              </h2>
              <p className={`text-xs ${isDark ? 'text-slate-400' : 'text-slate-500'}`}>
                Simulate change impact on downstream models, measures, and Power BI reports
              </p>
            </div>
          </div>

          <button
            onClick={onClose}
            className={`p-2 rounded-lg transition-colors ${
              isDark ? 'text-slate-400 hover:text-white hover:bg-slate-800' : 'text-slate-500 hover:text-slate-800 hover:bg-slate-100'
            }`}
          >
            <X className="w-5 h-5" />
          </button>
        </div>

        {/* Modal Body */}
        <div className="flex-1 overflow-y-auto p-6 space-y-6">
          
          {/* Target Selection & Action Toggle Bar */}
          <div className={`p-4 rounded-xl border grid grid-cols-1 md:grid-cols-2 gap-4 ${
            isDark ? 'bg-slate-950/60 border-slate-800' : 'bg-slate-50 border-slate-200'
          }`}>
            <div>
              <label className={`block text-xs font-semibold mb-1.5 ${isDark ? 'text-slate-300' : 'text-slate-700'}`}>
                Target Column to Simulate
              </label>
              <select
                value={selectedColumnId}
                onChange={(e) => setSelectedColumnId(e.target.value)}
                className={`w-full px-3 py-2 text-xs rounded-lg border font-mono outline-none transition-all ${
                  isDark 
                    ? 'bg-slate-900 border-slate-700 text-slate-200 focus:border-indigo-500' 
                    : 'bg-white border-slate-300 text-slate-800 focus:border-indigo-500'
                }`}
              >
                {flatColumns.map(col => (
                  <option key={col.columnId} value={col.columnId}>
                    {col.nodeName} → {col.columnName} ({col.dataType})
                  </option>
                ))}
              </select>
            </div>

            <div>
              <label className={`block text-xs font-semibold mb-1.5 ${isDark ? 'text-slate-300' : 'text-slate-700'}`}>
                Simulated Action
              </label>
              <div className="grid grid-cols-3 gap-2">
                <button
                  type="button"
                  onClick={() => setSelectedAction('delete')}
                  className={`py-2 px-3 rounded-lg text-xs font-semibold border transition-all flex items-center justify-center gap-1.5 ${
                    selectedAction === 'delete'
                      ? 'bg-rose-500/20 border-rose-500/60 text-rose-400 shadow-sm'
                      : isDark ? 'border-slate-800 text-slate-400 hover:bg-slate-900' : 'border-slate-200 text-slate-600 hover:bg-white'
                  }`}
                >
                  <AlertTriangle className="w-3.5 h-3.5 text-rose-500" />
                  Delete / Drop
                </button>

                <button
                  type="button"
                  onClick={() => setSelectedAction('update')}
                  className={`py-2 px-3 rounded-lg text-xs font-semibold border transition-all flex items-center justify-center gap-1.5 ${
                    selectedAction === 'update'
                      ? 'bg-amber-500/20 border-amber-500/60 text-amber-400 shadow-sm'
                      : isDark ? 'border-slate-800 text-slate-400 hover:bg-slate-900' : 'border-slate-200 text-slate-600 hover:bg-white'
                  }`}
                >
                  <Layers className="w-3.5 h-3.5 text-amber-500" />
                  Update Type
                </button>

                <button
                  type="button"
                  onClick={() => setSelectedAction('add')}
                  className={`py-2 px-3 rounded-lg text-xs font-semibold border transition-all flex items-center justify-center gap-1.5 ${
                    selectedAction === 'add'
                      ? 'bg-emerald-500/20 border-emerald-500/60 text-emerald-400 shadow-sm'
                      : isDark ? 'border-slate-800 text-slate-400 hover:bg-slate-900' : 'border-slate-200 text-slate-600 hover:bg-white'
                  }`}
                >
                  <CheckCircle2 className="w-3.5 h-3.5 text-emerald-500" />
                  Add Derived
                </button>
              </div>
            </div>
          </div>

          {/* Loading & Error States */}
          {loading ? (
            <div className="py-12 flex flex-col items-center justify-center space-y-3">
              <div className="w-8 h-8 border-3 border-indigo-500 border-t-transparent rounded-full animate-spin"></div>
              <p className={`text-xs font-medium ${isDark ? 'text-slate-400' : 'text-slate-500'}`}>
                Calculating downstream graph blast radius...
              </p>
            </div>
          ) : error ? (
            <div className="p-4 rounded-xl bg-red-500/10 border border-red-500/20 text-red-400 text-xs">
              Error analyzing impact: {error}
            </div>
          ) : impactData ? (
            <>
              {/* Risk Assessment Banner */}
              <div className={`p-4 rounded-xl border flex items-start gap-3.5 ${
                impactData.summary.riskLevel === 'CRITICAL'
                  ? 'bg-rose-500/10 border-rose-500/30 text-rose-400'
                  : impactData.summary.riskLevel === 'HIGH'
                  ? 'bg-amber-500/10 border-amber-500/30 text-amber-400'
                  : 'bg-emerald-500/10 border-emerald-500/30 text-emerald-400'
              }`}>
                <div className="p-2 rounded-lg bg-current/10 shrink-0">
                  {impactData.summary.riskLevel === 'CRITICAL' ? (
                    <ShieldAlert className="w-5 h-5 text-rose-500" />
                  ) : impactData.summary.riskLevel === 'HIGH' ? (
                    <AlertTriangle className="w-5 h-5 text-amber-500" />
                  ) : (
                    <CheckCircle2 className="w-5 h-5 text-emerald-500" />
                  )}
                </div>
                <div className="flex-1">
                  <div className="flex items-center gap-2">
                    <span className="text-xs font-black tracking-wider uppercase px-2 py-0.5 rounded bg-current/15">
                      {impactData.summary.riskLevel} RISK
                    </span>
                    <span className="text-xs font-bold text-slate-200">
                      Action: {impactData.action.toUpperCase()}
                    </span>
                  </div>
                  <p className={`text-xs mt-1.5 leading-relaxed font-medium ${isDark ? 'text-slate-300' : 'text-slate-700'}`}>
                    {impactData.summary.riskReason}
                  </p>
                </div>
              </div>

              {/* KPI Summary Cards */}
              <div className="grid grid-cols-2 sm:grid-cols-4 gap-3">
                <div className={`p-3.5 rounded-xl border ${
                  isDark ? 'bg-slate-950/60 border-slate-800' : 'bg-slate-50 border-slate-200'
                }`}>
                  <span className={`text-[11px] block font-medium ${isDark ? 'text-slate-400' : 'text-slate-500'}`}>
                    Total Impacted Objects
                  </span>
                  <span className="text-xl font-extrabold text-indigo-400 mt-1 block">
                    {impactData.summary.totalImpactedObjects}
                  </span>
                </div>

                <div className={`p-3.5 rounded-xl border ${
                  isDark ? 'bg-slate-950/60 border-slate-800' : 'bg-slate-50 border-slate-200'
                }`}>
                  <span className={`text-[11px] block font-medium ${isDark ? 'text-slate-400' : 'text-slate-500'}`}>
                    Critical Reports
                  </span>
                  <span className={`text-xl font-extrabold mt-1 block ${
                    impactData.summary.impactedReportsCount > 0 ? 'text-rose-400' : 'text-slate-400'
                  }`}>
                    {impactData.summary.impactedReportsCount}
                  </span>
                </div>

                <div className={`p-3.5 rounded-xl border ${
                  isDark ? 'bg-slate-950/60 border-slate-800' : 'bg-slate-50 border-slate-200'
                }`}>
                  <span className={`text-[11px] block font-medium ${isDark ? 'text-slate-400' : 'text-slate-500'}`}>
                    Dataset Models
                  </span>
                  <span className="text-xl font-extrabold text-amber-400 mt-1 block">
                    {impactData.summary.impactedModelsCount}
                  </span>
                </div>

                <div className={`p-3.5 rounded-xl border ${
                  isDark ? 'bg-slate-950/60 border-slate-800' : 'bg-slate-50 border-slate-200'
                }`}>
                  <span className={`text-[11px] block font-medium ${isDark ? 'text-slate-400' : 'text-slate-500'}`}>
                    Formulas & Measures
                  </span>
                  <span className="text-xl font-extrabold text-purple-400 mt-1 block">
                    {impactData.summary.impactedMeasuresCount}
                  </span>
                </div>
              </div>

              {/* Search & Filter Header for Impacted Objects */}
              <div className="space-y-3">
                <div className="flex flex-col sm:flex-row items-center justify-between gap-3">
                  <h3 className="text-xs font-bold uppercase tracking-wider text-slate-400 flex items-center gap-2">
                    <Database className="w-3.5 h-3.5 text-indigo-400" />
                    Impacted Lineage Inventory ({filteredImpactedObjects.length})
                  </h3>

                  <div className="flex items-center gap-2 w-full sm:w-auto">
                    {/* Filter Type */}
                    <div className="flex items-center gap-1 bg-slate-900/60 border border-slate-800 rounded-lg p-1 text-[11px]">
                      <button
                        type="button"
                        onClick={() => setTypeFilter('all')}
                        className={`px-2 py-0.5 rounded transition-all ${typeFilter === 'all' ? 'bg-indigo-600 text-white' : 'text-slate-400 hover:text-slate-200'}`}
                      >
                        All
                      </button>
                      <button
                        type="button"
                        onClick={() => setTypeFilter('report')}
                        className={`px-2 py-0.5 rounded transition-all ${typeFilter === 'report' ? 'bg-indigo-600 text-white' : 'text-slate-400 hover:text-slate-200'}`}
                      >
                        Reports
                      </button>
                      <button
                        type="button"
                        onClick={() => setTypeFilter('model')}
                        className={`px-2 py-0.5 rounded transition-all ${typeFilter === 'model' ? 'bg-indigo-600 text-white' : 'text-slate-400 hover:text-slate-200'}`}
                      >
                        Models
                      </button>
                    </div>

                    {/* Search Field */}
                    <div className="relative flex-1 sm:w-48">
                      <Search className="w-3.5 h-3.5 absolute left-2.5 top-2 text-slate-400" />
                      <input
                        type="text"
                        placeholder="Filter objects..."
                        value={searchTerm}
                        onChange={(e) => setSearchTerm(e.target.value)}
                        className={`w-full pl-8 pr-3 py-1.5 text-xs rounded-lg border outline-none ${
                          isDark 
                            ? 'bg-slate-950 border-slate-800 text-slate-200 placeholder:text-slate-500 focus:border-indigo-500' 
                            : 'bg-white border-slate-300 text-slate-800 placeholder:text-slate-400 focus:border-indigo-500'
                        }`}
                      />
                    </div>
                  </div>
                </div>

                {/* Table of Impacted Objects */}
                <div className={`rounded-xl border overflow-hidden ${
                  isDark ? 'border-slate-800 bg-slate-950/40' : 'border-slate-200 bg-white'
                }`}>
                  {filteredImpactedObjects.length === 0 ? (
                    <div className="p-8 text-center text-xs text-slate-400">
                      No downstream objects found matching your filter criteria.
                    </div>
                  ) : (
                    <div className="overflow-x-auto max-h-64">
                      <table className="w-full text-left text-xs">
                        <thead className={`sticky top-0 border-b ${
                          isDark ? 'bg-slate-900 border-slate-800 text-slate-400' : 'bg-slate-100 border-slate-200 text-slate-600'
                        }`}>
                          <tr>
                            <th className="px-3.5 py-2 font-semibold">Object / Node</th>
                            <th className="px-3.5 py-2 font-semibold">Layer</th>
                            <th className="px-3.5 py-2 font-semibold">Field / Measure</th>
                            <th className="px-3.5 py-2 font-semibold">Distance</th>
                            <th className="px-3.5 py-2 font-semibold">Severity</th>
                            <th className="px-3.5 py-2 font-semibold">Impact Rationale</th>
                          </tr>
                        </thead>
                        <tbody className="divide-y divide-slate-800/40">
                          {filteredImpactedObjects.map((obj, idx) => (
                            <tr 
                              key={idx} 
                              className={`transition-colors ${
                                isDark ? 'hover:bg-slate-800/40' : 'hover:bg-slate-50'
                              }`}
                            >
                              <td className="px-3.5 py-2.5 font-bold text-slate-200">
                                {obj.nodeName}
                                <span className="block text-[10px] font-normal text-slate-400 font-mono">
                                  {obj.container}
                                </span>
                              </td>
                              <td className="px-3.5 py-2.5">
                                <span className={`inline-block text-[10px] font-semibold px-2 py-0.5 rounded border ${
                                  obj.nodeType === 'report'
                                    ? 'bg-emerald-500/10 border-emerald-500/20 text-emerald-400'
                                    : obj.nodeType === 'dataset_table'
                                    ? 'bg-indigo-500/10 border-indigo-500/20 text-indigo-400'
                                    : 'bg-amber-500/10 border-amber-500/20 text-amber-400'
                                }`}>
                                  {obj.nodeType}
                                </span>
                              </td>
                              <td className="px-3.5 py-2.5 font-mono text-[11px] text-slate-300">
                                {obj.columnName}
                              </td>
                              <td className="px-3.5 py-2.5 text-slate-400 text-[11px]">
                                {obj.relationship === 'direct' ? (
                                  <span className="text-indigo-400 font-semibold">Direct (1)</span>
                                ) : (
                                  <span>Hop {obj.distance}</span>
                                )}
                              </td>
                              <td className="px-3.5 py-2.5">
                                <span className={`text-[10px] font-black uppercase px-2 py-0.5 rounded ${
                                  obj.severity === 'CRITICAL'
                                    ? 'bg-rose-500/20 text-rose-400'
                                    : obj.severity === 'HIGH'
                                    ? 'bg-amber-500/20 text-amber-400'
                                    : obj.severity === 'MEDIUM'
                                    ? 'bg-yellow-500/20 text-yellow-300'
                                    : 'bg-emerald-500/20 text-emerald-400'
                                }`}>
                                  {obj.severity}
                                </span>
                              </td>
                              <td className="px-3.5 py-2.5 text-slate-400 text-[11px] max-w-xs truncate" title={obj.impactDescription}>
                                {obj.impactDescription}
                              </td>
                            </tr>
                          ))}
                        </tbody>
                      </table>
                    </div>
                  )}
                </div>
              </div>
            </>
          ) : null}
        </div>

        {/* Modal Footer Actions */}
        <div className={`px-6 py-3.5 border-t flex flex-col sm:flex-row items-center justify-between gap-3 ${
          isDark ? 'border-slate-800 bg-slate-900/80' : 'border-slate-200 bg-slate-50/80'
        }`}>
          <div className="text-[11px] text-slate-400 flex items-center gap-1.5">
            <Layers className="w-3.5 h-3.5 text-indigo-400" />
            <span>Full graph recursive impact computation</span>
          </div>

          <div className="flex items-center gap-2">
            <button
              onClick={handleCopyMarkdown}
              disabled={!impactData}
              className={`px-3 py-1.5 rounded-lg text-xs font-semibold border flex items-center gap-1.5 transition-all ${
                isDark 
                  ? 'bg-slate-800 hover:bg-slate-700 text-slate-200 border-slate-700' 
                  : 'bg-white hover:bg-slate-100 text-slate-700 border-slate-300 shadow-sm'
              } disabled:opacity-50`}
            >
              {copied ? <Check className="w-3.5 h-3.5 text-emerald-400" /> : <Copy className="w-3.5 h-3.5" />}
              {copied ? 'Copied' : 'Copy Summary'}
            </button>

            <button
              onClick={handleDownloadCsv}
              disabled={!impactData}
              className="px-3 py-1.5 rounded-lg text-xs font-semibold bg-indigo-600 hover:bg-indigo-500 text-white flex items-center gap-1.5 transition-all shadow-md shadow-indigo-600/20 disabled:opacity-50"
            >
              <Download className="w-3.5 h-3.5" />
              Download Audit CSV
            </button>
          </div>
        </div>
      </div>
    </div>
  );
}
