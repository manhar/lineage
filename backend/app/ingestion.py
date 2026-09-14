import re
import hashlib
from typing import Tuple
from .db import get_db, DB_PATH
from .models import TeradataIngestRequest, FabricIngestRequest, IngestResponse

def slugify(text: str) -> str:
    return re.sub(r'[\s/]+', '_', text.strip().lower())

def process_node_urn(raw_id: str, default_prefix: str) -> str:
    if raw_id and (raw_id.startswith("teradata://") or raw_id.startswith("fabric://")):
        return raw_id
    return f"{default_prefix}/{slugify(raw_id)}"

def ingest_teradata_lineage(req: TeradataIngestRequest, db_path: str = DB_PATH) -> IngestResponse:
    server = slugify(req.server or "td_prod")
    nodes_count = 0
    cols_count = 0
    edges_count = 0

    with get_db(db_path) as conn:
        cursor = conn.cursor()

        col_to_node_map = {}

        # 1. Upsert Nodes and Columns
        for n in req.nodes:
            container = n.container or req.defaultDatabase or "edw_core"
            container_slug = slugify(container)
            name_slug = slugify(n.name)

            node_urn = n.id if (n.id and n.id.startswith("teradata://")) else f"teradata://{server}/{container_slug}/{name_slug}"
            system = "Teradata EDW"

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
                col_urn = f"{node_urn}#{c.name.strip().lower()}"
                col_to_node_map[col_urn] = node_urn

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

            node_urn = n.id if (n.id and n.id.startswith("fabric://")) else f"fabric://{ws_slug}/{container_slug}/{name_slug}"
            system = "Fabric Semantic Layer" if n.type != "report" else "Fabric Reporting"

            cursor.execute("""
                INSERT INTO nodes (id, system, container, name, schema_name, type)
                VALUES (?, ?, ?, ?, ?, ?)
                ON CONFLICT(id) DO UPDATE SET
                    system = excluded.system,
                    container = excluded.container,
                    name = excluded.name,
                    schema_name = excluded.schema_name,
                    type = excluded.type;
            """, (node_urn, system, container, n.name, n.schema_name or "Model", n.type or "dataset_table"))
            nodes_count += 1

            for c in n.columns:
                col_urn = f"{node_urn}#{c.name.strip().lower()}"

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

        # 2. Upsert Edges (including bridge edges from Teradata)
        for e in req.edges:
            src_col = e.sourceColumnId.strip()
            tgt_col = e.targetColumnId.strip()

            src_node = src_col.split("#")[0] if "#" in src_col else ""
            tgt_node = tgt_col.split("#")[0] if "#" in tgt_col else ""

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
