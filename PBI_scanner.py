#!/usr/bin/env python3
"""
===============================================================================
 Power BI / Fabric Metadata Scanner CLI
 Optimized & Streamlined Edition (Enterprise Compliant)
===============================================================================
 Connects to Azure Fabric & Power BI Scanner APIs to extract:
   - Workspaces, datasets, and reports
   - Power Query (M) transformations and source database dependencies
   - DAX calculated columns and cross-table references
   - End-to-end column-level lineage graph in canonical format

 Usage:
   python3 PBI_scanner.py --workspace-id <ws_id> --report-id <rep_id> --report-name <name>
"""

import argparse
import copy
import json
import os
import re
import sys
import time
from datetime import datetime, timezone

import requests
import urllib3
from urllib3.exceptions import InsecureRequestWarning

# Environment variable keys
TENANT_ID_ENV = "PBI_TENANT_ID"
CLIENT_ID_ENV = "PBI_CLIENT_ID"
CLIENT_SECRET_ENV = "PBI_CLIENT_SECRET"
PROXY_ENV = "PBI_PROXY"

# Power BI REST API URLs
RESOURCE_URI = "https://analysis.windows.net/powerbi/api"
SCAN_URL = (
    "https://api.powerbi.com/v1.0/myorg/admin/workspaces/getInfo"
    "?lineage=true&datasourceDetails=true&datasetSchema=true&datasetExpressions=true"
)
GROUP_REPORT_URL_TEMPLATE = (
    "https://api.powerbi.com/v1.0/myorg/groups/{workspace_id}/reports/{report_id}"
)

# API Timeouts and polling configuration
REQUEST_TIMEOUT = 60
SCAN_TIMEOUT_SECONDS = 300
SCAN_POLL_SECONDS = 5

urllib3.disable_warnings(InsecureRequestWarning)

# Pre-compiled Regexes for High-Performance Parsing
URN_PATTERN = re.compile(r"^[a-z0-9]+://[a-z0-9_\-\.]+/[a-z0-9_\-\.]+/[a-z0-9_\-\.]+#[a-z0-9_\-\.]+$")
DAX_PATTERN = re.compile(r"(?:'([^']+)'|([A-Za-z0-9_ ]+))?\[([^\]]+)\]")
RENAME_PATTERN = re.compile(r'\{"([^"]+)",\s*"([^"]+)"\}')
ADD_COL_PATTERN = re.compile(r'Table\.AddColumn\([^,]+,\s*"([^"]+)"\s*,\s*each\s*(.+)\)$')
COL_REF_PATTERN = re.compile(r'\[([^\]]+)\]')
SCHEMA_ITEM_PATTERN = re.compile(r'Schema\s*=\s*"([^"]+)"\s*,\s*Item\s*=\s*"([^"]+)"', re.IGNORECASE)
NAME_MATCH_PATTERN = re.compile(r'\[Name\s*=\s*"([^"]+)"\]', re.IGNORECASE)
FROM_MATCH_PATTERN = re.compile(r'\bfrom\s+([\[\]\w\."]+)', re.IGNORECASE)

POWER_QUERY_MARKERS = (
    "let\n", "let\r\n", "table.", "text.", "number.", "datetime.", "date.",
    "time.", "duration.", "record.", "list.", "value.", "binary.",
    "teradata.database", "sql.database", "each ", "=>"
)


# =============================================================================
# 1. Network, Environment & OAuth2 Authentication
# =============================================================================

def build_proxies():
    proxy_url = (
        os.getenv(PROXY_ENV)
        or os.getenv("HTTPS_PROXY")
        or os.getenv("HTTP_PROXY")
    )
    if not proxy_url or not proxy_url.strip():
        return None
    p = proxy_url.strip()
    return {"http": p, "https": p}


def get_required_env(var_name):
    val = os.getenv(var_name)
    if val is None or not val.strip():
        raise RuntimeError(f"Missing required environment variable: {var_name}.")
    return val.strip()


def get_access_token(proxies, tenant_id, client_id, client_secret):
    auth_url = f"https://login.microsoftonline.com/{tenant_id}/oauth2/v2.0/token"
    token_data = {
        "client_id": client_id,
        "scope": f"{RESOURCE_URI}/.default",
        "client_secret": client_secret,
        "grant_type": "client_credentials",
    }
    response = requests.post(
        auth_url,
        data=token_data,
        proxies=proxies,
        verify=False,
        timeout=REQUEST_TIMEOUT,
    )
    response.raise_for_status()
    access_token = response.json().get("access_token")
    if not access_token:
        raise RuntimeError("Access token was not returned by Azure AD.")
    print("Access token retrieved successfully.")
    return access_token


def request_json(method, url, token, proxies, **kwargs):
    headers = kwargs.pop("headers", {})
    headers["Authorization"] = f"Bearer {token}"
    response = requests.request(
        method,
        url,
        headers=headers,
        proxies=proxies,
        verify=False,
        timeout=REQUEST_TIMEOUT,
        **kwargs,
    )
    response.raise_for_status()
    return response.json() if response.text else {}


# =============================================================================
# 2. Power BI Admin Scanner API Execution
# =============================================================================

def start_workspace_scan(token, proxies, workspace_id):
    body = {
        "workspaces": [workspace_id],
        "lineage": True,
        "datasourceDetails": True,
        "datasetSchema": True,
        "datasetExpressions": True,
    }
    response_json = request_json("POST", SCAN_URL, token, proxies, json=body)
    scan_id = response_json.get("id")
    if not scan_id:
        raise RuntimeError("Unable to start workspace scan. Response did not include scan id.")
    print(f"Scan started. Scan ID: {scan_id}")
    return scan_id


def wait_for_scan_completion(token, proxies, scan_id):
    status_url = f"https://api.powerbi.com/v1.0/myorg/admin/workspaces/scanStatus/{scan_id}"
    deadline = time.time() + SCAN_TIMEOUT_SECONDS

    while time.time() < deadline:
        status_payload = request_json("GET", status_url, token, proxies)
        status = (status_payload.get("status") or "").lower()
        print(f"Scan status: {status_payload.get('status', 'Unknown')}")

        if status == "succeeded":
            return
        if status in {"failed", "error"}:
            raise RuntimeError(f"Scan failed: {json.dumps(status_payload)}")

        time.sleep(SCAN_POLL_SECONDS)

    raise TimeoutError(f"Scan did not complete within {SCAN_TIMEOUT_SECONDS} seconds.")


def get_scan_result(token, proxies, scan_id):
    result_url = f"https://api.powerbi.com/v1.0/myorg/admin/workspaces/scanResult/{scan_id}"
    payload = request_json("GET", result_url, token, proxies)
    if not payload:
        raise RuntimeError("Scan result payload is empty.")
    return payload


def verify_report_dataset_binding(token, proxies, workspace_id, report_id, expected_dataset_id):
    report_url = GROUP_REPORT_URL_TEMPLATE.format(workspace_id=workspace_id, report_id=report_id)
    try:
        report_payload = request_json("GET", report_url, token, proxies)
        actual_dataset_id = report_payload.get("datasetId")
        if actual_dataset_id and actual_dataset_id != expected_dataset_id:
            raise RuntimeError(
                f"Dataset mismatch: expected {expected_dataset_id}, but report is bound to {actual_dataset_id}."
            )
    except requests.HTTPError as exc:
        print(f"Warning: Could not validate report-dataset binding with group endpoint: {exc}")


# =============================================================================
# 3. Workspace Object Lookup & Entity Resolution
# =============================================================================

def safe_list(val):
    return val if isinstance(val, list) else []


def find_workspace(scan_result, workspace_id):
    for ws in safe_list(scan_result.get("workspaces")):
        if ws.get("id") == workspace_id:
            return ws
    return None


def find_report(workspace_obj, report_id, report_name):
    reports = safe_list(workspace_obj.get("reports"))
    for r in reports:
        if r.get("id") == report_id:
            return r, "report_id"
    for r in reports:
        if (r.get("name") or "").strip().lower() == report_name.strip().lower():
            return r, "report_name"
    return None, "none"


def find_dataset(workspace_obj, dataset_id):
    for ds in safe_list(workspace_obj.get("datasets")):
        if ds.get("id") == dataset_id:
            return ds
    return None


# =============================================================================
# 4. Runtime Variable Substitution
# =============================================================================

def build_runtime_variables(cli_vars=None, p_entity=None, p_environment=None):
    vars_dict = {}
    for raw in cli_vars or []:
        if "=" in raw:
            k, _, v = raw.partition("=")
            if k.strip():
                vars_dict[k.strip().lower()] = v.strip()
    if p_entity:
        vars_dict["p_entity"] = p_entity.strip()
    if p_environment:
        vars_dict["p_environment"] = p_environment.strip()
    return vars_dict


def substitute_runtime_variables(expression, runtime_variables):
    if not expression or not runtime_variables:
        return expression

    text = str(expression)
    lowered = text.lower()
    if not any(marker in lowered for marker in POWER_QUERY_MARKERS):
        return expression

    # Replace variable identifiers
    for var_name, var_val in runtime_variables.items():
        pattern = re.compile(rf'\b{re.escape(var_name)}\b', re.IGNORECASE)
        text = pattern.sub(f'"{var_val}"', text)

    return text


def apply_runtime_variables_to_dataset(dataset, runtime_variables):
    if not runtime_variables:
        return dataset

    # In-memory deep copy
    dataset_copy = copy.deepcopy(dataset)
    for table in safe_list(dataset_copy.get("tables")):
        for source in safe_list(table.get("source")):
            if source.get("expression"):
                source["expression"] = substitute_runtime_variables(source["expression"], runtime_variables)
        for col in safe_list(table.get("columns")):
            if col.get("expression"):
                col["expression"] = substitute_runtime_variables(col["expression"], runtime_variables)

    return dataset_copy


# =============================================================================
# 5. M & DAX Expression Lineage Extractors
# =============================================================================

def extract_model_columns(table):
    cols = []
    for c in safe_list(table.get("columns")):
        cols.append({
            "name": c.get("name"),
            "data_type": c.get("dataType"),
            "is_hidden": c.get("isHidden", False),
            "expression": c.get("expression"),
            "source_column": c.get("sourceColumn"),
            "is_calculated": bool(c.get("expression")),
            "transformation_type": c.get("transformationType"),
        })
    return cols


def extract_table_transformations(table):
    transformations = []
    for source_entry in safe_list(table.get("source")):
        expression = source_entry.get("expression") or ""
        for raw_line in expression.splitlines():
            line = raw_line.strip()
            if not line or line.lower() in {"let", "in"} or "=" not in line:
                continue

            left, right = line.split("=", 1)
            step_name = left.strip().strip(",")
            rhs = right.strip().rstrip(",")
            if not step_name or not rhs:
                continue

            op_match = re.search(r"([A-Za-z_][A-Za-z0-9_\.]*)\s*\(", rhs)
            operation = op_match.group(1) if op_match else "expression"

            transformations.append({
                "step_name": step_name,
                "operation": operation,
                "expression": rhs,
            })
    return transformations


def infer_source_objects_from_expression(expression):
    if not expression:
        return []

    objects = []
    # 1. Schema="..." and Item="..."
    for schema, item in SCHEMA_ITEM_PATTERN.findall(expression):
        objects.append({"object_name": f"{schema}.{item}", "object_type": "table_or_view"})

    # 2. [Name="..."]
    for name in NAME_MATCH_PATTERN.findall(expression):
        objects.append({"object_name": name, "object_type": "table_or_view"})

    # 3. from <table_name>
    for tbl in FROM_MATCH_PATTERN.findall(expression):
        clean = tbl.strip("[]\"")
        if clean:
            objects.append({"object_name": clean, "object_type": "table_or_view"})

    # Deduplicate
    unique = {}
    for obj in objects:
        unique[obj["object_name"]] = obj
    return list(unique.values())


def extract_table_source_objects(table):
    objects = []
    for source_entry in safe_list(table.get("source")):
        objects.extend(infer_source_objects_from_expression(source_entry.get("expression")))
    if not objects:
        objects.append({"object_name": "unknown_source_object", "object_type": "unknown"})
    return objects


def build_column_lineage_for_table(model_columns, transformations):
    model_col_names = {c.get("name") for c in model_columns if c.get("name")}
    mappings = []

    for step in transformations:
        op = step.get("operation", "")
        expr = step.get("expression", "")
        step_name = step.get("step_name", "")

        if op.endswith("RenameColumns"):
            for src_col, dst_col in RENAME_PATTERN.findall(expr):
                if dst_col in model_col_names:
                    mappings.append({
                        "source_column": src_col,
                        "model_column": dst_col,
                        "transformation_step": step_name,
                        "mapping_type": "rename",
                    })

        elif op.endswith("AddColumn"):
            add_match = ADD_COL_PATTERN.search(expr)
            if add_match:
                new_col, calc_expr = add_match.group(1), add_match.group(2)
                if new_col in model_col_names:
                    refs = COL_REF_PATTERN.findall(calc_expr)
                    for ref in refs:
                        mappings.append({
                            "source_column": ref,
                            "model_column": new_col,
                            "transformation_step": step_name,
                            "mapping_type": "derived",
                        })

    # Add direct pass-through for mapped source columns
    for c in model_columns:
        src = c.get("source_column")
        tgt = c.get("name")
        if src and tgt and src != tgt and not any(m["model_column"] == tgt for m in mappings):
            mappings.append({
                "source_column": src,
                "model_column": tgt,
                "transformation_step": "SourceProjection",
                "mapping_type": "projection",
            })

    return mappings


def parse_dax_dependencies(current_table_name, expression):
    if not expression:
        return []
    dependencies = []
    seen = set()

    for match in DAX_PATTERN.finditer(expression):
        table_name = match.group(1) or match.group(2) or current_table_name
        column_name = match.group(3)
        if not column_name:
            continue
        key = (table_name.strip(), column_name.strip())
        if key not in seen:
            seen.add(key)
            dependencies.append({
                "table_name": table_name.strip(),
                "column_name": column_name.strip(),
            })

    return dependencies


def infer_dax_transformation_type(current_table_name, dependencies):
    curr = normalize_urn_segment(current_table_name)
    for dep in dependencies:
        if normalize_urn_segment(dep.get("table_name")) != curr:
            return "DAX_Cross_Table"
    return "DAX_Calculated"


def infer_mapping_transformation_type(col_map, transformation_step):
    mapping_type = (col_map.get("mapping_type") or "").lower()
    operation = (transformation_step or {}).get("operation", "")

    if mapping_type == "projection":
        return "Direct"
    if mapping_type == "rename":
        return "PowerQuery_Rename"
    if mapping_type == "derived":
        return "PowerQuery_Derived" if operation.endswith("AddColumn") else "PowerQuery_Expression"
    return "Direct"


# =============================================================================
# 6. Standard URN Builders
# =============================================================================

def normalize_urn_segment(value):
    normalized = re.sub(r"[^a-z0-9]+", "_", str(value or "").strip().lower())
    return re.sub(r"_+", "_", normalized).strip("_") or "unknown"


def normalize_container_segment(value, fallback):
    text = str(value or "").strip()
    return fallback if (not text or (text.startswith("<") and text.endswith(">"))) else normalize_urn_segment(text)


def build_fabric_table_urn(workspace_name, dataset_name, table_name):
    return f"fabric://{normalize_urn_segment(workspace_name)}/{normalize_urn_segment(dataset_name)}/{normalize_urn_segment(table_name)}"


def build_fabric_dataset_urn(workspace_name, dataset_name):
    return f"fabric://{normalize_urn_segment(workspace_name)}/datasets/{normalize_urn_segment(dataset_name)}"


def build_fabric_report_urn(workspace_name, report_name):
    return f"fabric://{normalize_urn_segment(workspace_name)}/reports/{normalize_urn_segment(report_name)}"


def build_fabric_column_urn(workspace_name, dataset_name, table_name, column_name):
    return f"{build_fabric_table_urn(workspace_name, dataset_name, table_name)}#{normalize_urn_segment(column_name)}"


def split_source_object_name(object_name):
    cleaned = str(object_name or "").strip().strip('[]"')
    parts = [p.strip().strip('[]"') for p in cleaned.split(".") if p.strip()]
    if len(parts) >= 2:
        return parts[-2], parts[-1]
    return (None, parts[0]) if len(parts) == 1 else (None, None)


def build_source_object_urn(source_system, source_object_name):
    conn = source_system.get("connection_details") or {}
    stype = normalize_urn_segment(source_system.get("type")).replace("_", "")
    scheme = "teradata" if "teradata" in stype else (stype or "source")
    host = normalize_urn_segment(conn.get("server") or conn.get("host") or source_system.get("name") or "unknown_source")
    schema_name, table_name = split_source_object_name(source_object_name)
    default_container = normalize_container_segment(conn.get("database") or conn.get("schema"), fallback="unknown_container")
    container = normalize_container_segment(schema_name, fallback=default_container)
    object_seg = normalize_urn_segment(table_name or source_object_name or "unknown_object")
    return f"{scheme}://{host}/{container}/{object_seg}"


def build_source_column_urn(source_system, source_object_name, column_name):
    return f"{build_source_object_urn(source_system, source_object_name)}#{normalize_urn_segment(column_name)}"


# =============================================================================
# 7. Datasource Resolution
# =============================================================================

def build_source_system_lookup(scan_result, workspace_obj):
    lookup = {}
    datasources = safe_list(scan_result.get("datasourceInstances")) or safe_list(workspace_obj.get("datasourceInstances"))

    for idx, inst in enumerate(datasources, start=1):
        sid = inst.get("datasourceId") or inst.get("id") or f"src_{idx}"
        conn = inst.get("connectionDetails") or {}
        lookup[sid] = {
            "id": sid,
            "name": conn.get("server") or conn.get("database") or inst.get("datasourceType", "source"),
            "type": inst.get("datasourceType", "unknown"),
            "connection_details": conn,
        }
    return lookup


def map_dataset_sources(dataset, source_lookup):
    usages = safe_list(dataset.get("datasourceUsages"))
    mapped = [source_lookup[u["datasourceInstanceId"]] for u in usages if u.get("datasourceInstanceId") in source_lookup]
    if mapped:
        return mapped
    return list(source_lookup.values()) if source_lookup else [{
        "id": "unknown_source", "name": "unknown_source", "type": "unknown", "connection_details": {}
    }]


# =============================================================================
# 8. Single-Pass Canonical Lineage Generator
# =============================================================================

def build_canonical_fabric_payload(workspace_obj, dataset, report, scan_result=None):
    """
    Constructs the standardized lineage payload containing:
      - 'nodes': Dataset tables and Power BI report visual entities
      - 'edges': Column-level lineage edges connecting sources -> dataset -> report
      - 'reports' and 'reportLinks': Metadata bindings
    """
    workspace_name = workspace_obj.get("name") or "unknown_workspace"
    dataset_name = dataset.get("name") or "unknown_dataset"
    dataset_id = dataset.get("id") or "unknown_dataset_id"
    dataset_tables = safe_list(dataset.get("tables"))

    source_lookup = build_source_system_lookup(scan_result or {}, workspace_obj)
    dataset_sources = map_dataset_sources(dataset, source_lookup)
    primary_source = dataset_sources[0] if dataset_sources else {"type": "unknown", "connection_details": {}}

    source_nodes_map = {}
    dataset_nodes = []
    edges = []
    seen_edges = set()

    # 1. Process Dataset Tables & Columns
    for raw_table in dataset_tables:
        table_name = raw_table.get("name")
        if not table_name:
            continue

        table_urn = build_fabric_table_urn(workspace_name, dataset_name, table_name)
        model_columns = extract_model_columns(raw_table)
        transformations = extract_table_transformations(raw_table)
        step_lookup = {t["step_name"]: t for t in transformations}
        col_lineage = build_column_lineage_for_table(model_columns, transformations)
        source_objects = extract_table_source_objects(raw_table)
        primary_source_obj = source_objects[-1]["object_name"] if source_objects else table_name

        table_cols = []
        for col in model_columns:
            c_name = col.get("name")
            if not c_name:
                continue

            expr = col.get("expression")
            c_urn = build_fabric_column_urn(workspace_name, dataset_name, table_name, c_name)
            col_payload = {
                "id": c_urn,
                "name": c_name,
                "dataType": col.get("data_type") or "String",
            }

            if col.get("is_calculated") and expr:
                dax_deps = parse_dax_dependencies(table_name, expr)
                col_payload["isCalculated"] = True
                col_payload["expression"] = expr
                col_payload["transformationType"] = col.get("transformation_type") or infer_dax_transformation_type(table_name, dax_deps)

            table_cols.append(col_payload)

        dataset_nodes.append({
            "id": table_urn,
            "name": table_name,
            "container": normalize_urn_segment(dataset_name),
            "schema_name": "Model",
            "type": "dataset_table",
            "columns": table_cols,
        })

        # 2. Build Ingest Edges from Source Objects & Record Upstream Source Nodes
        for mapping in col_lineage:
            src_col = mapping.get("source_column")
            tgt_col = mapping.get("model_column")
            step = step_lookup.get(mapping.get("transformation_step"), {})
            trans_type = infer_mapping_transformation_type(mapping, step)

            if src_col and tgt_col:
                src_urn = build_source_column_urn(primary_source, primary_source_obj, src_col)
                tgt_urn = build_fabric_column_urn(workspace_name, dataset_name, table_name, tgt_col)
                src_node_urn = build_source_object_urn(primary_source, primary_source_obj)

                # Register upstream source node and column so React Flow can render the edges
                if src_node_urn not in source_nodes_map:
                    s_schema, s_table = split_source_object_name(primary_source_obj)
                    if not s_schema and len(source_objects) >= 2:
                        s_schema = source_objects[-2]["object_name"]
                    conn = primary_source.get("connection_details") or {}
                    def_container = normalize_container_segment(conn.get("database") or conn.get("schema"), fallback="unknown_container")
                    s_container = normalize_container_segment(s_schema, fallback=def_container)
                    source_nodes_map[src_node_urn] = {
                        "id": src_node_urn,
                        "name": s_table or primary_source_obj,
                        "container": s_container,
                        "schema_name": s_schema or "dbo",
                        "type": "source_table",
                        "columns": {}
                    }
                if src_col not in source_nodes_map[src_node_urn]["columns"]:
                    source_nodes_map[src_node_urn]["columns"][src_col] = {
                        "id": src_urn,
                        "name": src_col,
                        "dataType": "String"
                    }

                edge_key = (src_urn, tgt_urn)
                if edge_key not in seen_edges:
                    seen_edges.add(edge_key)
                    edges.append({
                        "sourceColumnId": src_urn,
                        "targetColumnId": tgt_urn,
                        "transformationType": trans_type,
                        "expression": step.get("expression") or f"{primary_source_obj}[{src_col}]"
                    })

        # 3. Build Cross-Table DAX Calculated Column Edges
        for col in model_columns:
            expr = col.get("expression")
            c_name = col.get("name")
            if not expr or not c_name:
                continue

            dax_deps = parse_dax_dependencies(table_name, expr)
            trans_type = infer_dax_transformation_type(table_name, dax_deps)
            tgt_urn = build_fabric_column_urn(workspace_name, dataset_name, table_name, c_name)

            for dep in dax_deps:
                src_urn = build_fabric_column_urn(workspace_name, dataset_name, dep["table_name"], dep["column_name"])
                edge_key = (src_urn, tgt_urn)
                if edge_key not in seen_edges:
                    seen_edges.add(edge_key)
                    edges.append({
                        "sourceColumnId": src_urn,
                        "targetColumnId": tgt_urn,
                        "transformationType": trans_type,
                        "expression": expr
                    })

    # Assemble nodes: upstream sources first, then dataset tables
    nodes = []
    for s_node in source_nodes_map.values():
        nodes.append({
            "id": s_node["id"],
            "name": s_node["name"],
            "container": s_node["container"],
            "schema_name": s_node["schema_name"],
            "type": s_node["type"],
            "columns": list(s_node["columns"].values())
        })
    nodes.extend(dataset_nodes)

    # 4. Process Power BI Report Entity Node
    reports = []
    report_links = []
    report_id = report.get("id") if report else None
    report_name = report.get("name") if report else None

    if report_id and report_name:
        report_urn = build_fabric_report_urn(workspace_name, report_name)
        dataset_urn = build_fabric_dataset_urn(workspace_name, dataset_name)

        # Build report visual columns bound to dataset tables
        report_cols = [
            {
                "id": f"{report_urn}#report_view",
                "name": "Report_View",
                "dataType": "Visual",
                "isCalculated": False,
                "transformationType": "Report_Binding",
                "expression": f"Dataset: {dataset_name}"
            }
        ]

        report_node = {
            "id": report_urn,
            "name": report_name,
            "container": normalize_urn_segment(workspace_name),
            "schema_name": "Visual",
            "type": "report",
            "columns": report_cols,
        }
        nodes.append(report_node)

        # Bridge edge from first dataset table column into report visual
        if dataset_nodes and dataset_nodes[0].get("columns"):
            first_table = dataset_nodes[0]
            first_col = first_table["columns"][0]["name"]
            src_col_urn = build_fabric_column_urn(workspace_name, dataset_name, first_table["name"], first_col)
            tgt_rep_urn = f"{report_urn}#report_view"
            edges.append({
                "sourceColumnId": src_col_urn,
                "targetColumnId": tgt_rep_urn,
                "transformationType": "Report_Binding",
                "expression": f"Visual Binding: {report_name}"
            })

        reports.append({
            "id": report_id,
            "name": report_name,
            "urn": report_urn,
            "datasetId": report.get("datasetId") or dataset_id,
            "datasetUrn": dataset_urn,
            "webUrl": report.get("webUrl"),
        })
        report_links.append({
            "reportId": report_id,
            "reportUrn": report_urn,
            "datasetId": report.get("datasetId") or dataset_id,
            "datasetUrn": dataset_urn,
            "relationship": "consumes_dataset",
        })

    nodes.sort(key=lambda n: (0 if n.get("type") == "source_table" else (1 if n.get("type") == "dataset_table" else 2), normalize_urn_segment(n.get("name"))))
    edges.sort(key=lambda e: (e.get("sourceColumnId", ""), e.get("targetColumnId", "")))

    return {
        "workspace": workspace_name,
        "nodes": nodes,
        "edges": edges,
        "reports": reports,
        "reportLinks": report_links,
    }


# =============================================================================
# 9. Declarative Payload Validation
# =============================================================================

def validate_canonical_payload(payload):
    if not isinstance(payload, dict):
        return ["Payload must be a JSON object."]

    errors = []
    workspace = payload.get("workspace")
    if not isinstance(workspace, str) or not workspace.strip():
        errors.append("Top-level 'workspace' must be a non-empty string.")

    nodes = payload.get("nodes")
    if not isinstance(nodes, list) or not nodes:
        errors.append("Top-level 'nodes' must be a non-empty array.")
        nodes = []

    edges = payload.get("edges")
    if not isinstance(edges, list):
        errors.append("Top-level 'edges' must be an array.")
        edges = []

    fabric_column_ids = set()
    node_names = set()

    for idx, node in enumerate(nodes, start=1):
        if not isinstance(node, dict):
            errors.append(f"Node #{idx} must be an object.")
            continue

        name = node.get("name")
        container = node.get("container")
        schema_name = node.get("schema_name")
        node_type = node.get("type")
        columns = node.get("columns", [])

        if not isinstance(name, str) or not name.strip():
            errors.append(f"Node #{idx} has invalid 'name'.")
            continue
        node_key = node.get("id") or (node_type, name)
        if node_key in node_names:
            errors.append(f"Duplicate node '{name}'.")
        node_names.add(node_key)

        if not isinstance(container, str) or not container.strip():
            errors.append(f"Node '{name}' has invalid 'container'.")
        if not isinstance(schema_name, str) or not schema_name.strip():
            errors.append(f"Node '{name}' has invalid 'schema_name'.")
        if node_type not in ("dataset_table", "report", "source_table", "source_view"):
            errors.append(f"Node '{name}' must have type 'dataset_table', 'report', 'source_table', or 'source_view'.")

        if not isinstance(columns, list):
            errors.append(f"Node '{name}' has invalid 'columns'.")
            continue

        for col_idx, col in enumerate(columns, start=1):
            if not isinstance(col, dict):
                errors.append(f"Column #{col_idx} in node '{name}' must be an object.")
                continue
            c_name = col.get("name")
            if not isinstance(c_name, str) or not c_name.strip():
                errors.append(f"Column #{col_idx} in node '{name}' has invalid 'name'.")
                continue

            if node_type == "report":
                fabric_column_ids.add(f"{build_fabric_report_urn(workspace, name)}#{normalize_urn_segment(c_name)}")
            elif node_type == "dataset_table":
                fabric_column_ids.add(build_fabric_column_urn(workspace, container, name, c_name))
            else:
                fabric_column_ids.add(col.get("id") or f"{node.get('id')}#{normalize_urn_segment(c_name)}")

            if col.get("isCalculated") and not col.get("expression"):
                errors.append(f"Calculated column '{name}.{c_name}' is missing 'expression'.")

    for edge_idx, edge in enumerate(edges, start=1):
        if not isinstance(edge, dict):
            errors.append(f"Edge #{edge_idx} must be an object.")
            continue

        src = edge.get("sourceColumnId")
        tgt = edge.get("targetColumnId")
        trans_type = edge.get("transformationType")

        if not isinstance(src, str) or not URN_PATTERN.match(src):
            errors.append(f"Edge #{edge_idx} has invalid 'sourceColumnId'.")
        if not isinstance(tgt, str) or not URN_PATTERN.match(tgt):
            errors.append(f"Edge #{edge_idx} has invalid 'targetColumnId'.")
        elif tgt not in fabric_column_ids:
            errors.append(f"Edge #{edge_idx} targets unknown Fabric column URN '{tgt}'.")
        if not isinstance(trans_type, str) or not trans_type.strip():
            errors.append(f"Edge #{edge_idx} has invalid 'transformationType'.")

    return errors


# =============================================================================
# 10. CLI Argument Parsing & Main Entrypoint
# =============================================================================

def parse_args():
    parser = argparse.ArgumentParser(
        description="Extract and generate canonical Fabric/Power BI column lineage JSON."
    )
    parser.add_argument("--workspace-id", required=True, help="Power BI / Fabric workspace GUID")
    parser.add_argument("--report-id", required=True, help="Power BI report GUID")
    parser.add_argument("--report-name", required=True, help="Display name of the target report")
    parser.add_argument("--output", default="lineage_output.json", help="Path to write lineage JSON output")
    parser.add_argument(
        "--var",
        action="append",
        default=[],
        metavar="name=value",
        help="Runtime variable to substitute into M/DAX expressions (e.g. env=prod).",
    )
    parser.add_argument("--p-entity", help="Convenience alias for entity variable")
    parser.add_argument("--p-environment", help="Convenience alias for environment variable")
    return parser.parse_args()


def main():
    args = parse_args()
    proxies = build_proxies()

    try:
        tenant_id = get_required_env(TENANT_ID_ENV)
        client_id = get_required_env(CLIENT_ID_ENV)
        client_secret = get_required_env(CLIENT_SECRET_ENV)

        runtime_variables = build_runtime_variables(
            cli_vars=args.var,
            p_entity=args.p_entity,
            p_environment=args.p_environment,
        )

        # 1. Authenticate & Trigger Workspace Scan
        token = get_access_token(proxies, tenant_id, client_id, client_secret)
        scan_id = start_workspace_scan(token, proxies, args.workspace_id)
        wait_for_scan_completion(token, proxies, scan_id)
        scan_result = get_scan_result(token, proxies, scan_id)

        # 2. Locate Workspace, Report, and Dataset
        workspace_obj = find_workspace(scan_result, args.workspace_id)
        if not workspace_obj:
            raise RuntimeError(f"Target workspace '{args.workspace_id}' was not found in scan results.")

        report, match_mode = find_report(workspace_obj, args.report_id, args.report_name)
        if not report:
            raise RuntimeError(f"Report not found in scanned workspace. ID: {args.report_id}, Name: {args.report_name}")

        dataset_id = report.get("datasetId")
        if not dataset_id:
            raise RuntimeError(f"Report '{report.get('name')}' does not reference a dataset.")

        dataset = find_dataset(workspace_obj, dataset_id)
        if not dataset:
            raise RuntimeError(f"Dataset '{dataset_id}' referenced by report was not found in scan results.")

        # 3. Apply Variable Substitutions & Validate Binding
        dataset = apply_runtime_variables_to_dataset(dataset, runtime_variables)
        verify_report_dataset_binding(token, proxies, args.workspace_id, report.get("id"), dataset_id)

        # 4. Generate Canonical Payload directly (1-pass)
        canonical_payload = build_canonical_fabric_payload(
            workspace_obj=workspace_obj,
            dataset=dataset,
            report=report,
            scan_result=scan_result,
        )

        validation_errors = validate_canonical_payload(canonical_payload)
        if validation_errors:
            raise RuntimeError("Canonical lineage payload failed validation: " + " | ".join(validation_errors))

        # 5. Output Results
        with open(args.output, "w", encoding="utf-8") as out_f:
            json.dump(canonical_payload, out_f, indent=2)

        print(f"\n✅ Canonical Fabric lineage JSON written to: {args.output}")
        print("✅ Validation: PASSED")
        if runtime_variables:
            print("   Runtime variables: " + ", ".join(f"{k}={v}" for k, v in sorted(runtime_variables.items())))

        report_nodes = [n for n in canonical_payload["nodes"] if n.get("type") == "report"]
        table_nodes = [n for n in canonical_payload["nodes"] if n.get("type") == "dataset_table"]

        print(
            f"   Summary: workspace={workspace_obj.get('name')} | "
            f"tables={len(table_nodes)} | "
            f"reports={len(report_nodes)} | "
            f"edges={len(canonical_payload['edges'])}"
        )
        return 0

    except requests.HTTPError as exc:
        status_code = exc.response.status_code if exc.response else "unknown"
        response_text = exc.response.text if exc.response else "no response body"
        print(f"❌ HTTP Error ({status_code}): {response_text}", file=sys.stderr)
        return 1
    except Exception as exc:
        print(f"❌ Error: {exc}", file=sys.stderr)
        return 1


if __name__ == "__main__":
    sys.exit(main())
