import React, { useMemo, useCallback } from 'react';
import { 
  ReactFlow, 
  Controls, 
  Background, 
  MiniMap, 
  useNodesState, 
  useEdgesState, 
  BackgroundVariant 
} from '@xyflow/react';
import dagre from 'dagre';
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
    // Estimate node height based on column count
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

export default function LineageCanvas({ 
  rawNodes = [], 
  rawColumnEdges = [], 
  selectedColumnId, 
  onSelectColumn 
}) {
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
    const formatted = rawNodes.map((n) => ({
      id: n.id,
      type: 'tableNode',
      data: {
        ...n,
        selectedColumnId,
        onSelectColumn,
        activePathColumnIds: activeColumnIds,
        isHighlighted: selectedColumnId ? activeNodeIds.has(n.id) : false,
        isDimmed: selectedColumnId ? !activeNodeIds.has(n.id) : false,
      },
      position: { x: 0, y: 0 },
    }));

    // Generate column handles edges
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
        className: selectedColumnId 
          ? (isAct ? 'highlighted' : 'dimmed') 
          : '',
        style: {
          stroke: isAct ? '#818cf8' : '#334155',
          strokeWidth: isAct ? 3 : 1.5,
        },
      };
    });

    return getLayoutedElements(formatted, formattedEdges).nodes;
  }, [rawNodes, rawColumnEdges, selectedColumnId, onSelectColumn, activeNodeIds, activeColumnIds, activeEdgeIds]);

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
        className: selectedColumnId 
          ? (isAct ? 'highlighted' : 'dimmed') 
          : '',
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

  // Sync state when selection updates
  React.useEffect(() => {
    setNodes(initialNodes);
    setEdges(initialEdges);
  }, [initialNodes, initialEdges, setNodes, setEdges]);

  return (
    <div className="w-full h-full relative bg-slate-950">
      <ReactFlow
        nodes={nodes}
        edges={edges}
        nodeTypes={nodeTypes}
        onNodesChange={onNodesChange}
        onEdgesChange={onEdgesChange}
        fitView
        minZoom={0.2}
        maxZoom={1.5}
        defaultEdgeOptions={{ type: 'smoothstep' }}
        proOptions={{ hideAttribution: true }}
      >
        <Background variant={BackgroundVariant.Dots} gap={24} size={1.5} color="#1e293b" />
        <Controls position="bottom-right" />
        <MiniMap 
          nodeColor={(node) => {
            switch (node.data?.type) {
              case 'source_table': return '#fbbf24';
              case 'dataset_table': return '#818cf8';
              case 'report': return '#34d399';
              default: return '#64748b';
            }
          }}
          maskColor="rgba(15, 23, 42, 0.7)"
          position="bottom-left"
        />
      </ReactFlow>
    </div>
  );
}
