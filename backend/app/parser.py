import sqlite3
from typing import List, Dict, Tuple, Set
from .db import get_db, DB_PATH
from .models import (
    EntityNode, ColumnAttribute, ColumnEdge, TableEdge, LineageGraphResponse,
    LineageDetailsResponse, PathNode, ColumnContributor
)

def get_lineage_graph_from_db(db_path: str = DB_PATH) -> LineageGraphResponse:
    with get_db(db_path) as conn:
        cursor = conn.cursor()

        # 1. Fetch count of incoming sources for each column to mark multi-source derivations
        cursor.execute("""
            SELECT target_column_id, COUNT(*) as cnt 
            FROM column_edges 
            GROUP BY target_column_id
        """)
        incoming_counts = {row["target_column_id"]: row["cnt"] for row in cursor.fetchall()}

        # 2. Fetch all nodes
        cursor.execute("SELECT id, system, container, name, schema_name, type FROM nodes ORDER BY id;")
        node_rows = cursor.fetchall()

        # 3. Fetch all columns
        cursor.execute("""
            SELECT id, node_id, name, data_type, is_calculated, expression, transformation_type 
            FROM columns 
            ORDER BY rowid;
        """)
        col_rows = cursor.fetchall()

        # Group columns by node_id
        node_cols_map: Dict[str, List[ColumnAttribute]] = {}
        for r in col_rows:
            cnt = incoming_counts.get(r["id"], 0)
            is_multi = cnt > 1
            col_attr = ColumnAttribute(
                id=r["id"],
                name=r["name"],
                dataType=r["data_type"],
                isCalculated=bool(r["is_calculated"]) or is_multi,
                isMultiSource=is_multi,
                contributorCount=cnt,
                expression=r["expression"],
                transformationType=r["transformation_type"]
            )
            node_cols_map.setdefault(r["node_id"], []).append(col_attr)

        nodes: List[EntityNode] = []
        for n in node_rows:
            nodes.append(EntityNode(
                id=n["id"],
                name=n["name"],
                type=n["type"],
                database=n["container"],
                schema_name=n["schema_name"],
                system=n["system"],
                columns=node_cols_map.get(n["id"], [])
            ))

        # 4. Fetch column edges
        cursor.execute("""
            SELECT id, source_node_id, source_column_id, target_node_id, target_column_id, 
                   transformation_type, expression, scanner_source 
            FROM column_edges;
        """)
        edge_rows = cursor.fetchall()

        column_edges: List[ColumnEdge] = []
        table_edges: List[TableEdge] = []
        seen_table_edges: Set[Tuple[str, str]] = set()

        for e in edge_rows:
            column_edges.append(ColumnEdge(
                id=e["id"],
                sourceNodeId=e["source_node_id"],
                sourceColumnId=e["source_column_id"],
                targetNodeId=e["target_node_id"],
                targetColumnId=e["target_column_id"],
                transformationType=e["transformation_type"],
                expression=e["expression"],
                scannerSource=e["scanner_source"]
            ))

            t_pair = (e["source_node_id"], e["target_node_id"])
            if t_pair not in seen_table_edges and e["source_node_id"] != e["target_node_id"]:
                seen_table_edges.add(t_pair)
                table_edges.append(TableEdge(
                    id=f"tbl-edge-{e['source_node_id']}-{e['target_node_id']}",
                    sourceNodeId=e["source_node_id"],
                    targetNodeId=e["target_node_id"]
                ))

        return LineageGraphResponse(
            nodes=nodes,
            columnEdges=column_edges,
            tableEdges=table_edges,
            summary={
                "totalNodes": len(nodes),
                "totalColumnEdges": len(column_edges),
                "totalTableEdges": len(table_edges),
                "multiSourceDerivations": sum(1 for cnt in incoming_counts.values() if cnt > 1)
            }
        )

def get_column_details_from_db(node_id: str, column_id: str, db_path: str = DB_PATH) -> LineageDetailsResponse:
    with get_db(db_path) as conn:
        cursor = conn.cursor()

        # Fetch selected column and node info
        cursor.execute("""
            SELECT c.id AS col_id, c.name AS col_name, c.data_type, c.expression, c.transformation_type, c.is_calculated,
                   n.id AS node_id, n.name AS table_name, n.container AS database_name
            FROM columns c
            JOIN nodes n ON c.node_id = n.id
            WHERE c.id = ?;
        """, (column_id,))
        target_row = cursor.fetchone()

        if not target_row:
            raise ValueError(f"Column '{column_id}' not found.")

        # 1. Fetch immediate direct contributors (columns directly feeding this column)
        cursor.execute("""
            SELECT e.source_column_id, e.transformation_type, e.expression,
                   c.name AS col_name, c.data_type, n.name AS table_name, n.container AS database_name
            FROM column_edges e
            JOIN columns c ON e.source_column_id = c.id
            JOIN nodes n ON c.node_id = n.id
            WHERE e.target_column_id = ?;
        """, (column_id,))
        contrib_rows = cursor.fetchall()

        direct_contributors = [
            ColumnContributor(
                columnId=cr["source_column_id"],
                columnName=cr["col_name"],
                tableName=cr["table_name"],
                databaseName=cr["database_name"],
                dataType=cr["data_type"],
                transformationType=cr["transformation_type"],
                expression=cr["expression"]
            )
            for cr in contrib_rows
        ]

        # 2. Fetch full graph nodes and column map for path traversal
        graph = get_lineage_graph_from_db(db_path)
        cols_map: Dict[str, Tuple[EntityNode, ColumnAttribute]] = {}
        for n in graph.nodes:
            for c in n.columns:
                cols_map[c.id] = (n, c)

        upstream_adj: Dict[str, List[ColumnEdge]] = {}
        downstream_adj: Dict[str, List[ColumnEdge]] = {}

        for edge in graph.columnEdges:
            upstream_adj.setdefault(edge.targetColumnId, []).append(edge)
            downstream_adj.setdefault(edge.sourceColumnId, []).append(edge)

        def find_paths(curr_col_id: str, adj: Dict[str, List[ColumnEdge]], direction: str) -> List[List[PathNode]]:
            paths = []

            def dfs(c_id: str, current_path: List[PathNode], visited: Set[str]):
                if c_id not in cols_map or c_id in visited:
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
                        dfs(next_c_id, new_path, visited | {c_id})

            dfs(curr_col_id, [], set())
            return paths

        up_paths = find_paths(column_id, upstream_adj, "upstream")
        down_paths = find_paths(column_id, downstream_adj, "downstream")

        is_multi = len(direct_contributors) > 1

        return LineageDetailsResponse(
            selectedNodeId=target_row["node_id"],
            selectedColumnId=target_row["col_id"],
            columnName=target_row["col_name"],
            tableName=target_row["table_name"],
            databaseName=target_row["database_name"],
            dataType=target_row["data_type"],
            expression=target_row["expression"],
            transformationType=target_row["transformation_type"],
            isMultiSource=is_multi,
            directContributors=direct_contributors,
            upstreamPaths=up_paths,
            downstreamPaths=down_paths
        )
