import json
import os
from typing import List, Dict, Tuple, Set
from .models import (
    EntityNode, ColumnAttribute, ColumnEdge, TableEdge, LineageGraphResponse,
    LineageDetailsResponse, PathNode
)

def load_scanner_json(file_path: str = None) -> dict:
    if file_path is None:
        file_path = os.path.join(os.path.dirname(__file__), "data", "scanner_output.json")
    with open(file_path, "r", encoding="utf-8") as f:
        return json.load(f)

def parse_lineage_graph(scanner_data: dict) -> LineageGraphResponse:
    nodes: List[EntityNode] = []
    column_edges: List[ColumnEdge] = []
    table_edges: List[TableEdge] = []
    seen_table_edges: Set[Tuple[str, str]] = set()

    for ws in scanner_data.get("workspaces", []):
        # 1. Source Systems
        for src in ws.get("sourceSystems", []):
            cols = [
                ColumnAttribute(
                    id=c["id"],
                    name=c["name"],
                    dataType=c["dataType"],
                    expression=c.get("expression")
                ) for c in src.get("columns", [])
            ]
            nodes.append(EntityNode(
                id=src["id"],
                name=src["name"],
                type=src.get("type", "source_table"),
                database=src.get("database", "Source System"),
                schema_name=src.get("schema", "dbo"),
                columns=cols
            ))

        # 2. Datasets
        for ds in ws.get("datasets", []):
            for tbl in ds.get("tables", []):
                cols = []
                for c in tbl.get("columns", []):
                    col_attr = ColumnAttribute(
                        id=c["id"],
                        name=c["name"],
                        dataType=c["dataType"],
                        isCalculated=c.get("isCalculated", False),
                        sourceColumn=c.get("sourceColumn"),
                        sourceTableId=c.get("sourceTableId"),
                        sourceColumnId=c.get("sourceColumnId"),
                        transformationType=c.get("transformationType"),
                        expression=c.get("expression")
                    )
                    cols.append(col_attr)

                    # Build Column-Level Edge if source exists
                    if c.get("sourceTableId") and c.get("sourceColumnId"):
                        edge_id = f"edge-{c['sourceColumnId']}-{c['id']}"
                        column_edges.append(ColumnEdge(
                            id=edge_id,
                            sourceNodeId=c["sourceTableId"],
                            sourceColumnId=c["sourceColumnId"],
                            targetNodeId=tbl["id"],
                            targetColumnId=c["id"],
                            transformationType=c.get("transformationType"),
                            expression=c.get("expression")
                        ))
                        # Record Table-Level Edge
                        t_pair = (c["sourceTableId"], tbl["id"])
                        if t_pair not in seen_table_edges and c["sourceTableId"] != tbl["id"]:
                            seen_table_edges.add(t_pair)
                            table_edges.append(TableEdge(
                                id=f"tbl-edge-{c['sourceTableId']}-{tbl['id']}",
                                sourceNodeId=c["sourceTableId"],
                                targetNodeId=tbl["id"]
                            ))

                nodes.append(EntityNode(
                    id=tbl["id"],
                    name=tbl["name"],
                    type=tbl.get("type", "dataset_table"),
                    database=tbl.get("database", ds["name"]),
                    schema_name=tbl.get("schema", "dbo"),
                    columns=cols
                ))

        # 3. Reports
        for rpt in ws.get("reports", []):
            for vw in rpt.get("views", []):
                cols = []
                for c in vw.get("columns", []):
                    col_attr = ColumnAttribute(
                        id=c["id"],
                        name=c["name"],
                        dataType=c["dataType"],
                        sourceColumn=c.get("sourceColumn"),
                        sourceTableId=c.get("sourceTableId"),
                        sourceColumnId=c.get("sourceColumnId"),
                        transformationType=c.get("transformationType"),
                        expression=c.get("expression")
                    )
                    cols.append(col_attr)

                    if c.get("sourceTableId") and c.get("sourceColumnId"):
                        edge_id = f"edge-{c['sourceColumnId']}-{c['id']}"
                        column_edges.append(ColumnEdge(
                            id=edge_id,
                            sourceNodeId=c["sourceTableId"],
                            sourceColumnId=c["sourceColumnId"],
                            targetNodeId=vw["id"],
                            targetColumnId=c["id"],
                            transformationType=c.get("transformationType"),
                            expression=c.get("expression")
                        ))
                        t_pair = (c["sourceTableId"], vw["id"])
                        if t_pair not in seen_table_edges:
                            seen_table_edges.add(t_pair)
                            table_edges.append(TableEdge(
                                id=f"tbl-edge-{c['sourceTableId']}-{vw['id']}",
                                sourceNodeId=c["sourceTableId"],
                                targetNodeId=vw["id"]
                            ))

                nodes.append(EntityNode(
                    id=vw["id"],
                    name=vw["name"],
                    type=vw.get("type", "report"),
                    database=vw.get("database", rpt["name"]),
                    schema_name=vw.get("schema", "Visual"),
                    columns=cols
                ))

    return LineageGraphResponse(
        nodes=nodes,
        columnEdges=column_edges,
        tableEdges=table_edges,
        summary={
            "totalNodes": len(nodes),
            "totalColumnEdges": len(column_edges),
            "totalTableEdges": len(table_edges)
        }
    )

def get_column_details(node_id: str, column_id: str, graph: LineageGraphResponse) -> LineageDetailsResponse:
    nodes_map: Dict[str, EntityNode] = {n.id: n for n in graph.nodes}
    cols_map: Dict[str, Tuple[EntityNode, ColumnAttribute]] = {}
    for n in graph.nodes:
        for c in n.columns:
            cols_map[c.id] = (n, c)

    if column_id not in cols_map:
        raise ValueError(f"Column '{column_id}' not found.")

    target_node, target_col = cols_map[column_id]

    # Map edges for quick traversal
    upstream_adj: Dict[str, List[ColumnEdge]] = {}
    downstream_adj: Dict[str, List[ColumnEdge]] = {}

    for edge in graph.columnEdges:
        upstream_adj.setdefault(edge.targetColumnId, []).append(edge)
        downstream_adj.setdefault(edge.sourceColumnId, []).append(edge)

    def find_paths(curr_col_id: str, adj: Dict[str, List[ColumnEdge]], direction: str) -> List[List[PathNode]]:
        paths = []

        def dfs(c_id: str, current_path: List[PathNode]):
            if c_id not in cols_map:
                return
            n_obj, c_obj = cols_map[c_id]
            pn = PathNode(
                nodeId=n_obj.id,
                nodeName=n_obj.name,
                columnId=c_obj.id,
                columnName=c_obj.name,
                dataType=c_obj.dataType,
                transformationType=c_obj.transformationType,
                expression=c_obj.expression
            )

            new_path = current_path + [pn]
            next_edges = adj.get(c_id, [])

            if not next_edges:
                paths.append(new_path)
            else:
                for e in next_edges:
                    next_c_id = e.sourceColumnId if direction == "upstream" else e.targetColumnId
                    dfs(next_c_id, new_path)

        dfs(curr_col_id, [])
        return paths

    up_paths = find_paths(column_id, upstream_adj, "upstream")
    down_paths = find_paths(column_id, downstream_adj, "downstream")

    return LineageDetailsResponse(
        selectedNodeId=node_id,
        selectedColumnId=column_id,
        columnName=target_col.name,
        tableName=target_node.name,
        databaseName=target_node.database,
        dataType=target_col.dataType,
        expression=target_col.expression,
        transformationType=target_col.transformationType,
        upstreamPaths=up_paths,
        downstreamPaths=down_paths
    )
