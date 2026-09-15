import React, { useState, useEffect, useCallback } from 'react';
import Header from './components/Header';
import Legend from './components/Legend';
import LineageCanvas from './components/LineageCanvas';
import InspectorPanel from './components/InspectorPanel';
import ImpactAnalysisModal from './components/ImpactAnalysisModal';
import { AlertCircle, RefreshCw } from 'lucide-react';

export default function App() {
  const [graphData, setGraphData] = useState(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(null);

  // Theme state: 'dark' or 'light'
  const [theme, setTheme] = useState(() => {
    return localStorage.getItem('lineage_theme') || 'dark';
  });

  const toggleTheme = useCallback(() => {
    setTheme(prev => {
      const next = prev === 'dark' ? 'light' : 'dark';
      localStorage.setItem('lineage_theme', next);
      return next;
    });
  }, []);

  const [selectedNodeId, setSelectedNodeId] = useState(null);
  const [selectedColumnId, setSelectedColumnId] = useState(null);
  const [focusNodeId, setFocusNodeId] = useState(null);
  const [columnDetails, setColumnDetails] = useState(null);
  const [loadingDetails, setLoadingDetails] = useState(false);

  // Impact analysis modal state
  const [impactModalOpen, setImpactModalOpen] = useState(false);
  const [impactTargetColumnId, setImpactTargetColumnId] = useState('');
  const [impactTargetNodeId, setImpactTargetNodeId] = useState('');

  const handleOpenImpactAnalysis = useCallback((colId, nodeId) => {
    setImpactTargetColumnId(colId || selectedColumnId || '');
    setImpactTargetNodeId(nodeId || selectedNodeId || '');
    setImpactModalOpen(true);
  }, [selectedColumnId, selectedNodeId]);

  const fetchLineageGraph = useCallback(async () => {
    setLoading(true);
    setError(null);
    try {
      const res = await fetch('/api/lineage');
      if (!res.ok) {
        throw new Error(`Server returned HTTP ${res.status}`);
      }
      const data = await res.json();
      setGraphData(data);
    } catch (err) {
      console.error('Failed to load lineage graph:', err);
      setError(err.message || 'Failed to connect to lineage backend API');
    } finally {
      setLoading(false);
    }
  }, []);

  useEffect(() => {
    fetchLineageGraph();
  }, [fetchLineageGraph]);

  const handleSelectNode = useCallback((nodeId) => {
    setFocusNodeId(nodeId);
    setSelectedNodeId(nodeId);
    // When focusing directly on a node/report from search, reset single column lineage selection
    setSelectedColumnId(null);
    setColumnDetails(null);
  }, []);

  const handleSelectColumn = useCallback(async (nodeId, columnId) => {
    if (selectedColumnId === columnId) {
      // Toggle off if same column clicked again
      setSelectedNodeId(null);
      setSelectedColumnId(null);
      setFocusNodeId(null);
      setColumnDetails(null);
      return;
    }

    setSelectedNodeId(nodeId);
    setSelectedColumnId(columnId);
    setFocusNodeId(nodeId);
    setLoadingDetails(true);

    try {
      const res = await fetch(`/api/details?nodeId=${encodeURIComponent(nodeId)}&columnId=${encodeURIComponent(columnId)}`);
      if (!res.ok) throw new Error(`HTTP error ${res.status}`);
      const data = await res.json();
      setColumnDetails(data);
    } catch (err) {
      console.error('Failed to fetch column details:', err);
    } finally {
      setLoadingDetails(false);
    }
  }, [selectedColumnId]);

  const handleResetView = useCallback(() => {
    setSelectedNodeId(null);
    setSelectedColumnId(null);
    setFocusNodeId(null);
    setColumnDetails(null);
  }, []);

  const isDark = theme === 'dark';

  return (
    <div className={`w-screen h-screen flex flex-col overflow-hidden select-none transition-colors duration-200 ${
      isDark ? 'bg-slate-950 text-slate-100' : 'bg-slate-100 text-slate-800'
    }`}>
      {/* Top Header Toolbar */}
      <Header 
        nodes={graphData?.nodes || []}
        summary={graphData?.summary} 
        activeTraceCount={selectedColumnId ? (columnDetails?.upstreamPaths?.length || 1) + (columnDetails?.downstreamPaths?.length || 0) : 0}
        onSelectNode={handleSelectNode}
        onSelectColumn={handleSelectColumn}
        onResetView={handleResetView}
        onRefresh={fetchLineageGraph}
        theme={theme}
        onToggleTheme={toggleTheme}
        onOpenImpactAnalysis={() => handleOpenImpactAnalysis()}
      />

      {/* Main Canvas & Inspector Drawer */}
      <div className="flex-1 relative flex overflow-hidden">
        {loading ? (
          <div className={`w-full h-full flex flex-col items-center justify-center space-y-4 ${
            isDark ? 'bg-slate-950' : 'bg-slate-100'
          }`}>
            <div className="w-10 h-10 border-4 border-indigo-500 border-t-transparent rounded-full animate-spin"></div>
            <p className={`text-sm font-semibold ${isDark ? 'text-slate-300' : 'text-slate-600'}`}>
              Parsing Power BI metadata graph...
            </p>
          </div>
        ) : error ? (
          <div className={`w-full h-full flex flex-col items-center justify-center p-6 ${
            isDark ? 'bg-slate-950' : 'bg-slate-100'
          }`}>
            <div className={`rounded-2xl p-6 max-w-md text-center space-y-4 shadow-2xl border ${
              isDark ? 'bg-slate-900 border-red-500/30' : 'bg-white border-red-300'
            }`}>
              <AlertCircle className="w-12 h-12 text-red-500 mx-auto" />
              <div>
                <h3 className={`text-base font-bold ${isDark ? 'text-slate-100' : 'text-slate-800'}`}>
                  Backend Connection Error
                </h3>
                <p className={`text-xs mt-1 ${isDark ? 'text-slate-400' : 'text-slate-500'}`}>{error}</p>
              </div>
              <button 
                onClick={fetchLineageGraph}
                className="w-full py-2 bg-indigo-600 hover:bg-indigo-500 text-white rounded-lg text-xs font-semibold flex items-center justify-center gap-2 transition-colors shadow-md"
              >
                <RefreshCw className="w-3.5 h-3.5" />
                Retry Connection
              </button>
            </div>
          </div>
        ) : (
          <>
            <LineageCanvas 
              rawNodes={graphData?.nodes || []}
              rawColumnEdges={graphData?.columnEdges || []}
              selectedColumnId={selectedColumnId}
              focusNodeId={focusNodeId}
              onSelectColumn={handleSelectColumn}
              theme={theme}
            />

            <Legend theme={theme} />

            {selectedColumnId && (
              <InspectorPanel 
                details={columnDetails} 
                isLoading={loadingDetails} 
                onClose={handleResetView} 
                theme={theme}
                onOpenImpactAnalysis={handleOpenImpactAnalysis}
              />
            )}
          </>
        )}
      </div>

      {/* Impact Analysis Modal */}
      <ImpactAnalysisModal 
        isOpen={impactModalOpen}
        onClose={() => setImpactModalOpen(false)}
        initialColumnId={impactTargetColumnId}
        initialNodeId={impactTargetNodeId}
        allNodes={graphData?.nodes || []}
        theme={theme}
      />
    </div>
  );
}
