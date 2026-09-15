import React, { useState, useRef, useEffect, useMemo } from 'react';
import { Search, X, FileText, Table, Database, Hash, Type, Sparkles, ChevronRight } from 'lucide-react';

export default function SearchBar({ nodes = [], onSelectNode, onSelectColumn, theme = 'dark' }) {
  const [query, setQuery] = useState('');
  const [isOpen, setIsOpen] = useState(false);
  const containerRef = useRef(null);
  const inputRef = useRef(null);

  const isDark = theme === 'dark';

  // Close dropdown on click outside
  useEffect(() => {
    function handleClickOutside(event) {
      if (containerRef.current && !containerRef.current.contains(event.target)) {
        setIsOpen(false);
      }
    }
    document.addEventListener('mousedown', handleClickOutside);
    return () => document.removeEventListener('mousedown', handleClickOutside);
  }, []);

  // Keyboard shortcut (Cmd+K / Ctrl+K or /) to focus search
  useEffect(() => {
    function handleKeyDown(e) {
      if ((e.metaKey || e.ctrlKey) && e.key === 'k') {
        e.preventDefault();
        inputRef.current?.focus();
        setIsOpen(true);
      }
      if (e.key === 'Escape') {
        setIsOpen(false);
        inputRef.current?.blur();
      }
    }
    window.addEventListener('keydown', handleKeyDown);
    return () => window.removeEventListener('keydown', handleKeyDown);
  }, []);

  // Filter and categorize search results
  const results = useMemo(() => {
    const q = query.trim().toLowerCase();
    if (!q) return { reports: [], tables: [], columns: [] };

    const reports = [];
    const tables = [];
    const columns = [];

    nodes.forEach((node) => {
      const nodeNameMatch = node.name.toLowerCase().includes(q);
      const containerMatch = (node.database || '').toLowerCase().includes(q);

      if (node.type === 'report') {
        if (nodeNameMatch || containerMatch) {
          reports.push(node);
        }
      } else {
        if (nodeNameMatch || containerMatch) {
          tables.push(node);
        }
      }

      // Check columns
      (node.columns || []).forEach((col) => {
        if (col.name.toLowerCase().includes(q)) {
          columns.push({
            nodeId: node.id,
            nodeName: node.name,
            nodeContainer: node.database,
            nodeType: node.type,
            column: col
          });
        }
      });
    });

    return {
      reports: reports.slice(0, 5),
      tables: tables.slice(0, 5),
      columns: columns.slice(0, 6)
    };
  }, [query, nodes]);

  const totalResults = results.reports.length + results.tables.length + results.columns.length;

  const handleChooseNode = (nodeId) => {
    onSelectNode(nodeId);
    setIsOpen(false);
    setQuery('');
  };

  const handleChooseColumn = (nodeId, colId) => {
    onSelectColumn(nodeId, colId);
    setIsOpen(false);
    setQuery('');
  };

  return (
    <div ref={containerRef} className="relative w-72 md:w-80 lg:w-96">
      {/* Search Input Box */}
      <div className="relative flex items-center">
        <Search className={`w-4 h-4 absolute left-3 pointer-events-none ${isDark ? 'text-slate-400' : 'text-slate-400'}`} />
        <input
          ref={inputRef}
          type="text"
          value={query}
          onChange={(e) => {
            setQuery(e.target.value);
            setIsOpen(true);
          }}
          onFocus={() => setIsOpen(true)}
          placeholder="Search report, table, or column... (⌘K)"
          className={`w-full rounded-lg pl-9 pr-8 py-1.5 text-xs transition-all outline-none border ${
            isDark 
              ? 'bg-slate-950/80 border-slate-800 hover:border-slate-700 focus:border-indigo-500 focus:ring-1 focus:ring-indigo-500 text-slate-100 placeholder-slate-500' 
              : 'bg-slate-100 border-slate-300 hover:border-slate-400 focus:border-indigo-500 focus:ring-1 focus:ring-indigo-500 text-slate-800 placeholder-slate-400 shadow-inner'
          }`}
        />
        {query ? (
          <button
            onClick={() => {
              setQuery('');
              setIsOpen(false);
            }}
            className={`absolute right-2.5 ${isDark ? 'text-slate-400 hover:text-slate-200' : 'text-slate-400 hover:text-slate-600'}`}
          >
            <X className="w-3.5 h-3.5" />
          </button>
        ) : (
          <kbd className={`absolute right-2 text-[10px] font-mono border px-1.5 py-0.5 rounded pointer-events-none hidden sm:inline-block ${
            isDark ? 'bg-slate-900 border-slate-800 text-slate-500' : 'bg-white border-slate-300 text-slate-400 shadow-xs'
          }`}>
            ⌘K
          </kbd>
        )}
      </div>

      {/* Search Results Dropdown */}
      {isOpen && query.trim().length > 0 && (
        <div className={`absolute top-full mt-2 left-0 right-0 rounded-xl border shadow-2xl overflow-hidden z-50 max-h-[420px] overflow-y-auto divide-y animate-in fade-in zoom-in-95 duration-150 ${
          isDark 
            ? 'bg-slate-900/95 backdrop-blur-xl border-slate-800 divide-slate-800/60 text-slate-100' 
            : 'bg-white/95 backdrop-blur-xl border-slate-200 divide-slate-100 text-slate-800 shadow-xl'
        }`}>
          {totalResults === 0 ? (
            <div className={`p-4 text-center text-xs italic ${isDark ? 'text-slate-400' : 'text-slate-500'}`}>
              No reports, tables, or columns matching "{query}"
            </div>
          ) : (
            <>
              {/* Reports Section */}
              {results.reports.length > 0 && (
                <div className="p-2">
                  <div className="px-2 py-1 text-[10px] font-bold uppercase tracking-wider text-emerald-500 flex items-center justify-between">
                    <span>Reports & Visuals</span>
                    <span className="text-[10px] bg-emerald-500/10 px-1.5 py-0.2 rounded border border-emerald-500/20">
                      {results.reports.length}
                    </span>
                  </div>
                  {results.reports.map((r) => (
                    <div
                      key={r.id}
                      onClick={() => handleChooseNode(r.id)}
                      className={`flex items-center justify-between px-2.5 py-2 rounded-lg text-xs cursor-pointer transition-colors group ${
                        isDark ? 'hover:bg-slate-800/80' : 'hover:bg-slate-100'
                      }`}
                    >
                      <div className="flex items-center gap-2 overflow-hidden">
                        <div className="p-1 rounded bg-emerald-500/10 text-emerald-500 border border-emerald-500/20 shrink-0">
                          <FileText className="w-3.5 h-3.5" />
                        </div>
                        <div className="overflow-hidden">
                          <p className={`font-semibold truncate transition-colors ${
                            isDark ? 'text-slate-100 group-hover:text-emerald-300' : 'text-slate-800 group-hover:text-emerald-600'
                          }`}>
                            {r.name}
                          </p>
                          <p className={`text-[10px] truncate ${isDark ? 'text-slate-400' : 'text-slate-500'}`}>
                            {r.database} • {r.schema_name}
                          </p>
                        </div>
                      </div>
                      <span className="text-[10px] text-emerald-500 bg-emerald-500/10 border border-emerald-500/30 px-1.5 py-0.5 rounded font-medium shrink-0">
                        Focus Report
                      </span>
                    </div>
                  ))}
                </div>
              )}

              {/* Tables & Datasets Section */}
              {results.tables.length > 0 && (
                <div className="p-2">
                  <div className="px-2 py-1 text-[10px] font-bold uppercase tracking-wider text-indigo-500 flex items-center justify-between">
                    <span>Tables & Datasets</span>
                    <span className="text-[10px] bg-indigo-500/10 px-1.5 py-0.2 rounded border border-indigo-500/20">
                      {results.tables.length}
                    </span>
                  </div>
                  {results.tables.map((t) => (
                    <div
                      key={t.id}
                      onClick={() => handleChooseNode(t.id)}
                      className={`flex items-center justify-between px-2.5 py-2 rounded-lg text-xs cursor-pointer transition-colors group ${
                        isDark ? 'hover:bg-slate-800/80' : 'hover:bg-slate-100'
                      }`}
                    >
                      <div className="flex items-center gap-2 overflow-hidden">
                        <div className="p-1 rounded bg-indigo-500/10 text-indigo-500 border border-indigo-500/20 shrink-0">
                          {t.type === 'source_table' ? <Database className="w-3.5 h-3.5 text-amber-500" /> : <Table className="w-3.5 h-3.5" />}
                        </div>
                        <div className="overflow-hidden">
                          <p className={`font-semibold truncate transition-colors ${
                            isDark ? 'text-slate-100 group-hover:text-indigo-300' : 'text-slate-800 group-hover:text-indigo-600'
                          }`}>
                            {t.name}
                          </p>
                          <p className={`text-[10px] truncate ${isDark ? 'text-slate-400' : 'text-slate-500'}`}>
                            {t.database} • {t.columns?.length || 0} columns
                          </p>
                        </div>
                      </div>
                      <ChevronRight className="w-3.5 h-3.5 text-slate-400 group-hover:text-slate-600 shrink-0" />
                    </div>
                  ))}
                </div>
              )}

              {/* Columns & Measures Section */}
              {results.columns.length > 0 && (
                <div className="p-2">
                  <div className="px-2 py-1 text-[10px] font-bold uppercase tracking-wider text-cyan-500 flex items-center justify-between">
                    <span>Columns & Measures</span>
                    <span className="text-[10px] bg-cyan-500/10 px-1.5 py-0.2 rounded border border-cyan-500/20">
                      {results.columns.length}
                    </span>
                  </div>
                  {results.columns.map((c, i) => (
                    <div
                      key={i}
                      onClick={() => handleChooseColumn(c.nodeId, c.column.id)}
                      className={`flex items-center justify-between px-2.5 py-2 rounded-lg text-xs cursor-pointer transition-colors group ${
                        isDark ? 'hover:bg-slate-800/80' : 'hover:bg-slate-100'
                      }`}
                    >
                      <div className="flex items-center gap-2 overflow-hidden">
                        <div className="p-1 rounded bg-cyan-500/10 text-cyan-500 border border-cyan-500/20 shrink-0">
                          <Hash className="w-3.5 h-3.5" />
                        </div>
                        <div className="overflow-hidden">
                          <p className={`font-semibold truncate transition-colors ${
                            isDark ? 'text-slate-100 group-hover:text-cyan-300' : 'text-slate-800 group-hover:text-cyan-600'
                          }`}>
                            {c.column.name}
                          </p>
                          <p className={`text-[10px] truncate ${isDark ? 'text-slate-400' : 'text-slate-500'}`}>
                            in <span className={`font-medium ${isDark ? 'text-slate-300' : 'text-slate-700'}`}>{c.nodeName}</span> ({c.nodeContainer})
                          </p>
                        </div>
                      </div>
                      <span className="text-[10px] text-indigo-500 bg-indigo-500/10 border border-indigo-500/30 px-1.5 py-0.5 rounded font-medium shrink-0 flex items-center gap-1">
                        <Sparkles className="w-2.5 h-2.5 text-amber-500" />
                        Trace Lineage
                      </span>
                    </div>
                  ))}
                </div>
              )}
            </>
          )}
        </div>
      )}
    </div>
  );
}
