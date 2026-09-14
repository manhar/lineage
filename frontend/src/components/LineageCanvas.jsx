import React, { useMemo, useEffect } from 'react';
import { 
  ReactFlow, 
  Controls, 
  Background, 
  MiniMap, 
  useNodesState, 
  useEdgesState, 
  BackgroundVariant,
  ReactFlowProvider,
  useReactFlow
} from '@xyflow/react';
import dagre from 'dagre';
import { Compass } from 'lucide-react';
import TableNode from './TableNode';

const nodeTypes = {
  tableNode: TableNode,
};

const NODE_WIDTH = 290;

const getLayoutedElements = (nodes, edges, direction = 'LR') => {
  const dagreGraph = new dagre.graphlib.Graph();
  dagreGraph.setDefaultEdgeLabel(() => ({}));
  dagreGraph.setGraph({ rankdir: direction, nodesep: 50, ranksep: 200 });

  nodes.forEach((node) => {
    const colCount = node.data.columns ? node.data.columns.length : 1;
    const nodeHeight = Math.max(140, 75 + colCount * 36);
    dagreGraph.setNode(node.id, { width: NODE_WIDTH, height: nodeHeight });
  });

  edges.forEach((edge) => {
    dagreGraph.setEdge(edge.source, edge.target);
  });

  dagre.layout(dagreGraph);

  const layoutedNodes = nodes.map((node) => {
    const nodeWithPosition = dagreGraph.node(node.id);
    const colCount = node.data.columns ? node.data.columns.length : 1;
    const nodeHeight = Math.max(140, 75 + colCount * 36);

    return {
      ...node,
      targetPosition: 'left',
      sourcePosition: 'right',
      position: {
        x: nodeWithPosition.x - NODE_WIDTH / 2,
        y: nodeWithPosition.y - nodeHeight / 2,
      },
    };
  });

  return { nodes: layoutedNodes, edges };
};

function CanvasInner({
  rawNodes = [],
  rawColumnEdges = [],
  selectedColumnId,
  focusNodeId,
  onSelectColumn
}) {
  const { fitView } = useReactFlow();

  // Compute active lineage subgraph when a column is selected
  const { activeNodeIds, activeColumnIds, activeEdgeIds } = useMemo(() => {
    if (!selectedColumnId) {
      return { 
        activeNodeIds: new Set(), 
        activeColumnIds: new Set(), 
        activeEdgeIds: new Set() 
      };
    }

    const colToNodeMap = new Map();
    rawNodes.forEach(n => {
      n.columns.forEach(c => colToNodeMap.set(c.id, n.id));
    });

    const activeCols = new Set([selectedColumnId]);
    const activeNodes = new Set();
    const activeEdges = new Set();

    if (colToNodeMap.has(selectedColumnId)) {
      activeNodes.add(colToNodeMap.get(selectedColumnId));
    }

    // Upstream traversal
    const upstreamEdgesMap = new Map();
    rawColumnEdges.forEach(e => {
      if (!upstreamEdgesMap.has(e.targetColumnId)) upstreamEdgesMap.set(e.targetColumnId, []);
      upstreamEdgesMap.get(e.targetColumnId).push(e);
    });

    const queueUp = [selectedColumnId];
    while (queueUp.length > 0) {
      const curr = queueUp.shift();
      const parents = upstreamEdgesMap.get(curr) || [];
      parents.forEach(e => {
        activeEdges.add(e.id);
        if (!activeCols.has(e.sourceColumnId)) {
          activeCols.add(e.sourceColumnId);
          if (colToNodeMap.has(e.sourceColumnId)) {
            activeNodes.add(colToNodeMap.get(e.sourceColumnId));
          }
          queueUp.push(e.sourceColumnId);
        }
      });
    }

    // Downstream traversal
    const downstreamEdgesMap = new Map();
    rawColumnEdges.forEach(e => {
      if (!downstreamEdgesMap.has(e.sourceColumnId)) downstreamEdgesMap.set(e.sourceColumnId, []);
      downstreamEdgesMap.get(e.sourceColumnId).push(e);
    });

    const queueDown = [selectedColumnId];
    while (queueDown.length > 0) {
      const curr = queueDown.shift();
      const children = downstreamEdgesMap.get(curr) || [];
      children.forEach(e => {
        activeEdges.add(e.id);
        if (!activeCols.has(e.targetColumnId)) {
          activeCols.add(e.targetColumnId);
          if (colToNodeMap.has(e.targetColumnId)) {
            activeNodes.add(colToNodeMap.get(e.targetColumnId));
          }
          queueDown.push(e.targetColumnId);
        }
      });
    }

    return { activeNodeIds: activeNodes, activeColumnIds: activeCols, activeEdgeIds: activeEdges };
  }, [selectedColumnId, rawNodes, rawColumnEdges]);

  // Convert raw API nodes & edges into React Flow format
  const initialNodes = useMemo(() => {
    const formatted = rawNodes.map((n) => {
      const isFocused = focusNodeId === n.id;
      const isHighlighted = selectedColumnId ? activeNodeIds.has(n.id) : isFocused;
      const isDimmed = selectedColumnId ? !activeNodeIds.has(n.id) : (focusNodeId ? !isFocused : false);

      return {
        id: n.id,
        type: 'tableNode',
        data: {
          ...n,
          selectedColumnId,
          onSelectColumn,
          activePathColumnIds: activeColumnIds,
          isFocused,
          isHighlighted,
          isDimmed,
        },
        position: { x: 0, y: 0 },
      };
    });

    const formattedEdges = rawColumnEdges.map((e) => {
      const isAct = activeEdgeIds.has(e.id);
      return {
        id: e.id,
        source: e.sourceNodeId,
        sourceHandle: `${e.sourceColumnId}-source`,
        target: e.targetNodeId,
        targetHandle: `${e.targetColumnId}-target`,
        type: 'smoothstep',
        animated: isAct,
        className: selectedColumnId ? (isAct ? 'highlighted' : 'dimmed') : '',
        style: {
          stroke: isAct ? '#818cf8' : '#334155',
          strokeWidth: isAct ? 3 : 1.5,
        },
      };
    });

    return getLayoutedElements(formatted, formattedEdges).nodes;
  }, [rawNodes, rawColumnEdges, selectedColumnId, focusNodeId, onSelectColumn, activeNodeIds, activeColumnIds, activeEdgeIds]);

  const initialEdges = useMemo(() => {
    const formatted = rawNodes.map((n) => ({
      id: n.id,
      type: 'tableNode',
      data: { ...n },
      position: { x: 0, y: 0 },
    }));

    const formattedEdges = rawColumnEdges.map((e) => {
      const isAct = activeEdgeIds.has(e.id);
      return {
        id: e.id,
        source: e.sourceNodeId,
        sourceHandle: `${e.sourceColumnId}-source`,
        target: e.targetNodeId,
        targetHandle: `${e.targetColumnId}-target`,
        type: 'smoothstep',
        animated: isAct,
        className: selectedColumnId ? (isAct ? 'highlighted' : 'dimmed') : '',
        style: {
          stroke: isAct ? '#818cf8' : '#334155',
          strokeWidth: isAct ? 3 : 1.5,
        },
      };
    });

    return getLayoutedElements(formatted, formattedEdges).edges;
  }, [rawNodes, rawColumnEdges, selectedColumnId, activeEdgeIds]);

  const [nodes, setNodes, onNodesChange] = useNodesState(initialNodes);
  const [edges, setEdges, onEdgesChange] = useEdgesState(initialEdges);

  // Sync state when selection/focus updates
  useEffect(() => {
    setNodes(initialNodes);
    setEdges(initialEdges);
  }, [initialNodes, initialEdges, setNodes, setEdges]);

  // Smoothly center & zoom when a node is searched / focused
  useEffect(() => {
    if (focusNodeId) {
      fitView({
        nodes: [{ id: focusNodeId }],
        duration: 800,
        padding: 0.6,
        maxZoom: 1.15
      });
    }
  }, [focusNodeId, fitView]);

  return (
    <div className="w-full h-full relative bg-slate-950">
      <ReactFlow
        nodes={nodes}
        edges={edges}
        nodeTypes={nodeTypes}
        onNodesChange={onNodesChange}
        onEdgesChange={onEdgesChange}
        fitView
        minZoom={0.15}
        maxZoom={1.6}
        defaultEdgeOptions={{ type: 'smoothstep' }}
        proOptions={{ hideAttribution: true }}
      >
        <Background variant={BackgroundVariant.Dots} gap={24} size={1.5} color="#1e293b" />
        <Controls position="bottom-right" />

        {/* Eagle View (MiniMap) Badge & Interactive Viewfinder */}
        <div className="absolute bottom-[170px] left-6 z-10 flex items-center gap-1.5 px-2.5 py-1 rounded-md bg-slate-900/90 border border-slate-800 text-[11px] font-semibold text-slate-300 shadow-lg pointer-events-none">
          <Compass className="w-3.5 h-3.5 text-indigo-400" />
          <span>Eagle View Navigator</span>
          <span className="text-[10px] text-slate-500 font-normal">(Drag or click to move)</span>
        </div>

        <MiniMap 
          nodeColor={(node) => {
            if (node.data?.isFocused) return '#10b981';
            switch (node.data?.type) {
              case 'source_table': return '#fbbf24';
              case 'dataset_table': return '#818cf8';
              case 'report': return '#34d399';
              default: return '#64748b';
            }
          }}
          maskColor="rgba(15, 23, 42, 0.75)"
          position="bottom-left"
          pannable={true}
          zoomable={true}
          nodeStrokeWidth={3}
          nodeBorderRadius={4}
          className="!w-64 !h-36 !rounded-xl !border !border-slate-800/90 !shadow-2xl !bg-slate-950/90 backdrop-blur-md cursor-grab active:cursor-grabbing hover:!border-indigo-500/50 transition-all"
        />
      </ReactFlow>
    </div>
  );
}

export default function LineageCanvas(props) {
  return (
    <ReactFlowProvider>
      <CanvasInner {...props} />
    </ReactFlowProvider>
  );
}
