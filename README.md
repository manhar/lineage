# Power BI & Teradata Column-Level Data Lineage (100% Python Edition)

A high-performance, column-level data lineage application bridging **Teradata SQL** and **Azure Fabric / Power BI**, built for **enterprise and banking environments where Python is the ONLY permitted runtime** (No Docker, No Node.js required on the server).

---

## 📋 Software Prerequisites

The server requires **only Python**. All dependencies are standard Python wheels.  
For network ports, security compliance, proxy setup, and air-gapped instructions, see **[PREREQUISITES.md](PREREQUISITES.md)**.

### Mandatory Requirements:
- **Python 3.10+ or 3.11+**
- **pip** (Python package installer)
- **python3-venv**

Verify on the server:
```bash
python3 --version
```

---

## 🚀 Quick Start

### 1. Run with Automated Script

**On Linux / macOS:**
```bash
./start.sh
```

**On Windows Server:**
```cmd
start.bat
```

### 2. Manual Commands (Standard Python Workflow)
```bash
# 1. Create and activate a virtual environment
python3 -m venv .venv
source .venv/bin/activate    # On Windows: .venv\Scripts\activate

# 2. Install Python dependencies
pip install -r backend/requirements.txt

# 3. Launch Unified Service (Web UI + REST API)
python run.py
```

---

## 🌐 Accessing the Application

Once launched, both the frontend UI and backend API run on a single unified port:
- **Interactive Lineage Canvas UI**: [http://localhost:8000](http://localhost:8000)
- **Interactive Swagger Documentation**: [http://localhost:8000/docs](http://localhost:8000/docs)
- **Health Check**: [http://localhost:8000/api/health](http://localhost:8000/api/health)

---

## 📥 Ingestion Endpoints (Teradata & Fabric)

The backend provides automated ingestion APIs for your scanner pipelines:
- **`POST /api/ingest/teradata`**: Ingests DDL, BTEQ scripts, views, and ELT multi-column derivations from Teradata SQL scanners.
- **`POST /api/ingest/fabric`**: Ingests Power BI semantic models, DAX measures, visual bindings, and bridge edges connecting back to Teradata.
- **`POST /api/reset`**: Resets the SQLite database to the verified sample dataset.

For payload schemas, cURL examples, and Python scripts, refer to the full **[INGESTION_API.md](INGESTION_API.md)** documentation.

---

## 🛠️ Architecture: How It Works Without Node.js

```
┌─────────────────────────────────────────────────────────────┐
│                    Bank Server (Python Only)                │
│                                                             │
│   ┌─────────────────────────────────────────────────────┐   │
│   │               FastAPI / Uvicorn Service             │   │
│   │                   (Port 8000)                       │   │
│   │                                                     │   │
│   │  • /api/lineage  ──> [ Parser & SQLite Engine ]     │   │
│   │  • /api/details  ──> [ Path & Formula Engine ]      │   │
│   │  • /api/ingest   ──> [ Multi-Scanner Ingestion ]    │   │
│   │  • /             ──> [ Pre-Compiled Static UI ]     │   │
│   │                      (React Flow + Dagre Canvas)    │   │
│   └─────────────────────────────────────────────────────┘   │
└─────────────────────────────────────────────────────────────┘
```

The frontend React application was pre-compiled into static HTML, CSS, and JS (`backend/app/static/`).  
FastAPI directly mounts and serves these files on port 8000 alongside its REST endpoints, eliminating any need for Node.js, npm, or Docker on the target bank server.
