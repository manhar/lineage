import React, { useState } from 'react';
import { Handle, Position } from '@xyflow/react';
import { 
  Database, 
  Table, 
  FileText, 
  Search, 
  Hash, 
  Type, 
  Calendar, 
  CheckCircle2, 
  Sparkles,
  GitMerge,
  Layers
} from 'lucide-react';

const getTypeIcon = (type) => {
  switch (type) {
    case 'source_table':
    case 'source_view':
      return <Database className="w-4 h-4 text-amber-400" />;
    case 'dataset_table':
      return <Table className="w-4 h-4 text-indigo-400" />;
    case 'report':
      return <FileText className="w-4 h-4 text-emerald-400" />;
    default:
      return <Layers className="w-4 h-4 text-slate-400" />;
  }
};

const getBadgeStyle = (type) => {
  switch (type) {
    case 'source_table':
      return 'bg-amber-500/10 text-amber-300 border-amber-500/30';
    case 'dataset_table':
      return 'bg-indigo-500/10 text-indigo-300 border-indigo-500/30';
    case 'report':
      return 'bg-emerald-500/10 text-emerald-300 border-emerald-500/30';
    default:
      return 'bg-slate-500/10 text-slate-300 border-slate-500/30';
  }
};

const getDataTypeIcon = (dataType) => {
  const dt = (dataType || '').toLowerCase();
  if (dt.includes('int') || dt.includes('decimal') || dt.includes('number') || dt.includes('float')) {
    return <Hash className="w-3 h-3 text-cyan-400" />;
  }
  if (dt.includes('date') || dt.includes('time')) {
    return <Calendar className="w-3 h-3 text-purple-400" />;
  }
  return <Type className="w-3 h-3 text-slate-400" />;
};

export default function TableNode({ data, id }) {
  const { 
    name, 
    database, 
    schema_name, 
    type, 
    columns = [], 
    selectedColumnId, 
    onSelectColumn, 
    activePathColumnIds = new Set(),
    theme = 'dark'
  } = data;
  const [searchTerm, setSearchTerm] = useState('');

  const isDark = theme === 'dark';

  const filteredColumns = columns.filter(col => 
    col.name.toLowerCase().includes(searchTerm.toLowerCase())
  );

  return (
    <div className={`w-72 backdrop-blur-md rounded-xl border shadow-2xl transition-all duration-300 ${
      isDark ? 'bg-slate-900/90' : 'bg-white/95 text-slate-800'
    } ${
      data.isFocused
        ? 'border-emerald-400 ring-4 ring-emerald-500/60 shadow-emerald-500/30 scale-[1.03]'
        : data.isHighlighted 
          ? 'border-indigo-500 ring-2 ring-indigo-500/40 shadow-indigo-500/20' 
          : data.isDimmed 
            ? 'opacity-30 border-slate-800' 
            : isDark ? 'border-slate-800 hover:border-slate-700' : 'border-slate-200 hover:border-slate-300 shadow-md'
    }`}>
      {/* Node Header */}
      <div className={`p-3.5 border-b rounded-t-xl ${
        isDark ? 'border-slate-800/80 bg-slate-950/50' : 'border-slate-200 bg-slate-50/80'
      }`}>
        <div className="flex items-center justify-between gap-2 mb-1.5">
          <div className="flex items-center gap-2 overflow-hidden">
            {getTypeIcon(type)}
            <span className={`text-xs font-semibold tracking-wide truncate ${isDark ? 'text-slate-300' : 'text-slate-600'}`} title={database}>
              {database}
            </span>
          </div>
          <span className={`text-[10px] uppercase tracking-wider font-semibold px-2 py-0.5 rounded-full border ${getBadgeStyle(type)}`}>
            {schema_name || type.replace('_', ' ')}
          </span>
        </div>

        <h3 className={`text-sm font-bold truncate tracking-tight flex items-center justify-between ${
          isDark ? 'text-slate-100' : 'text-slate-900'
        }`} title={name}>
          <span>{name}</span>
          <span className={`text-[11px] font-normal px-1.5 py-0.5 rounded ${
            isDark ? 'text-slate-400 bg-slate-800/60' : 'text-slate-500 bg-slate-200'
          }`}>
            {columns.length} cols
          </span>
        </h3>

        {/* Quick Search inside node */}
        {columns.length > 5 && (
          <div className="relative mt-2.5">
            <Search className="w-3.5 h-3.5 absolute left-2.5 top-1/2 -translate-y-1/2 text-slate-400" />
            <input 
              type="text" 
              placeholder="Search column..."
              value={searchTerm}
              onChange={(e) => setSearchTerm(e.target.value)}
              className={`w-full rounded-md pl-8 pr-2.5 py-1 text-xs outline-none transition-all ${
                isDark 
                  ? 'bg-slate-900/80 border border-slate-800 text-slate-200 placeholder-slate-500 focus:border-indigo-500' 
                  : 'bg-white border border-slate-300 text-slate-800 placeholder-slate-400 focus:border-indigo-500 shadow-inner'
              }`}
            />
          </div>
        )}
      </div>

      {/* Column Row List */}
      <div className="p-2 space-y-1 max-h-[320px] overflow-y-auto">
        {filteredColumns.length === 0 ? (
          <p className="text-xs text-slate-400 py-3 text-center italic">No matching columns</p>
        ) : (
          filteredColumns.map((col) => {
            const isSelected = selectedColumnId === col.id;
            const isInActivePath = activePathColumnIds.has(col.id);

            return (
              <div
                key={col.id}
                onClick={() => onSelectColumn && onSelectColumn(id, col.id)}
                className={`group relative flex items-center justify-between px-2.5 py-1.5 rounded-lg text-xs font-medium cursor-pointer transition-all duration-200 select-none ${
                  isSelected 
                    ? (isDark 
                        ? 'bg-indigo-600/30 text-indigo-200 border border-indigo-500/60 shadow-sm shadow-indigo-500/20'
                        : 'bg-indigo-100 text-indigo-900 border border-indigo-400 shadow-sm')
                    : isInActivePath
                      ? (isDark 
                          ? 'bg-indigo-950/50 text-indigo-300 border border-indigo-700/50'
                          : 'bg-indigo-50 text-indigo-800 border border-indigo-200')
                      : (isDark 
                          ? 'hover:bg-slate-800/60 text-slate-300 border border-transparent'
                          : 'hover:bg-slate-100 text-slate-700 border border-transparent')
                }`}
              >
                {/* Left Handle (Target) */}
                <Handle
                  type="target"
                  position={Position.Left}
                  id={`${col.id}-target`}
                  style={{
                    left: -12,
                    top: '50%',
                    transform: 'translateY(-50%)',
                  }}
                  className="!w-2.5 !h-2.5 !bg-indigo-500 hover:!scale-125 transition-transform"
                />

                {/* Column details */}
                <div className="flex items-center gap-1.5 overflow-hidden">
                  <div className={`p-1 rounded transition-colors ${
                    isDark ? 'bg-slate-800/80 group-hover:bg-slate-700/80' : 'bg-slate-100 group-hover:bg-slate-200'
                  }`}>
                    {getDataTypeIcon(col.dataType)}
                  </div>
                  <span className="truncate" title={col.name}>
                    {col.name}
                  </span>
                  {col.isMultiSource ? (
                    <span 
                      className="text-[9px] font-bold text-amber-500 bg-amber-500/20 border border-amber-500/30 px-1 py-0.2 rounded flex items-center gap-0.5 shrink-0" 
                      title={`Derived from ${col.contributorCount} source columns`}
                    >
                      <GitMerge className="w-2.5 h-2.5" />
                      {col.contributorCount}
                    </span>
                  ) : col.isCalculated && (
                    <Sparkles className="w-3 h-3 text-amber-500 shrink-0" title="Calculated Column (SQL/DAX/M)" />
                  )}
                </div>

                <div className="flex items-center gap-1.5">
                  <span className={`text-[10px] font-mono ${isDark ? 'text-slate-500' : 'text-slate-400'}`}>
                    {col.dataType}
                  </span>
                  {isSelected && (
                    <CheckCircle2 className="w-3.5 h-3.5 text-indigo-500 shrink-0" />
                  )}
                </div>

                {/* Right Handle (Source) */}
                <Handle
                  type="source"
                  position={Position.Right}
                  id={`${col.id}-source`}
                  style={{
                    right: -12,
                    top: '50%',
                    transform: 'translateY(-50%)',
                  }}
                  className="!w-2.5 !h-2.5 !bg-indigo-500 hover:!scale-125 transition-transform"
                />
              </div>
            );
          })
        )}
      </div>
    </div>
  );
}
