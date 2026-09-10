# Enterprise & Banking Deployment - Software Prerequisites & Security Guide

This document outlines the mandatory and optional software prerequisites, system specifications, firewall port allowances, and security compliance guidelines for deploying the **Power BI Column-Level Data Lineage** application in locked-down enterprise and banking environments where **Docker is prohibited**.

---

## 1. Required Software Checklist

Below is the list of software packages that must be approved and provisioned by the Bank IT Infrastructure / Security team:

| Component | Software | Supported Versions | Purpose | Verification Command |
| :--- | :--- | :--- | :--- | :--- |
| **Backend Runtime** | **Python** | `3.10.x` or `3.11.x` | Runs the FastAPI lineage parser & API service | `python3 --version` |
| **Package Installer** | **pip** | `22.0+` | Installs Python dependencies (`uvicorn`, `fastapi`, `pydantic`) | `python3 -m pip --version` |
| **Virtual Environments** | **python3-venv** | Included with Python | Isolates Python libraries from system packages | `python3 -m venv --help` |
| **Frontend Runtime** | **Node.js** | `v18.x` or `v20.x` (LTS) | Compiles React / Vite frontend and serves static assets | `node --version` |
| **Package Manager** | **npm** | `9.x+` or `10.x+` | Installs frontend dependencies (`@xyflow/react`, `dagre`, `tailwindcss`) | `npm --version` |
| **Version Control** | **Git** | `2.20+` | Source code retrieval & branch management | `git --version` |

---

## 2. Optional Production Infrastructure (Recommended for Banking)

If hosting behind an existing enterprise reverse proxy or web gateway:

| Software | Supported Versions | Role in Architecture |
| :--- | :--- | :--- |
| **Nginx** | `1.20+` (or RHEL default) | Serves pre-built static React files and reverse-proxies `/api/` to backend on port 8000 |
| **Apache HTTP Server** | `2.4+` | Alternative to Nginx using `mod_proxy` |
| **Microsoft IIS** | `10.0+` | Alternative on Windows Server using URL Rewrite & ARR |
| **systemd** | Standard Linux | Process supervisor to auto-restart backend on reboot or failure |

---

## 3. Supported Operating Systems & Sizing

### Operating Systems
- **Red Hat Enterprise Linux (RHEL)** 8.x / 9.x
- **Rocky Linux / AlmaLinux** 8.x / 9.x
- **Ubuntu Server** 20.04 LTS / 22.04 LTS / 24.04 LTS
- **SUSE Linux Enterprise Server (SLES)** 15+
- **Windows Server** 2019 / 2022

### Hardware Sizing
- **CPU**: 2 cores minimum (4 cores recommended for large metadata sets)
- **RAM**: 2 GB minimum (4 GB recommended)
- **Disk**: 2 GB free disk space (includes node_modules, Python venv, and metadata JSON files)

---

## 4. Network Ports & Firewall Configuration

| Port | Direction | Source | Destination | Description |
| :--- | :--- | :--- | :--- | :--- |
| **3000** | Inbound | Authorized Internal Users / Intranet | Server IP | Default Frontend Web UI port (if using dev server) |
| **80 / 443** | Inbound | Bank Users / Browser clients | Reverse Proxy IP | Recommended production web ports (HTTP/HTTPS with Bank SSL cert) |
| **8000** | Internal Loopback | `127.0.0.1` | `127.0.0.1:8000` | FastAPI Backend API (can be restricted to localhost) |

> [!NOTE]
> In production with Nginx or IIS, **Port 8000 does NOT need to be exposed to end users**. Only Port 80/443 is exposed; the web server proxies `/api/*` to `127.0.0.1:8000` internally.

---

## 5. Corporate Proxy, Artifactory & Air-Gapped Environments

In banking environments where outbound internet access to public PyPI (`pypi.org`) and npm (`registry.npmjs.org`) is blocked:

### Option A: Internal Repository Mirrors (Artifactory / Nexus / JFrog)
Configure pip and npm to use your organization's internal mirror:

```bash
# Point pip to internal enterprise PyPI mirror
pip config set global.index-url https://artifactory.bank.internal/artifactory/api/pypi/pypi-remote/simple
pip config set global.trusted-host artifactory.bank.internal

# Point npm to internal enterprise npm registry
npm config set registry https://artifactory.bank.internal/artifactory/api/npm/npm-virtual/
```

### Option B: Offline / Air-Gapped Deployment
If the target server has zero internet access:

1. **On a connected machine with same OS architecture**, download wheels and npm dependencies:
   ```bash
   # Download all Python wheels
   pip wheel -r backend/requirements.txt -w ./wheelhouse
   
   # Build the frontend into static bundle
   cd frontend && npm install && npm run build
   ```
2. **Transfer files** (`wheelhouse/`, `frontend/dist/`, `backend/`) via approved secure bank media / secure copy (SCP).
3. **Install on target air-gapped machine without network**:
   ```bash
   python3 -m venv backend/.venv
   source backend/.venv/bin/activate
   pip install --no-index --find-links=./wheelhouse -r backend/requirements.txt
   ```

---

## 6. Banking Security & Compliance Checklist

- [x] **No Root Required**: The application runs completely under an unprivileged service account (e.g. `lineage_user`).
- [x] **Zero External Telemetry**: No tracking, metrics, or outbound CDN calls. All fonts, CSS, and libraries are locally bundled.
- [x] **On-Premises Data Privacy**: Scanner metadata JSON is parsed and stored purely on internal server storage.
- [x] **Standard Protocol Compliance**: Clean REST API, standard HTTP status codes, and configurable CORS allowlist.
