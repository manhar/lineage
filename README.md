# Power BI Column-Level Data Lineage (Dockerized Edition)

A full-stack, Dockerized column-level data lineage application for Power BI metadata scanner output.

## Architecture

- **Backend**: Python 3.11 + FastAPI + Uvicorn (Port `8000`)
- **Frontend**: React + Vite + Tailwind CSS + `@xyflow/react` + Dagre layout (Port `3000`)
- **Orchestration**: Docker Compose with Nginx reverse proxy

## Features

- **End-to-End Tracing**: Left-to-Right lineage flow from Source Systems $\rightarrow$ Dataset Models $\rightarrow$ Report Visuals.
- **Column-Level Handles**: Connects specific source and target column attributes with active glow highlighting.
- **Formula Inspector**: Real-time sliding drawer revealing M-Query transformations and DAX calculated column formulas.
- **Upstream / Downstream Trees**: Step-by-step dependency explorer for each selected column.

## Quick Start with Docker

### Prerequisites
- Docker (version 20.10+)
- Docker Compose (v2 or `docker-compose`)

### 1. Build and Run Containers
```bash
docker-compose up --build -d
```

### 2. Access the Application
- **Web UI**: [http://localhost:3000](http://localhost:3000)
- **Backend API & Swagger Docs**: [http://localhost:8000/docs](http://localhost:8000/docs)
- **Health Check**: `curl http://localhost:8000/api/health`

### 3. Stop Containers
```bash
docker-compose down
```
