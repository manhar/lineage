Build a Dockerized Column-Level Data Lineage Application with a Python FastAPI backend and a React (Vite + Tailwind + React Flow) frontend.

Backend:
1. Load and parse the Power BI metadata scanner JSON output.
2. Construct a directed lineage graph containing table nodes, their columns/types, and column-level edges mapping left-to-right from source systems to Power BI tables/reports.
3. Expose REST endpoints:
   - GET /api/lineage: returns nodes, column handles, and edges for the graph.
   - GET /api/details?nodeId=...&columnId=...: returns upstream/downstream paths and transformation code.

Frontend:
1. Implement an interactive Left-to-Right (LR) canvas using @xyflow/react and Dagre layout.
2. Build custom Table/View nodes that render a header (name, schema, icon) and an attribute list where each column row has its own source/target connection handles.
3. On selecting a column, highlight the active lineage trace and open a right-side inspector panel.
4. The right-side panel must display upstream/downstream endpoint paths and the transformation expression.

Packaging:
- Provide multi-stage Dockerfiles for frontend and backend.
- Provide a docker-compose.yml that brings up both services cleanly.




Phase 1: Data Model & Transformation Engine (Backend)
The agent needs to normalize the raw metadata scanner JSON payload into a unified graph format with column-level mappings.
	1.	Graph Data Schema (lineage_graph.json / DB schema):
•	Nodes (Entities):
•	id: Unique identifier (e.g., db.schema.table or workspace.dataset.table).
•	name: Entity name (e.g., ABSCOSI_Extract).
•	type: source_table, source_view, dataset_table, or report.
•	database / workspace: Parent container metadata.
•	columns: Array of attributes [{ id, name, dataType, expression, isCalculated }].
•	Edges (Movements / Dependencies):
•	Table-level edges: { sourceNodeId, targetNodeId }.
•	Column-level edges: { sourceColumnId, targetColumnId, transformationType, expression }.
	2.	Column-Level Extraction Logic:
•	Map Power BI model column names to source table column names using the extracted M-expressions and table partition metadata.
•	Parse column transformations (renames, DAX calculated columns, and M-query transformations).
	3.	Backend API Endpoints (e.g., FastAPI):
•	GET /api/lineage: Returns nodes and edges filtered by root object or workspace.
•	GET /api/node/{id}: Returns full table metadata and schema.
•	GET /api/column/{nodeId}/{columnId}/lineage: Returns upstream/downstream paths and transformation code for the selected column.
Phase 2: Canvas & UI Architecture (Frontend)
To achieve the exact layout from your screenshot:
	1.	Recommended UI Stack:
•	Framework: React + TypeScript + Vite + Tailwind CSS.
•	Graph Canvas: React Flow (@xyflow/react). It natively supports custom nodes with multiple input/output handles (ports) for each column row.
•	Layout Engine: Dagre.js or ELK.js configured for left-to-right (rankdir: 'LR') hierarchical layout.
	2.	Custom Node Component (TableNode.jsx):
•	Header: Icon, Table/View name, Database/Schema tag, and attribute counter.
•	Search Filter: Input box inside the node to filter column attributes.
•	Attribute List: Scrollable list of columns with:
•	Data type badge (Abc, 123, Date).
•	Column name.
•	React Flow Handles: Invisible or styled connection handles (<Handle ... type="target"/> on the left, <Handle ... type="source"/> on the right) for each individual column row.
	3.	Lineage Highlighting & Interactivity:
•	On Column Click:
•	Highlight connected upstream/downstream edges and related column rows.
•	Dim non-related nodes/columns.
•	Open the right inspector sidebar.
	4.	Right Inspector Panel:
•	Header: Selected column name and container name.
•	Tabs: Upstream vs. Downstream paths.
•	Lineage Tree: Stepper or expandable tree showing:

‭$$\text{Source Column} \xrightarrow{\text{Transformation}} \text{Target Column}$$‬‭‬‭‬
•	Transformation Viewer: Code block showing the underlying M-Query or DAX expression for that specific field.
Phase 3: Dockerization
Create a lightweight, multi-service setup:
•	frontend/Dockerfile: Multi-stage build (Node build ‭$\rightarrow$‬ Nginx serving static assets and reverse-proxying /api/ to backend).
•	backend/Dockerfile: Lightweight Python (FastAPI/Uvicorn) or Node container.
•	docker-compose.yml:
•	backend: Mounts scanner output JSON directory or reads directly from storage.
•	frontend: Exposes the web interface (port 3000 or 80).