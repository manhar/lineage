from typing import List, Dict, Set, Tuple, Optional
from .db import get_db, DB_PATH
from .models import (
    ImpactAnalysisResponse, TargetColumnInfo, ImpactAnalysisSummary,
    ImpactedObject, PathNode
)
from .parser import get_lineage_graph_from_db

def calculate_column_impact(
    column_id: str,
    action: str = "delete",
    db_path: str = DB_PATH
) -> ImpactAnalysisResponse:
    """
    Computes downstream blast-radius and impact analysis when a column is changed:
    - 'delete': High/Critical risk. Any downstream report, visual, measure, or calculation referencing it breaks.
    - 'update': Medium/High risk. Downstream measures or visuals may require formula/type alignment.
    - 'add': Low/Info risk. Non-breaking additive extension available for consumption.
    """
    action = action.lower()
    if action not in {"delete", "update", "add"}:
        action = "delete"

    with get_db(db_path) as conn:
        cursor = conn.cursor()

        # 1. Fetch target column & node metadata
        cursor.execute("""
            SELECT c.id AS col_id, c.name AS col_name, c.data_type, c.expression,
                   n.id AS node_id, n.name AS node_name, n.container, n.schema_name, n.system, n.type AS node_type
            FROM columns c
            JOIN nodes n ON c.node_id = n.id
            WHERE c.id = ?;
        """, (column_id,))
        target_row = cursor.fetchone()

        if not target_row:
            raise ValueError(f"Column '{column_id}' does not exist in the lineage database.")

        target_info = TargetColumnInfo(
            nodeId=target_row["node_id"],
            nodeName=target_row["node_name"],
            nodeType=target_row["node_type"],
            container=target_row["container"],
            system=target_row["system"],
            columnId=target_row["col_id"],
            columnName=target_row["col_name"],
            dataType=target_row["data_type"],
            expression=target_row["expression"]
        )

        # 2. Get full verified lineage graph
        graph = get_lineage_graph_from_db(db_path)
        cols_map = {}
        for n in graph.nodes:
            for c in n.columns:
                cols_map[c.id] = (n, c)

        # Build downstream adjacency
        downstream_adj: Dict[str, List] = {}
        for edge in graph.columnEdges:
            downstream_adj.setdefault(edge.sourceColumnId, []).append(edge)

        # 3. BFS Traversal to compute downstream blast-radius
        queue: List[Tuple[str, int]] = [(column_id, 0)]
        visited_cols: Set[str] = {column_id}
        impacted_objects: List[ImpactedObject] = []

        while queue:
            curr_col, dist = queue.pop(0)
            next_edges = downstream_adj.get(curr_col, [])

            for edge in next_edges:
                target_col_id = edge.targetColumnId
                if target_col_id not in visited_cols:
                    visited_cols.add(target_col_id)
                    queue.append((target_col_id, dist + 1))

                    if target_col_id in cols_map:
                        node_obj, col_obj = cols_map[target_col_id]
                        d = dist + 1
                        rel = "direct" if d == 1 else "transitive"

                        # Assess severity and impact description based on action & target node type
                        if action == "delete":
                            if node_obj.type == "report":
                                severity = "CRITICAL"
                                desc = f"Report broken: visual binding in '{node_obj.name}' depends on this column."
                            elif col_obj.isCalculated or col_obj.expression:
                                severity = "CRITICAL"
                                desc = f"Calculation broken: measure/calculated column in '{node_obj.name}' references this column."
                            else:
                                severity = "HIGH"
                                desc = f"Schema breakage: downstream column '{col_obj.name}' in '{node_obj.name}' loses its data source."
                        elif action == "update":
                            if node_obj.type == "report":
                                severity = "HIGH"
                                desc = f"Report visual alert: formatting or aggregation in '{node_obj.name}' may require adjustment."
                            elif col_obj.isCalculated or col_obj.expression:
                                severity = "HIGH"
                                desc = f"Formula review required: calculation logic in '{node_obj.name}' should be re-validated."
                            else:
                                severity = "MEDIUM"
                                desc = f"Schema evolution: downstream column in '{node_obj.name}' inherits schema changes."
                        else:  # "add"
                            if node_obj.type == "report":
                                severity = "LOW"
                                desc = f"Reporting opportunity: new field can be added as visual/filter in '{node_obj.name}'."
                            else:
                                severity = "LOW"
                                desc = f"Additive extension: new column can be consumed downstream in '{node_obj.name}'."

                        impacted_objects.append(ImpactedObject(
                            nodeId=node_obj.id,
                            nodeName=node_obj.name,
                            nodeType=node_obj.type,
                            container=node_obj.database,
                            system=node_obj.system,
                            columnId=col_obj.id,
                            columnName=col_obj.name,
                            dataType=col_obj.dataType,
                            distance=d,
                            relationship=rel,
                            severity=severity,
                            action=action,
                            impactDescription=desc,
                            affectedExpression=col_obj.expression or edge.expression
                        ))

        # 4. DFS Traversal for downstream full paths
        downstream_paths: List[List[PathNode]] = []
        def dfs_paths(c_id: str, current_path: List[PathNode], visited: Set[str]):
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
            next_edges = downstream_adj.get(c_id, [])
            if not next_edges:
                if len(new_path) > 1:
                    downstream_paths.append(new_path)
            else:
                for e in next_edges:
                    dfs_paths(e.targetColumnId, new_path, visited | {c_id})

        dfs_paths(column_id, [], set())

        # 5. Summary metrics
        impacted_nodes = set(obj.nodeId for obj in impacted_objects)
        reports_count = sum(1 for obj in impacted_objects if obj.nodeType == "report")
        models_count = sum(1 for obj in impacted_objects if obj.nodeType in ("dataset_table", "source_table", "source_view"))
        measures_count = sum(1 for obj in impacted_objects if obj.affectedExpression is not None)

        if action == "delete":
            if reports_count > 0:
                risk_level = "CRITICAL"
                risk_reason = f"Deleting '{target_info.columnName}' directly breaks {reports_count} end-user reports/visuals and {len(impacted_objects)} downstream objects."
            elif len(impacted_objects) > 0:
                risk_level = "HIGH"
                risk_reason = f"Deleting '{target_info.columnName}' causes schema failure in {len(impacted_objects)} downstream tables or measures."
            else:
                risk_level = "LOW"
                risk_reason = f"Column '{target_info.columnName}' has no downstream dependencies. Safe to drop."
        elif action == "update":
            if reports_count > 0 or measures_count > 0:
                risk_level = "HIGH"
                risk_reason = f"Modifying '{target_info.columnName}' propagates to {reports_count} reports and {measures_count} formulas requiring re-verification."
            elif len(impacted_objects) > 0:
                risk_level = "MEDIUM"
                risk_reason = f"Modifying '{target_info.columnName}' impacts {len(impacted_objects)} downstream columns."
            else:
                risk_level = "LOW"
                risk_reason = f"No downstream dependencies impacted by updating '{target_info.columnName}'."
        else:  # "add"
            risk_level = "LOW"
            risk_reason = f"Adding column '{target_info.columnName}' is an additive non-breaking change."

        summary = ImpactAnalysisSummary(
            totalImpactedObjects=len(impacted_objects),
            totalImpactedNodes=len(impacted_nodes),
            impactedReportsCount=reports_count,
            impactedModelsCount=models_count,
            impactedMeasuresCount=measures_count,
            riskLevel=risk_level,
            riskReason=risk_reason
        )

        return ImpactAnalysisResponse(
            target=target_info,
            action=action,
            summary=summary,
            impactedObjects=impacted_objects,
            downstreamPaths=downstream_paths
        )
