from typing import List, Optional
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
