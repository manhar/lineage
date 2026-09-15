import os
import json
from datetime import datetime, timezone
from typing import Optional
from fastapi import FastAPI, HTTPException, Query, Response, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles

from .models import (
    LineageGraphResponse, LineageDetailsResponse,
    TeradataIngestRequest, FabricIngestRequest, IngestResponse,
    LineageExportResponse, ImpactAnalysisResponse
)
from .parser import get_lineage_graph_from_db, get_column_details_from_db, export_lineage_from_db
from .ingestion import ingest_teradata_lineage, ingest_fabric_lineage
from .impact import calculate_column_impact
from .db import DB_PATH, clear_db, prune_orphaned_edges
from .seed_data import seed_lineage_database

# Automatically initialize & seed database if not present
if not os.path.exists(DB_PATH):
    seed_lineage_database(DB_PATH)

app = FastAPI(
    title="Power BI & Teradata Column-Level Data Lineage Service",
    version="2.1.0",
    description="Backend service providing canonical SQLite metadata graph, multi-scanner ingestion API, and column lineage."
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

@app.get("/api/health")
def health_check():
    return {
        "status": "ok", 
        "service": "lineage_ui_backend",
        "database": "sqlite",
        "engine": "canonical_urn_graph"
    }

@app.get("/api/lineage", response_model=LineageGraphResponse)
def get_lineage_graph():
    try:
        return get_lineage_graph_from_db()
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/api/details", response_model=LineageDetailsResponse)
def get_lineage_details(
    nodeId: str = Query(..., description="ID of the table/view node"),
    columnId: str = Query(..., description="ID of the selected column")
):
    try:
        return get_column_details_from_db(nodeId, columnId)
    except ValueError as ve:
        raise HTTPException(status_code=404, detail=str(ve))
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/api/export", response_model=LineageExportResponse)
def export_lineage(
    nodeId: Optional[str] = Query(None, description="Filter or root node ID for subgraph export"),
    columnId: Optional[str] = Query(None, description="Filter or root column ID for subgraph export"),
    type: Optional[str] = Query(None, description="Filter by entity type (source_table, source_view, dataset_table, report)"),
    system: Optional[str] = Query(None, description="Filter by system (e.g. 'Teradata EDW', 'Fabric Semantic Layer')"),
    scanner: Optional[str] = Query(None, description="Filter edges by scanner source (teradata_sql_scanner, fabric_scanner)"),
    scope: str = Query("all", description="Export scope: 'all' (default) or 'subgraph' (traces connected paths)"),
    download: bool = Query(False, description="Whether to trigger a browser file download")
):
    """
    Extract a JSON snapshot of the entire lineage graph or a filtered subset.
    Supports attribute-based filtering or upstream/downstream subgraph reachability extraction.
    """
    try:
        export_data = export_lineage_from_db(
            node_id=nodeId,
            column_id=columnId,
            entity_type=type,
            system=system,
            scanner_source=scanner,
            scope=scope
        )

        if download:
            now_str = datetime.now(timezone.utc).strftime("%Y%m%d_%H%M%S")
            filename = f"lineage_extract_{now_str}.json"
            if hasattr(export_data, "model_dump_json"):
                json_str = export_data.model_dump_json(indent=2)
            elif hasattr(export_data, "json"):
                json_str = export_data.json(indent=2)
            else:
                json_str = json.dumps(export_data.dict(), indent=2)

            return Response(
                content=json_str.encode("utf-8"),
                media_type="application/json",
                headers={
                    "Content-Disposition": f'attachment; filename="{filename}"'
                }
            )

        return export_data

    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to export lineage: {str(e)}")

# =============================================================================
# Column Impact Analysis Endpoints
# =============================================================================

@app.get("/api/impact-analysis", response_model=ImpactAnalysisResponse)
def get_impact_analysis(
    columnId: str = Query(..., description="Target Column URN to analyze"),
    action: str = Query("delete", description="Simulated action: delete, update, add")
):
    """
    Simulates the blast-radius impact of modifying (delete, update, add) a column
    across all downstream models, measures, calculations, and report visuals.
    """
    try:
        return calculate_column_impact(columnId, action=action)
    except ValueError as ve:
        raise HTTPException(status_code=404, detail=str(ve))
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/api/impact-analysis/csv")
def export_impact_analysis_csv(
    columnId: str = Query(..., description="Target Column URN to analyze"),
    action: str = Query("delete", description="Simulated action: delete, update, add")
):
    """
    Downloads an enterprise-ready CSV impact report for change management & audit.
    """
    try:
        import io, csv
        result = calculate_column_impact(columnId, action=action)
        output = io.StringIO()
        writer = csv.writer(output)
        writer.writerow(["=== LINEAGE COLUMN IMPACT ANALYSIS REPORT ==="])
        writer.writerow(["Target Column", result.target.columnName])
        writer.writerow(["Target Table/View", result.target.nodeName])
        writer.writerow(["Target Container", result.target.container])
        writer.writerow(["Simulated Action", result.action.upper()])
        writer.writerow(["Overall Risk Level", result.summary.riskLevel])
        writer.writerow(["Risk Reason", result.summary.riskReason])
        writer.writerow(["Total Impacted Objects", result.summary.totalImpactedObjects])
        writer.writerow(["Impacted Reports", result.summary.impactedReportsCount])
        writer.writerow(["Impacted Models", result.summary.impactedModelsCount])
        writer.writerow(["Impacted Measures/Formulas", result.summary.impactedMeasuresCount])
        writer.writerow([])
        writer.writerow(["Impacted Object Name", "Container", "Type", "Column/Measure", "Distance", "Relationship", "Severity", "Impact Description", "Affected Expression"])
        for obj in result.impactedObjects:
            writer.writerow([
                obj.nodeName,
                obj.container,
                obj.nodeType,
                obj.columnName,
                obj.distance,
                obj.relationship,
                obj.severity,
                obj.impactDescription,
                obj.affectedExpression or ""
            ])
        now_str = datetime.now(timezone.utc).strftime("%Y%m%d_%H%M%S")
        filename = f"impact_analysis_{result.target.columnName}_{action}_{now_str}.csv"
        return Response(
            content=output.getvalue().encode("utf-8"),
            media_type="text/csv",
            headers={"Content-Disposition": f'attachment; filename="{filename}"'}
        )
    except ValueError as ve:
        raise HTTPException(status_code=404, detail=str(ve))
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

# =============================================================================
# Ingestion Endpoints (Teradata SQL Scanner & Azure Fabric / Power BI Scanner)
# =============================================================================

@app.post("/api/ingest/teradata", response_model=IngestResponse)
def ingest_teradata(payload: TeradataIngestRequest):
    """
    Ingest lineage generated by the Teradata SQL file scanner (DDL, BTEQ, Views, Insert-Select).
    Upserts tables, columns, and column-level edges.
    """
    try:
        return ingest_teradata_lineage(payload)
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Teradata ingestion failed: {str(e)}")

@app.post("/api/ingest/fabric", response_model=IngestResponse)
def ingest_fabric(payload: FabricIngestRequest):
    """
    Ingest lineage generated by the Azure Fabric / Power BI Metadata Scanner API.
    Upserts dataset tables, measures, report visuals, and bridge edges connecting to Teradata.
    """
    try:
        return ingest_fabric_lineage(payload)
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Fabric ingestion failed: {str(e)}")

@app.post("/api/reset")
async def reset_database(request: Request, seed_sample: Optional[bool] = Query(None)):
    """
    Clear all lineage data from the SQLite database (nodes, columns, edges).
    Pass ?seed_sample=true or {"seed_sample": true} to repopulate with default sample lineage.
    """
    should_seed = False
    if seed_sample is not None:
        should_seed = seed_sample
    else:
        # Check if JSON body contains seed_sample
        try:
            body = await request.json()
            if isinstance(body, dict) and "seed_sample" in body:
                should_seed = bool(body["seed_sample"])
        except Exception:
            pass

    try:
        if should_seed:
            seed_lineage_database(DB_PATH)
            return {
                "status": "ok",
                "message": "Lineage database successfully reset and re-seeded with sample data."
            }
        else:
            clear_db(DB_PATH)
            return {
                "status": "ok",
                "message": "Lineage database successfully cleared (0 nodes, 0 edges)."
            }
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

# Mount pre-compiled frontend static assets (Single-Port Python Deployment)
static_dir = os.path.join(os.path.dirname(__file__), "static")
if os.path.exists(static_dir):
    app.mount("/", StaticFiles(directory=static_dir, html=True), name="static")
