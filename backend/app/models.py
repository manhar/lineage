from typing import List, Optional, Dict, Any
from pydantic import BaseModel

class ColumnContributor(BaseModel):
    columnId: str
    columnName: str
    tableName: str
    databaseName: str
    dataType: str
    transformationType: Optional[str] = None
    expression: Optional[str] = None

class ColumnAttribute(BaseModel):
    id: str
    name: str
    dataType: str
    isCalculated: Optional[bool] = False
    isMultiSource: Optional[bool] = False
    contributorCount: Optional[int] = 0
    sourceColumn: Optional[str] = None
    sourceTableId: Optional[str] = None
    sourceColumnId: Optional[str] = None
    transformationType: Optional[str] = None
    expression: Optional[str] = None

class EntityNode(BaseModel):
    id: str
    name: str
    type: str  # source_table, source_view, dataset_table, report
    database: str
    schema_name: str
    system: Optional[str] = None
    columns: List[ColumnAttribute]

class ColumnEdge(BaseModel):
    id: str
    sourceNodeId: str
    sourceColumnId: str
    targetNodeId: str
    targetColumnId: str
    transformationType: Optional[str] = None
    expression: Optional[str] = None
    scannerSource: Optional[str] = None

class TableEdge(BaseModel):
    id: str
    sourceNodeId: str
    targetNodeId: str

class LineageGraphResponse(BaseModel):
    nodes: List[EntityNode]
    columnEdges: List[ColumnEdge]
    tableEdges: List[TableEdge]
    summary: dict

class PathNode(BaseModel):
    nodeId: str
    nodeName: str
    columnId: str
    columnName: str
    dataType: str
    transformationType: Optional[str] = None
    expression: Optional[str] = None

class LineageDetailsResponse(BaseModel):
    selectedNodeId: str
    selectedColumnId: str
    columnName: str
    tableName: str
    databaseName: str
    dataType: str
    expression: Optional[str] = None
    transformationType: Optional[str] = None
    isMultiSource: Optional[bool] = False
    directContributors: List[ColumnContributor] = []
    upstreamPaths: List[List[PathNode]]
    downstreamPaths: List[List[PathNode]]

# =============================================================================
# Ingestion API Schemas
# =============================================================================

class IngestColumnInput(BaseModel):
    id: Optional[str] = None
    name: str
    dataType: str
    isCalculated: Optional[bool] = False
    expression: Optional[str] = None
    transformationType: Optional[str] = None

class IngestNodeInput(BaseModel):
    id: Optional[str] = None  # Optional explicit URN; auto-generated if omitted
    name: str
    container: str            # Database name (Teradata) or Dataset/Workspace name (Fabric)
    schema_name: Optional[str] = "dbo"
    type: Optional[str] = "dataset_table"  # source_table, dataset_table, report
    columns: List[IngestColumnInput]

class IngestEdgeInput(BaseModel):
    sourceColumnId: str       # Full source column URN
    targetColumnId: str       # Full target column URN
    transformationType: Optional[str] = "Direct"  # Direct, SQL_Multi_Derivation, DAX, M_Query
    expression: Optional[str] = None

class TeradataIngestRequest(BaseModel):
    server: Optional[str] = "td_prod"
    defaultDatabase: Optional[str] = "EDW_CORE"
    nodes: List[IngestNodeInput]
    edges: List[IngestEdgeInput]

class FabricIngestRequest(BaseModel):
    workspace: Optional[str] = "Finance & Sales Analytics"
    nodes: List[IngestNodeInput]
    edges: List[IngestEdgeInput]

class IngestResponse(BaseModel):
    status: str
    scannerSource: str
    nodesUpserted: int
    columnsUpserted: int
    edgesUpserted: int
    message: str

# =============================================================================
# Lineage Export API Schemas
# =============================================================================

class LineageExportSummary(BaseModel):
    totalNodes: int
    tables: int
    views: int
    reports: int
    datasetColumns: int
    columnEdges: int
    multiSourceDerivations: int

class LineageExportResponse(BaseModel):
    exportMetadata: Dict[str, Any]
    summary: LineageExportSummary
    nodes: List[EntityNode]
    columnEdges: List[ColumnEdge]

