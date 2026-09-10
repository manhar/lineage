# Power BI Column-Level Data Lineage (Non-Dockerized / Enterprise Edition)

A high-performance, column-level data lineage application for Power BI metadata scanner output, built for bare-metal / host deployment in **enterprise and banking environments where Docker is not permitted**.

---

## 📋 Software Prerequisites

Before installing, ensure the following software packages are approved and installed on your host server.  
For comprehensive sizing, security compliance, air-gapped guidelines, and firewall rules, see **[PREREQUISITES.md](PREREQUISITES.md)**.

### Mandatory Requirements:
1. **Python 3.10+ or 3.11+** with `pip` and `python3-venv`
2. **Node.js v18.x or v20.x (LTS)** with `npm 9+` or `10+`
3. **Git 2.20+**

Verify requirements on the server:
```bash
python3 --version
node --version
npm --version
```

---

## 🚀 Quick Start (Development & Staging)

### On Linux / macOS:
Use the provided automated startup script:
```bash
./start.sh
```
This script will automatically:
1. Verify Python and Node.js prerequisites.
2. Initialize and activate a Python virtual environment in `backend/.venv`.
3. Install backend packages (`fastapi`, `uvicorn`, `pydantic`).
4. Install frontend dependencies (`@xyflow/react`, `dagre`, `tailwindcss`).
5. Launch the backend API on `http://127.0.0.1:8000` and frontend UI on `http://127.0.0.1:3000`.

### On Windows Server:
Double click or execute the batch script:
```cmd
start.bat
```

---

## 🛠️ Manual Step-by-Step Installation

If your organization requires running installation commands individually or under restricted service accounts:

### Step 1: Set Up Backend Service
```bash
cd backend

# Create and activate virtual environment
python3 -m venv .venv
source .venv/bin/activate    # On Windows: .venv\Scripts\activate

# Upgrade pip & install dependencies
pip install --upgrade pip
pip install -r requirements.txt

# Start backend service
python -m uvicorn app.main:app --host 0.0.0.0 --port 8000
```
- Test API Health: `curl http://localhost:8000/api/health`
- Interactive Swagger UI: [http://localhost:8000/docs](http://localhost:8000/docs)

### Step 2: Set Up Frontend Service
Open a second terminal window:
```bash
cd frontend

# Install packages
npm install

# Start local dev server
npm run dev -- --host 0.0.0.0 --port 3000
```
- Open Browser: [http://localhost:3000](http://localhost:3000)

---

## 🏢 Enterprise Production Deployment (Nginx + systemd)

For long-term institutional hosting behind an enterprise reverse proxy:

### 1. Build Static Frontend Bundle
Compile the frontend into optimized static HTML/JS/CSS assets:
```bash
cd frontend
npm run build
```
This generates the standalone production bundle in `frontend/dist/`.

### 2. Configure Nginx Reverse Proxy
Copy the template configuration from [systemd/nginx-site.conf](systemd/nginx-site.conf) to `/etc/nginx/conf.d/lineage.conf`:
```nginx
server {
    listen 80;
    server_name lineage.internal.bank;

    # Serve static React frontend
    location / {
        root /opt/lineage_ui.service/frontend/dist;
        index index.html;
        try_files $uri $uri/ /index.html;
    }

    # Proxy API calls to backend service
    location /api/ {
        proxy_pass http://127.0.0.1:8000/api/;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
    }
}
```

### 3. Configure systemd Service for Backend
Copy [systemd/lineage-backend.service](systemd/lineage-backend.service) to `/etc/systemd/system/lineage-backend.service`:
```bash
sudo cp systemd/lineage-backend.service /etc/systemd/system/
sudo systemctl daemon-reload
sudo systemctl enable lineage-backend
sudo systemctl start lineage-backend
sudo systemctl status lineage-backend
```

---

## 🔒 Security & Bank Compliance Notes

- **Unprivileged Execution**: Runs completely without root privileges.
- **Local Data Storage**: Metadata JSON is loaded locally from `backend/app/data/scanner_output.json`.
- **Zero Internet Callout**: No external analytics, CDNs, or telemetry calls at runtime.
- **Air-Gapped Ready**: For completely isolated networks, refer to the offline wheel bundle instructions in [PREREQUISITES.md](PREREQUISITES.md#option-b-offline--air-gapped-deployment).
