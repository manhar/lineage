#!/usr/bin/env python3
"""
===============================================================================
 Power BI & Teradata Lineage Ingestion & Validation CLI
 100% Python Standard Library - Bank & Enterprise Compliant
===============================================================================
Usage:
    python3 scripts/load_lineage.py sample_data/teradata_sample.json
    python3 scripts/load_lineage.py sample_data/fabric_sample.json --validate-only
    python3 scripts/load_lineage.py sample_data/fabric_sample.json --api-url http://localhost:8000
"""

import sys
import os
import json
import argparse
import urllib.request
import urllib.error
from pathlib import Path
from typing import Dict, List, Any, Tuple, Optional

# Valid entity types
VALID_ENTITY_TYPES = {"source_table", "source_view", "dataset_table", "report"}

class ValidationError:
    def __init__(self, severity: str, message: str, context: Optional[str] = None):
        self.severity = severity  # "ERROR" or "WARNING"
        self.message = message
        self.context = context

    def __str__(self):
        ctx = f" [{self.context}]" if self.context else ""
        return f"{self.severity}: {self.message}{ctx}"


def format_report_box(
    title: str,
    stats: Dict[str, Any],
    api_url: Optional[str] = None,
    scanner_type: Optional[str] = None,
    status_msg: Optional[str] = None,
    is_success: bool = True
) -> str:
    """Generates an enterprise terminal ASCII report."""
    border = "=" * 70
    sub_border = "-" * 70

    lines = [
        border,
        f" {title.center(68)} ",
        border,
    ]

    if api_url:
        lines.append(f"  Target Service:   {api_url}")
    if scanner_type:
        lines.append(f"  Scanner Type:     {scanner_type}")

    lines.append(sub_border)
    lines.append("  OBJECT INVENTORY SUMMARY:")
    lines.append(f"    📦 Tables:              {stats.get('tables', 0):>6}")
    lines.append(f"    👁️  Views:               {stats.get('views', 0):>6}")
    lines.append(f"    📊 Reports:             {stats.get('reports', 0):>6}")
    lines.append(f"    📑 Columns / Measures:  {stats.get('datasetColumns', 0):>6}")
    lines.append(f"    🔗 Column Edges:        {stats.get('columnEdges', 0):>6}")
    if stats.get('multiDerivations', 0) > 0:
        lines.append(f"    🔀 Multi-Source Derivs: {stats.get('multiDerivations', 0):>6}")

    lines.append(sub_border)
    if status_msg:
        prefix = "✅ SUCCESS: " if is_success else "❌ FAILED:  "
        lines.append(f"  {prefix}{status_msg}")
    lines.append(border)

    return "\n".join(lines)


class LineageValidator:
    """Validates lineage JSON files against schema rules and integrity checks."""

    def __init__(self, raw_data: Any, file_path: str):
        self.data = raw_data
        self.file_path = file_path
        self.errors: List[ValidationError] = []
        self.warnings: List[ValidationError] = []
        self.normalized_payload: Dict[str, Any] = {}
        self.detected_scanner: str = "auto"
        self.stats: Dict[str, int] = {
            "tables": 0,
            "views": 0,
            "reports": 0,
            "datasetColumns": 0,
            "columnEdges": 0,
            "multiDerivations": 0
        }

    def validate_and_normalize(self, forced_type: str = "auto") -> bool:
        if not isinstance(self.data, dict):
            self.errors.append(ValidationError("ERROR", "Top-level JSON structure must be an object/dict."))
            return False

        # Format A: Exported JSON extract format
        if "exportMetadata" in self.data and "nodes" in self.data:
            return self._normalize_from_export(forced_type)

        # Format B: Legacy Fabric scanner format (workspaces -> datasets -> tables)
        if "workspaces" in self.data:
            return self._normalize_from_fabric_scanner(forced_type)

        # Format C: Canonical Ingestion format (nodes, edges)
        if "nodes" in self.data:
            return self._normalize_from_canonical(forced_type)

        self.errors.append(ValidationError(
            "ERROR",
            "Unrecognized JSON lineage schema. Expected 'nodes' array or 'workspaces' array or 'exportMetadata'."
        ))
        return False

    def _normalize_from_canonical(self, forced_type: str) -> bool:
        nodes = self.data.get("nodes")
        edges = self.data.get("edges", self.data.get("columnEdges", []))

        if not isinstance(nodes, list):
            self.errors.append(ValidationError("ERROR", "'nodes' field must be a list of entity objects."))
            return False
        if not isinstance(edges, list):
            self.errors.append(ValidationError("ERROR", "'edges' field must be a list of edge objects."))
            return False

        # Auto-detect scanner type if auto
        explicit_scanner = (self.data.get("scanner") or self.data.get("scannerSource") or "").lower()
        if "teradata" in explicit_scanner:
            self.detected_scanner = "teradata"
        elif "fabric" in explicit_scanner or "powerbi" in explicit_scanner:
            self.detected_scanner = "fabric"
        else:
            # Inspect node IDs / containers
            has_teradata = any("teradata" in str(n.get("id", "")) or "td_" in str(n.get("container", "")).lower() for n in nodes)
            has_fabric = any("fabric" in str(n.get("id", "")) or n.get("type") == "report" for n in nodes)
            if has_teradata and not has_fabric:
                self.detected_scanner = "teradata"
            elif has_fabric and not has_teradata:
                self.detected_scanner = "fabric"
            else:
                self.detected_scanner = "teradata" if "teradata" in forced_type else ("fabric" if "fabric" in forced_type else "teradata")

        if forced_type in ("teradata", "fabric"):
            self.detected_scanner = forced_type

        # Validate nodes and columns
        declared_col_urns = set()
        for idx, n in enumerate(nodes):
            n_name = n.get("name")
            if not n_name or not isinstance(n_name, str):
                self.errors.append(ValidationError("ERROR", f"Node at index {idx} is missing required string 'name'."))
                continue

            n_type = n.get("type", "dataset_table")
            if n_type not in VALID_ENTITY_TYPES:
                self.warnings.append(ValidationError(
                    "WARNING",
                    f"Node '{n_name}' has unrecognized type '{n_type}'. Defaulting to 'dataset_table'.",
                    f"Node: {n_name}"
                ))
                n["type"] = "dataset_table"
                n_type = "dataset_table"

            if n_type in ("source_table", "dataset_table"):
                self.stats["tables"] += 1
            elif n_type == "source_view":
                self.stats["views"] += 1
            elif n_type == "report":
                self.stats["reports"] += 1

            cols = n.get("columns", [])
            if not isinstance(cols, list):
                self.errors.append(ValidationError("ERROR", f"Node '{n_name}' has invalid 'columns' (must be a list).", f"Node: {n_name}"))
                continue

            node_id = n.get("id")
            for c_idx, c in enumerate(cols):
                c_name = c.get("name")
                if not c_name or not isinstance(c_name, str):
                    self.errors.append(ValidationError("ERROR", f"Column at index {c_idx} in node '{n_name}' missing 'name'.", f"Node: {n_name}"))
                    continue
                if not c.get("dataType"):
                    self.warnings.append(ValidationError("WARNING", f"Column '{c_name}' in '{n_name}' missing 'dataType'. Defaulting to 'String'.", f"Col: {c_name}"))
                    c["dataType"] = "String"

                self.stats["datasetColumns"] += 1

                # Record declared column URN
                if node_id:
                    declared_col_urns.add(f"{node_id}#{c_name.strip().lower()}")
                declared_col_urns.add(f"{n_name.lower()}#{c_name.strip().lower()}")
                declared_col_urns.add(c_name.strip().lower())

        # Validate edges
        edge_targets = {}
        valid_edges = []
        for e_idx, e in enumerate(edges):
            src = e.get("sourceColumnId")
            tgt = e.get("targetColumnId")
            if not src or not tgt:
                self.errors.append(ValidationError("ERROR", f"Edge at index {e_idx} missing 'sourceColumnId' or 'targetColumnId'.", f"Edge: {e}"))
                continue

            self.stats["columnEdges"] += 1
            edge_targets[tgt] = edge_targets.get(tgt, 0) + 1
            valid_edges.append(e)

        self.stats["multiDerivations"] = sum(1 for cnt in edge_targets.values() if cnt > 1)

        self.normalized_payload = {
            "server": self.data.get("server", "td_prod"),
            "defaultDatabase": self.data.get("defaultDatabase", "EDW_CORE"),
            "workspace": self.data.get("workspace", "Finance & Sales Analytics"),
            "nodes": nodes,
            "edges": valid_edges
        }

        return len(self.errors) == 0

    def _normalize_from_export(self, forced_type: str) -> bool:
        """Converts an exported lineage JSON into standard ingestion format."""
        raw_nodes = self.data.get("nodes", [])
        raw_edges = self.data.get("columnEdges", [])

        nodes = []
        for n in raw_nodes:
            cols = []
            for c in n.get("columns", []):
                cols.append({
                    "name": c.get("name"),
                    "dataType": c.get("dataType", "String"),
                    "isCalculated": c.get("isCalculated", False),
                    "expression": c.get("expression"),
                    "transformationType": c.get("transformationType", "Direct")
                })
            nodes.append({
                "id": n.get("id"),
                "name": n.get("name"),
                "container": n.get("database", "EDW_CORE"),
                "schema_name": n.get("schema_name", "dbo"),
                "type": n.get("type", "dataset_table"),
                "columns": cols
            })

        edges = []
        for e in raw_edges:
            edges.append({
                "sourceColumnId": e.get("sourceColumnId"),
                "targetColumnId": e.get("targetColumnId"),
                "transformationType": e.get("transformationType", "Direct"),
                "expression": e.get("expression")
            })

        self.data = {
            "scanner": "teradata" if forced_type == "teradata" else "fabric",
            "nodes": nodes,
            "edges": edges
        }
        return self._normalize_from_canonical(forced_type)

    def _normalize_from_fabric_scanner(self, forced_type: str) -> bool:
        """Converts legacy scanner_output.json format into standard ingestion format."""
        nodes = []
        edges = []

        for ws in self.data.get("workspaces", []):
            ws_name = ws.get("name", "Analytics Workspace")
            for ds in ws.get("datasets", []):
                for tbl in ds.get("tables", []):
                    cols = []
                    for c in tbl.get("columns", []):
                        cols.append({
                            "name": c.get("name"),
                            "dataType": c.get("dataType", "String"),
                            "isCalculated": bool(c.get("expression")),
                            "expression": c.get("expression"),
                            "transformationType": c.get("transformationType", "Direct")
                        })
                        if c.get("sourceTableId") and c.get("sourceColumnId"):
                            edges.append({
                                "sourceColumnId": c.get("sourceColumnId"),
                                "targetColumnId": c.get("id"),
                                "transformationType": c.get("transformationType", "Direct"),
                                "expression": c.get("expression")
                            })
                    nodes.append({
                        "name": tbl.get("name"),
                        "container": ds.get("name", ws_name),
                        "type": tbl.get("type", "dataset_table"),
                        "schema_name": tbl.get("schema", "Model"),
                        "columns": cols
                    })

        self.data = {
            "scanner": "fabric",
            "workspace": ws_name,
            "nodes": nodes,
            "edges": edges
        }
        return self._normalize_from_canonical(forced_type or "fabric")


def upload_payload(payload: Dict[str, Any], scanner_type: str, base_url: str) -> Tuple[bool, str]:
    """Uploads normalized payload to the Lineage FastAPI backend."""
    endpoint = f"{base_url.rstrip('/')}/api/ingest/{scanner_type}"
    payload_bytes = json.dumps(payload).encode("utf-8")

    req = urllib.request.Request(
        endpoint,
        data=payload_bytes,
        headers={"Content-Type": "application/json"},
        method="POST"
    )

    try:
        with urllib.request.urlopen(req, timeout=15) as resp:
            resp_body = resp.read().decode("utf-8")
            data = json.loads(resp_body)
            msg = data.get("message", f"HTTP {resp.status} OK")
            return True, msg

    except urllib.error.HTTPError as he:
        err_body = he.read().decode("utf-8", errors="replace")
        try:
            err_json = json.loads(err_body)
            detail = err_json.get("detail", err_body)
        except Exception:
            detail = err_body
        return False, f"Server HTTP {he.code}: {detail}"

    except urllib.error.URLError as ue:
        if "Connection refused" in str(ue.reason):
            return False, (
                f"Connection refused at {base_url}.\n"
                "  Is the Lineage Service running?\n"
                "  Start the server with: python3 run.py"
            )
        return False, f"Network error connecting to {base_url}: {str(ue.reason)}"

    except Exception as e:
        return False, f"Unexpected error during upload: {str(e)}"


def main():
    parser = argparse.ArgumentParser(
        description="Power BI & Teradata Lineage Ingestion & Pre-flight Validation Tool",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  # Pre-flight validation without upload:
  python3 scripts/load_lineage.py sample_data/teradata_sample.json --validate-only

  # Upload to default local lineage service (http://localhost:8000):
  python3 scripts/load_lineage.py sample_data/teradata_sample.json

  # Upload to custom host/port and force scanner type:
  python3 scripts/load_lineage.py sample_data/fabric_sample.json --type fabric --api-url http://10.20.30.40:8000
        """
    )

    parser.add_argument("file", help="Path to the JSON lineage file to validate or upload")
    parser.add_argument(
        "--type",
        choices=["teradata", "fabric", "auto"],
        default="auto",
        help="Scanner type: 'teradata', 'fabric', or 'auto' (default: auto-detect)"
    )
    parser.add_argument(
        "--api-url",
        default="http://localhost:8000",
        help="Base URL of Lineage backend service (default: http://localhost:8000)"
    )
    parser.add_argument(
        "--validate-only",
        action="store_true",
        help="Perform pre-flight JSON syntax and schema validation only without uploading"
    )
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Validate and prepare payload, display inventory report, but do not send HTTP request"
    )
    parser.add_argument(
        "--reset-first",
        action="store_true",
        help="Reset and re-seed the backend database before loading this file"
    )

    args = parser.parse_args()

    # 1. File existence check
    path = Path(args.file)
    if not path.exists():
        print(f"\n❌ Error: File not found: '{args.file}'", file=sys.stderr)
        sys.exit(1)

    # 2. JSON syntax check
    try:
        with open(path, "r", encoding="utf-8") as f:
            raw_data = json.load(f)
    except json.JSONDecodeError as jde:
        print(f"\n❌ Invalid JSON in '{args.file}':", file=sys.stderr)
        print(f"   Line {jde.lineno}, Column {jde.colno}: {jde.msg}", file=sys.stderr)
        sys.exit(1)
    except Exception as e:
        print(f"\n❌ Failed to read file '{args.file}': {str(e)}", file=sys.stderr)
        sys.exit(1)

    # 3. Schema & Integrity Validation
    validator = LineageValidator(raw_data, str(path))
    is_valid = validator.validate_and_normalize(args.type)

    scanner_type = validator.detected_scanner
    if args.type != "auto":
        scanner_type = args.type

    # Print Validation diagnostics
    print()
    if validator.warnings:
        print(f"⚠️  {len(validator.warnings)} Validation Warning(s):")
        for w in validator.warnings:
            print(f"   • {w}")
        print()

    if not is_valid or validator.errors:
        print(f"❌ Validation Failed with {len(validator.errors)} Error(s):")
        for err in validator.errors:
            print(f"   • {err}")
        print("\nAborting: please fix the JSON errors above before loading.")
        sys.exit(1)

    print("✅ Pre-flight validation passed successfully.")

    # 4. Handle --validate-only
    if args.validate_only:
        report = format_report_box(
            title="PRE-FLIGHT LINEAGE VALIDATION REPORT",
            stats=validator.stats,
            api_url="(Validation Only - Not Uploaded)",
            scanner_type=scanner_type,
            status_msg="File conforms to lineage specification.",
            is_success=True
        )
        print("\n" + report)
        sys.exit(0)

    # 5. Optional Reset First
    if args.reset_first:
        reset_url = f"{args.api_url.rstrip('/')}/api/reset"
        print(f"🔄 Resetting database at {reset_url}...")
        try:
            req = urllib.request.Request(reset_url, data=b"{}", headers={"Content-Type": "application/json"}, method="POST")
            with urllib.request.urlopen(req, timeout=10) as r:
                pass
            print("   Database reset successfully.")
        except Exception as e:
            print(f"   ⚠️ Warning: Failed to reset database: {str(e)}")

    # 6. Handle --dry-run
    if args.dry_run:
        report = format_report_box(
            title="DRY-RUN LINEAGE INVENTORY REPORT",
            stats=validator.stats,
            api_url=f"{args.api_url}/api/ingest/{scanner_type} (Dry Run)",
            scanner_type=scanner_type,
            status_msg="Dry-run complete. Ready to upload.",
            is_success=True
        )
        print("\n" + report)
        sys.exit(0)

    # 7. Upload to Lineage API
    print(f"🚀 Uploading lineage payload to {args.api_url}/api/ingest/{scanner_type}...")
    success, msg = upload_payload(validator.normalized_payload, scanner_type, args.api_url)

    report = format_report_box(
        title="LINEAGE INGESTION EXECUTION REPORT",
        stats=validator.stats,
        api_url=f"{args.api_url}/api/ingest/{scanner_type}",
        scanner_type=scanner_type,
        status_msg=msg,
        is_success=success
    )
    print("\n" + report)

    if not success:
        sys.exit(2)


if __name__ == "__main__":
    main()
