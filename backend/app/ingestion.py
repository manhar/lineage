import re
import hashlib
from typing import Tuple
from .db import get_db, DB_PATH
from .models import TeradataIngestRequest, FabricIngestRequest, IngestResponse

def slugify(text: str) -> str:
    """Normalize text into lowercase alphanumeric and underscore segment."""
    if not text:
        return ""
    seg = str(text).strip().lower()
    seg = re.sub(r'[^a-z0-9_]', '_', seg)
    seg = re.sub(r'_+', '_', seg)
    return seg.strip('_')

def infer_node_system(node_urn: str, node_type: str) -> str:
    if node_type == "report" or "/reports/" in node_urn:
        return "Fabric Reporting"
    if "teradata://" in node_urn:
        return "Teradata EDW"
    if "fabric://" in node_urn:
        return "Fabric Semantic Layer"
    return "Upstream Source"

def ensure_node_and_column_exist(cursor, node_urn: str, col_urn: str, fallback_type: str = "dataset_table") -> Tuple[int, int]:
    """
    Auto-synthesizes missing upstream/downstream nodes and columns in SQLite
    so that edges are never orphaned and React Flow always renders every connection.
    """
    nodes_added = 0
    cols_added = 0
    if not node_urn:
        return 0, 0

    cursor.execute("SELECT id FROM nodes WHERE id = ?", (node_urn,))
    if not cursor.fetchone():
        clean_urn = node_urn.replace("://", "/")
        parts = [p for p in clean_urn.split("/") if p]
        scheme = parts[0] if parts else "source"
        node_name = parts[-1] if len(parts) > 1 else "unknown_table"
        container = parts[-2] if len(parts) > 2 else "default"

        if "reports" in parts or fallback_type == "report":
            node_type = "report"
            system = "Fabric Reporting"
            schema_name = "Visual"
        elif "teradata" in scheme:
            node_type = "source_table"
            system = "Teradata EDW"
            schema_name = "dbo"
        elif "fabric" in scheme:
            node_type = "dataset_table"
            system = "Fabric Semantic Layer"
            schema_name = "Model"
        else:
            node_type = "source_table"
            system = "Upstream Source"
            schema_name = "dbo"

        cursor.execute("""
            INSERT INTO nodes (id, system, container, name, schema_name, type)
            VALUES (?, ?, ?, ?, ?, ?)
            ON CONFLICT(id) DO NOTHING;
        """, (node_urn, system, container, node_name, schema_name, node_type))
        nodes_added += 1

    if col_urn:
        cursor.execute("SELECT id FROM columns WHERE id = ?", (col_urn,))
        if not cursor.fetchone():
            col_name = col_urn.split("#")[-1] if "#" in col_urn else "col"
            cursor.execute("""
                INSERT INTO columns (id, node_id, name, data_type, is_calculated, expression, transformation_type)
                VALUES (?, ?, ?, ?, ?, ?, ?)
                ON CONFLICT(id) DO NOTHING;
            """, (col_urn, node_urn, col_name, "String", 0, None, "Direct"))
            cols_added += 1

    return nodes_added, cols_added

def ingest_teradata_lineage(req: TeradataIngestRequest, db_path: str = DB_PATH) -> IngestResponse:
    server = slugify(req.server or "td_prod")
    nodes_count = 0
    cols_count = 0
    edges_count = 0

    with get_db(db_path) as conn:
        cursor = conn.cursor()

        # 1. Upsert Nodes and Columns
        for n in req.nodes:
            container = n.container or req.defaultDatabase or "edw_core"
            container_slug = slugify(container)
            name_slug = slugify(n.name)

            node_urn = n.id if (n.id and "://" in n.id) else f"teradata://{server}/{container_slug}/{name_slug}"
            system = infer_node_system(node_urn, n.type or "dataset_table")

            cursor.execute("""
                INSERT INTO nodes (id, system, container, name, schema_name, type)
                VALUES (?, ?, ?, ?, ?, ?)
                ON CONFLICT(id) DO UPDATE SET
                    system = excluded.system,
                    container = excluded.container,
                    name = excluded.name,
                    schema_name = excluded.schema_name,
                    type = excluded.type;
            """, (node_urn, system, container, n.name, n.schema_name or "dbo", n.type or "dataset_table"))
            nodes_count += 1

            for c in n.columns:
                col_urn = c.id if (getattr(c, "id", None) and "#" in c.id) else f"{node_urn}#{slugify(c.name)}"

                cursor.execute("""
                    INSERT INTO columns (id, node_id, name, data_type, is_calculated, expression, transformation_type)
                    VALUES (?, ?, ?, ?, ?, ?, ?)
                    ON CONFLICT(id) DO UPDATE SET
                        node_id = excluded.node_id,
                        name = excluded.name,
                        data_type = excluded.data_type,
                        is_calculated = excluded.is_calculated,
                        expression = excluded.expression,
                        transformation_type = excluded.transformation_type;
                """, (col_urn, node_urn, c.name, c.dataType, 1 if c.isCalculated else 0, c.expression, c.transformationType or "Direct"))
                cols_count += 1

        # 2. Upsert Edges
        for e in req.edges:
            src_col = e.sourceColumnId.strip()
            tgt_col = e.targetColumnId.strip()

            src_node = src_col.split("#")[0] if "#" in src_col else ""
            tgt_node = tgt_col.split("#")[0] if "#" in tgt_col else ""

            s_n_add, s_c_add = ensure_node_and_column_exist(cursor, src_node, src_col, fallback_type="source_table")
            t_n_add, t_c_add = ensure_node_and_column_exist(cursor, tgt_node, tgt_col, fallback_type="dataset_table")
            nodes_count += (s_n_add + t_n_add)
            cols_count += (s_c_add + t_c_add)

            edge_hash = hashlib.md5(f"{src_col}->{tgt_col}".encode('utf-8')).hexdigest()[:12]
            edge_id = f"td-edge-{edge_hash}"

            cursor.execute("""
                INSERT INTO column_edges (id, source_node_id, source_column_id, target_node_id, target_column_id, transformation_type, expression, scanner_source)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?)
                ON CONFLICT(id) DO UPDATE SET
                    transformation_type = excluded.transformation_type,
                    expression = excluded.expression,
                    scanner_source = excluded.scanner_source;
            """, (edge_id, src_node, src_col, tgt_node, tgt_col, e.transformationType or "Direct", e.expression, "teradata_sql_scanner"))
            edges_count += 1

        conn.commit()

    return IngestResponse(
        status="success",
        scannerSource="teradata_sql_scanner",
        nodesUpserted=nodes_count,
        columnsUpserted=cols_count,
        edgesUpserted=edges_count,
        message=f"Successfully ingested Teradata lineage: {nodes_count} nodes, {cols_count} columns, {edges_count} column edges."
    )

def ingest_fabric_lineage(req: FabricIngestRequest, db_path: str = DB_PATH) -> IngestResponse:
    ws_slug = slugify(req.workspace or "workspace")
    nodes_count = 0
    cols_count = 0
    edges_count = 0

    with get_db(db_path) as conn:
        cursor = conn.cursor()

        # 1. Upsert Nodes and Columns
        for n in req.nodes:
            container = n.container or req.workspace or "semantic_model"
            container_slug = slugify(container)
            name_slug = slugify(n.name)

            if n.id and "://" in n.id:
                node_urn = n.id
            elif n.type == "report":
                node_urn = f"fabric://{ws_slug}/reports/{name_slug}"
            else:
                node_urn = f"fabric://{ws_slug}/{container_slug}/{name_slug}"

            system = infer_node_system(node_urn, n.type or "dataset_table")

            cursor.execute("""
                INSERT INTO nodes (id, system, container, name, schema_name, type)
                VALUES (?, ?, ?, ?, ?, ?)
                ON CONFLICT(id) DO UPDATE SET
                    system = excluded.system,
                    container = excluded.container,
                    name = excluded.name,
                    schema_name = excluded.schema_name,
                    type = excluded.type;
            """, (node_urn, system, container, n.name, n.schema_name or ("Visual" if n.type == "report" else "Model"), n.type or "dataset_table"))
            nodes_count += 1

            for c in n.columns:
                col_urn = c.id if (getattr(c, "id", None) and "#" in c.id) else f"{node_urn}#{slugify(c.name)}"

                cursor.execute("""
                    INSERT INTO columns (id, node_id, name, data_type, is_calculated, expression, transformation_type)
                    VALUES (?, ?, ?, ?, ?, ?, ?)
                    ON CONFLICT(id) DO UPDATE SET
                        node_id = excluded.node_id,
                        name = excluded.name,
                        data_type = excluded.data_type,
                        is_calculated = excluded.is_calculated,
                        expression = excluded.expression,
                        transformation_type = excluded.transformation_type;
                """, (col_urn, node_urn, c.name, c.dataType, 1 if c.isCalculated else 0, c.expression, c.transformationType or "Direct"))
                cols_count += 1

        # 2. Upsert Edges (including bridge edges from Teradata/Sources)
        for e in req.edges:
            src_col = e.sourceColumnId.strip()
            tgt_col = e.targetColumnId.strip()

            src_node = src_col.split("#")[0] if "#" in src_col else ""
            tgt_node = tgt_col.split("#")[0] if "#" in tgt_col else ""

            # Ensure source and target nodes & columns exist in SQLite to avoid orphaned edges
            s_n_add, s_c_add = ensure_node_and_column_exist(cursor, src_node, src_col, fallback_type="source_table")
            t_n_add, t_c_add = ensure_node_and_column_exist(cursor, tgt_node, tgt_col, fallback_type="dataset_table")
            nodes_count += (s_n_add + t_n_add)
            cols_count += (s_c_add + t_c_add)

            edge_hash = hashlib.md5(f"{src_col}->{tgt_col}".encode('utf-8')).hexdigest()[:12]
            edge_id = f"fabric-edge-{edge_hash}"

            cursor.execute("""
                INSERT INTO column_edges (id, source_node_id, source_column_id, target_node_id, target_column_id, transformation_type, expression, scanner_source)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?)
                ON CONFLICT(id) DO UPDATE SET
                    transformation_type = excluded.transformation_type,
                    expression = excluded.expression,
                    scanner_source = excluded.scanner_source;
            """, (edge_id, src_node, src_col, tgt_node, tgt_col, e.transformationType or "Direct", e.expression, "fabric_scanner"))
            edges_count += 1

        conn.commit()

    return IngestResponse(
        status="success",
        scannerSource="fabric_scanner",
        nodesUpserted=nodes_count,
        columnsUpserted=cols_count,
        edgesUpserted=edges_count,
        message=f"Successfully ingested Fabric lineage: {nodes_count} nodes, {cols_count} columns, {edges_count} column edges."
    )
