# Enterprise & Banking Deployment - Software Prerequisites & Security Guide
## 100% Python-Only Deployment Edition

This document details the software prerequisites, network ports, and security compliance checklist for deploying the **Power BI Column-Level Data Lineage** application in banking environments where **Python is the only permitted runtime** (No Docker, No Node.js required on the server).

---

## 1. Required Software Checklist (Server-Side)

The host server requires **only Python**. All application dependencies are standard Python packages installed via `pip`:

| Software Component | Required Version | Banking Purpose | Verification Command |
| :--- | :--- | :--- | :--- |
| **Python** | `3.10.x` or `3.11.x` | Core execution runtime | `python3 --version` |
| **pip** | `22.0+` | Package manager for Python wheels | `python3 -m pip --version` |
| **python3-venv** | Standard with Python | Isolated virtual environment | `python3 -m venv --help` |

> [!IMPORTANT]
> **No Node.js, No npm, and No Docker are required on the bank server.**  
> The React Flow UI has been pre-compiled into static production assets (`backend/app/static/`) and is served directly by the Python FastAPI server on a single port (`8000`).

---

## 2. Python Package List (`backend/requirements.txt`)

All software dependencies are standard open-source Python packages approved in financial institutions:

| Package | Purpose | License |
| :--- | :--- | :--- |
| `fastapi` | High-performance asynchronous REST API & static file serving | MIT |
| `uvicorn` | Lightweight ASGI production web server | BSD-3-Clause |
| `pydantic` | Data validation and JSON parsing engine | MIT |

---

## 3. Network Ports & Firewall Rules

| Port | Protocol | Binding | Allowed Source | Description |
| :--- | :--- | :--- | :--- | :--- |
| **8000** | TCP / HTTP | `0.0.0.0` or `127.0.0.1` | Internal Bank Users / Intranet | Unified Web UI, REST APIs, and Swagger Documentation |

*(Optional)* If the bank uses an enterprise reverse proxy (Nginx, Apache, or F5 Big-IP) with an institutional SSL certificate, configure it to forward external HTTPS requests to `http://127.0.0.1:8000`.

---

## 4. Corporate Proxy, Artifactory & Air-Gapped Environments

### Option A: Internal Enterprise PyPI Mirror (Artifactory / Nexus / JFrog)
If outbound internet access is restricted, point `pip` to your bank's internal mirror:

```bash
pip config set global.index-url https://artifactory.bank.internal/artifactory/api/pypi/pypi-remote/simple
pip config set global.trusted-host artifactory.bank.internal
```

### Option B: Offline / Air-Gapped Installation
If the bank server is completely disconnected from the network:

1. **Pre-download wheels on a connected machine**:
   ```bash
   pip wheel -r backend/requirements.txt -w ./wheelhouse
   ```
2. **Transfer** the `wheelhouse/` folder and project files to the target server.
3. **Install completely offline**:
   ```bash
   python3 -m venv .venv
   source .venv/bin/activate
   pip install --no-index --find-links=./wheelhouse -r backend/requirements.txt
   ```

---

## 5. Bank Security & Compliance Checklist

- [x] **100% Python Runtime**: No external runtime (Node.js, Java, Docker) required.
- [x] **Single-Port Architecture**: Web UI, static assets, and REST endpoints are all hosted on port 8000.
- [x] **Unprivileged Service Account**: Can be run under any restricted Linux/Windows user (no `root` or `admin` needed).
- [x] **Zero External Telemetry**: No third-party API calls, CDNs, or internet requests occur at runtime.
- [x] **Data Privacy**: Power BI scanner metadata remains strictly local on internal server storage.
