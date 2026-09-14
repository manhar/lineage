import os
from fastapi import FastAPI, HTTPException, Query
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles

from .models import LineageGraphResponse, LineageDetailsResponse
from .parser import get_lineage_graph_from_db, get_column_details_from_db
from .db import DB_PATH
from .seed_data import seed_lineage_database

# Automatically initialize & seed database if not present
if not os.path.exists(DB_PATH):
    seed_lineage_database(DB_PATH)

app = FastAPI(
    title="Power BI & Teradata Column-Level Data Lineage Service",
    version="2.0.0",
    description="Backend service providing canonical SQLite metadata graph and column lineage API."
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

# Mount pre-compiled frontend static assets (Single-Port Python Deployment)
static_dir = os.path.join(os.path.dirname(__file__), "static")
if os.path.exists(static_dir):
    app.mount("/", StaticFiles(directory=static_dir, html=True), name="static")
