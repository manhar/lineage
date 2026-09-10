from fastapi import FastAPI, HTTPException, Query
from fastapi.middleware.cors import CORSMiddleware
from .models import LineageGraphResponse, LineageDetailsResponse
from .parser import load_scanner_json, parse_lineage_graph, get_column_details

app = FastAPI(
    title="Power BI Column-Level Data Lineage Service",
    version="1.0.0",
    description="Backend service providing metadata graph parsing and column lineage API."
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
    return {"status": "ok", "service": "lineage_ui_backend"}

@app.get("/api/lineage", response_model=LineageGraphResponse)
def get_lineage_graph():
    try:
        raw_data = load_scanner_json()
        graph = parse_lineage_graph(raw_data)
        return graph
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/api/details", response_model=LineageDetailsResponse)
def get_lineage_details(
    nodeId: str = Query(..., description="ID of the table/view node"),
    columnId: str = Query(..., description="ID of the selected column")
):
    try:
        raw_data = load_scanner_json()
        graph = parse_lineage_graph(raw_data)
        details = get_column_details(nodeId, columnId, graph)
        return details
    except ValueError as ve:
        raise HTTPException(status_code=404, detail=str(ve))
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
