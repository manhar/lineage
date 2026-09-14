import argparse
import json
import os
import re
import sys
import time
from collections import defaultdict
from datetime import datetime, timezone

import requests
import urllib3
from urllib3.exceptions import InsecureRequestWarning


TENANT_ID_ENV = "PBI_TENANT_ID"
CLIENT_ID_ENV = "PBI_CLIENT_ID"
CLIENT_SECRET_ENV = "PBI_CLIENT_SECRET"
PROXY_ENV = "PBI_PROXY"

RESOURCE_URI = "https://analysis.windows.net/powerbi/api"

SCAN_URL = (
    "https://api.powerbi.com/v1.0/myorg/admin/workspaces/getInfo"
    "?lineage=true&datasourceDetails=true&datasetSchema=true&datasetExpressions=true"
)
GROUP_REPORT_URL_TEMPLATE = (
    "https://api.powerbi.com/v1.0/myorg/groups/{workspace_id}/reports/{report_id}"
)

REQUEST_TIMEOUT = 60
SCAN_TIMEOUT_SECONDS = 300
SCAN_POLL_SECONDS = 5

urllib3.disable_warnings(InsecureRequestWarning)


def build_proxies():
    proxy_url = (
        os.getenv(PROXY_ENV)
        or os.getenv("HTTPS_PROXY")
        or os.getenv("HTTP_PROXY")
    )
    if not proxy_url or not proxy_url.strip():
        return None
    proxy_url = proxy_url.strip()
    return {"http": proxy_url, "https": proxy_url}


def get_required_env(var_name):
    value = os.getenv(var_name)
    if value is None or not value.strip():
        raise RuntimeError(
            f"Missing required environment variable: {var_name}."
        )
    return value.strip()


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
    if not response.text:
        return {}
    return response.json()


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
        raise RuntimeError(
            "Unable to start workspace scan. Response did not include scan id."
        )
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

    raise TimeoutError(
        f"Scan did not complete within {SCAN_TIMEOUT_SECONDS} seconds."
    )


def get_scan_result(token, proxies, scan_id):
    result_url = f"https://api.powerbi.com/v1.0/myorg/admin/workspaces/scanResult/{scan_id}"
    payload = request_json("GET", result_url, token, proxies)
    if not payload:
        raise RuntimeError("Scan result payload is empty.")
    return payload


def safe_list(value):
    if isinstance(value, list):
        return value
    return []


def escape_m_string_literal(value):
    return str(value).replace('"', '""')


def parse_runtime_variable(raw_value):
    if raw_value is None:
        raise ValueError("Runtime variable cannot be empty.")

    name, separator, value = str(raw_value).partition("=")
    if not separator:
        raise ValueError(
            f"Invalid runtime variable '{raw_value}'. Expected format is name=value."
        )

    normalized_name = name.strip().lower()
    if not normalized_name:
        raise ValueError(
            f"Invalid runtime variable '{raw_value}'. Variable name cannot be empty."
        )

    return normalized_name, value


def build_runtime_variables(cli_vars=None, p_entity=None, p_environment=None):
    variables = {}

    for raw_var in cli_vars or []:
        name, value = parse_runtime_variable(raw_var)
        variables[name] = value

    if p_entity is not None:
        variables["p_entity"] = str(p_entity)
    if p_environment is not None:
        variables["p_environment"] = str(p_environment)

    return variables


def is_power_query_expression(expression):
    text = str(expression or "").strip()
    if not text:
        return False

    power_query_markers = (
        "let\n",
        "let\r\n",
        "table.",
        "text.",
        "number.",
        "datetime.",
        "date.",
        "time.",
        "duration.",
        "record.",
        "list.",
        "value.",
        "binary.",
        "teradata.database",
        "each ",
        "=>",
    )
    lowered = text.lower()
    return any(marker in lowered for marker in power_query_markers)


def substitute_m_identifiers(expression, runtime_variables):
    if not expression or not runtime_variables:
        return expression

    text = str(expression)
    current = []
    in_string = False
    index = 0

    while index < len(text):
        char = text[index]
        if char == '"':
            current.append(char)
            if in_string and index + 1 < len(text) and text[index + 1] == '"':
                current.append('"')
                index += 2
                continue
            in_string = not in_string
            index += 1
            continue

        if in_string:
            current.append(char)
            index += 1
            continue

        if char.isalpha() or char == "_":
            start = index
            while index < len(text) and (text[index].isalnum() or text[index] == "_"):
                index += 1
            token = text[start:index]
            replacement = runtime_variables.get(token.lower())
            if replacement is not None:
                current.append(f'"{escape_m_string_literal(replacement)}"')
            else:
                current.append(token)
            continue

        current.append(char)
        index += 1

    return "".join(current)


def substitute_runtime_variables(expression, runtime_variables):
    if not expression or not runtime_variables:
        return expression

    if not is_power_query_expression(expression):
        return expression

    return substitute_m_identifiers(expression, runtime_variables)


def apply_runtime_variables_to_dataset(dataset, runtime_variables):
    if not runtime_variables:
        return dataset

    dataset_copy = json.loads(json.dumps(dataset))
    for table in safe_list(dataset_copy.get("tables")):
        for source_entry in safe_list(table.get("source")):
            source_entry["expression"] = substitute_runtime_variables(
                source_entry.get("expression"),
                runtime_variables,
            )

        for column in safe_list(table.get("columns")):
            if column.get("expression") and is_power_query_expression(
                column.get("expression")
            ):
                column["expression"] = substitute_runtime_variables(
                    column.get("expression"),
                    runtime_variables,
                )

    return dataset_copy


def find_workspace(scan_result, workspace_id):
    workspaces = safe_list(scan_result.get("workspaces"))
    for workspace in workspaces:
        if workspace.get("id") == workspace_id:
            return workspace
    return None


def find_report(workspace_obj, report_id, report_name):
    reports = safe_list(workspace_obj.get("reports"))
    for report in reports:
        if report.get("id") == report_id:
            return report, "report_id"

    for report in reports:
        if (report.get("name") or "").strip().lower() == report_name.strip().lower():
            return report, "report_name"

    return None, "none"


def find_dataset(workspace_obj, dataset_id):
    for dataset in safe_list(workspace_obj.get("datasets")):
        if dataset.get("id") == dataset_id:
            return dataset
    return None


def infer_source_objects_from_expression(expression):
    objects = []
    if not expression:
        return objects

    step_lookup = parse_m_step_lookup(expression)
    schema_context = None

    schema_item_matches = re.findall(
        r'Schema\s*=\s*"([^"]+)"\s*,\s*Item\s*=\s*"([^"]+)"',
        expression,
        flags=re.IGNORECASE,
    )
    for schema_name, item_name in schema_item_matches:
        objects.append(
            {
                "object_name": f"{schema_name}.{item_name}",
                "object_type": "table_or_view",
                "source_object_resolution": "inferred",
            }
        )

    schema_only_match = re.search(
        r'Schema\s*=\s*("[^"]+"|[A-Za-z_][A-Za-z0-9_]*)',
        expression,
        flags=re.IGNORECASE,
    )
    if schema_only_match:
        raw_schema = schema_only_match.group(1)
        resolved_schema = resolve_m_reference(raw_schema, step_lookup)
        if resolved_schema:
            schema_context = resolved_schema
        elif raw_schema.startswith('"') and raw_schema.endswith('"'):
            schema_context = raw_schema.strip('"')
        else:
            schema_context = f"<{raw_schema}>"

    name_matches = re.findall(
        r'\[Name\s*=\s*"([^"]+)"\]',
        expression,
        flags=re.IGNORECASE,
    )
    for name_value in name_matches:
        object_name = f"{schema_context}.{name_value}" if schema_context else name_value
        objects.append(
            {
                "object_name": object_name,
                "object_type": "table_or_view",
                "source_object_resolution": "inferred",
            }
        )

    from_matches = re.findall(
        r'\bfrom\s+([\[\]\w\."]+)',
        expression,
        flags=re.IGNORECASE,
    )
    for object_name in from_matches:
        cleaned = object_name.strip("[]\"")
        if cleaned:
            objects.append(
                {
                    "object_name": cleaned,
                    "object_type": "table_or_view",
                    "source_object_resolution": "inferred",
                }
            )

    dedup = {}
    for obj in objects:
        dedup[(obj["object_name"], obj["object_type"])] = obj
    return list(dedup.values())


def parse_m_step_lookup(expression):
    steps = {}
    for step in parse_expression_transformations(expression):
        step_name = step.get("step_name")
        step_expression = step.get("expression")
        if step_name and step_expression:
            steps[step_name] = step_expression
    return steps


def split_m_concatenation(expression):
    parts = []
    current = []
    in_string = False
    index = 0

    while index < len(expression):
        char = expression[index]
        if char == '"':
            current.append(char)
            if in_string and index + 1 < len(expression) and expression[index + 1] == '"':
                current.append('"')
                index += 2
                continue
            in_string = not in_string
            index += 1
            continue

        if char == "&" and not in_string:
            part = "".join(current).strip()
            if part:
                parts.append(part)
            current = []
            index += 1
            continue

        current.append(char)
        index += 1

    tail = "".join(current).strip()
    if tail:
        parts.append(tail)
    return parts


def strip_wrapping_parentheses(expression):
    text = str(expression or "").strip()
    while text.startswith("(") and text.endswith(")"):
        depth = 0
        balanced = True
        in_string = False
        for index, char in enumerate(text):
            if char == '"':
                if in_string and index + 1 < len(text) and text[index + 1] == '"':
                    continue
                in_string = not in_string
            if in_string:
                continue
            if char == "(":
                depth += 1
            elif char == ")":
                depth -= 1
                if depth == 0 and index != len(text) - 1:
                    balanced = False
                    break
        if not balanced or depth != 0:
            break
        text = text[1:-1].strip()
    return text


def resolve_m_reference(token, step_lookup, seen=None):
    token = strip_wrapping_parentheses(token)
    if not token:
        return None

    if seen is None:
        seen = set()
    if token in seen:
        return None

    if token.startswith('"') and token.endswith('"'):
        return token[1:-1]

    lowered_match = re.fullmatch(r"Text\.Lower\((.+)\)", token, flags=re.IGNORECASE)
    if lowered_match:
        resolved = resolve_m_reference(lowered_match.group(1), step_lookup, seen)
        return resolved.lower() if resolved else None

    upper_match = re.fullmatch(r"Text\.Upper\((.+)\)", token, flags=re.IGNORECASE)
    if upper_match:
        resolved = resolve_m_reference(upper_match.group(1), step_lookup, seen)
        return resolved.upper() if resolved else None

    if "&" in token:
        pieces = []
        for part in split_m_concatenation(token):
            resolved = resolve_m_reference(part, step_lookup, seen)
            if resolved is None:
                resolved = normalize_urn_segment(part)
            pieces.append(resolved)
        return "".join(pieces)

    identifier_match = re.fullmatch(r'#"[^"]+"|[A-Za-z_][A-Za-z0-9_]*', token)
    if identifier_match:
        seen = set(seen)
        seen.add(token)
        if token in step_lookup:
            resolved = resolve_m_reference(step_lookup[token], step_lookup, seen)
            if resolved:
                return resolved
        return normalize_urn_segment(token)

    return None


def extract_table_source_objects(table):
    source_entries = safe_list(table.get("source"))
    objects = []
    for source_entry in source_entries:
        expression = source_entry.get("expression")
        objects.extend(infer_source_objects_from_expression(expression))

    if objects:
        return objects

    return [
        {
            "object_name": "unknown_source_object",
            "object_type": "unknown",
            "source_object_resolution": "unresolved",
        }
    ]


def parse_expression_transformations(expression):
    if not expression:
        return []

    transformations = []
    lines = expression.splitlines()

    for raw_line in lines:
        line = raw_line.strip()
        if not line or line.lower() in {"let", "in"}:
            continue

        if "=" not in line:
            continue

        left, right = line.split("=", 1)
        step_name = left.strip().strip(",")
        rhs = right.strip().rstrip(",")

        if not step_name or not rhs:
            continue

        op_match = re.search(r"([A-Za-z_][A-Za-z0-9_\.]*)\s*\(", rhs)
        operation = op_match.group(1) if op_match else "expression"

        transformations.append(
            {
                "step_name": step_name,
                "operation": operation,
                "expression": rhs,
                "expression_excerpt": rhs[:220],
            }
        )

    return transformations


def extract_table_transformations(table):
    all_transformations = []
    source_entries = safe_list(table.get("source"))
    for source_entry in source_entries:
        expression = source_entry.get("expression")
        all_transformations.extend(parse_expression_transformations(expression))
    return all_transformations


def extract_model_columns(table):
    model_columns = []
    for column in safe_list(table.get("columns")):
        model_columns.append(
            {
                "name": column.get("name"),
                "data_type": column.get("dataType"),
                "is_hidden": column.get("isHidden", False),
                "expression": column.get("expression"),
                "source_column": column.get("sourceColumn"),
                "column_type": column.get("type") or column.get("columnType"),
                "is_calculated": bool(column.get("expression")),
                "transformation_type": column.get("transformationType"),
            }
        )
    return model_columns


def parse_rename_columns(expression):
    mappings = []
    if not expression:
        return mappings
    matches = re.findall(r'\{"([^"]+)",\s*"([^"]+)"\}', expression)
    for src_col, dst_col in matches:
        mappings.append((src_col, dst_col))
    return mappings


def parse_add_column(expression):
    if not expression:
        return None, []
    new_col_match = re.search(r'Table\.AddColumn\([^,]+,\s*"([^"]+)"\s*,\s*each\s*(.+)\)$', expression)
    if not new_col_match:
        return None, []
    new_col = new_col_match.group(1)
    calc_expr = new_col_match.group(2)
    refs = re.findall(r'\[([^\]]+)\]', calc_expr)
    return new_col, refs


def parse_select_columns(expression):
    if not expression:
        return []
    columns_block_match = re.search(r'\{\s*("[^"]+"(?:\s*,\s*"[^"]+")*)\s*\}', expression)
    if not columns_block_match:
        return []
    return re.findall(r'"([^"]+)"', columns_block_match.group(1))


def build_column_lineage_for_table(model_columns, transformations):
    model_col_names = {col.get("name") for col in model_columns if col.get("name")}
    mapped_pairs = []

    for step in transformations:
        op = step.get("operation", "")
        expr = step.get("expression", "")
        step_name = step.get("step_name", "")

        if op.endswith("RenameColumns"):
            for src_col, dst_col in parse_rename_columns(expr):
                if dst_col in model_col_names:
                    mapped_pairs.append(
                        {
                            "source_column": src_col,
                            "model_column": dst_col,
                            "transformation_step": step_name,
                            "mapping_type": "rename",
                            "confidence": "inferred",
                        }
                    )

        if op.endswith("AddColumn"):
            new_col, refs = parse_add_column(expr)
            if new_col and new_col in model_col_names:
                if refs:
                    for ref_col in refs:
                        mapped_pairs.append(
                            {
                                "source_column": ref_col,
                                "model_column": new_col,
                                "transformation_step": step_name,
                                "mapping_type": "derived",
                                "confidence": "inferred",
                            }
                        )
                else:
                    mapped_pairs.append(
                        {
                            "source_column": "unknown_source_column",
                            "model_column": new_col,
                            "transformation_step": step_name,
                            "mapping_type": "derived",
                            "confidence": "unresolved",
                        }
                    )

        if op.endswith("SelectColumns"):
            selected = parse_select_columns(expr)
            for col_name in selected:
                if col_name in model_col_names:
                    mapped_pairs.append(
                        {
                            "source_column": col_name,
                            "model_column": col_name,
                            "transformation_step": step_name,
                            "mapping_type": "projection",
                            "confidence": "inferred",
                        }
                    )

    covered_model_columns = {item["model_column"] for item in mapped_pairs}
    for model_col in sorted(model_col_names):
        if model_col not in covered_model_columns:
            mapped_pairs.append(
                {
                    "source_column": "unknown_source_column",
                    "model_column": model_col,
                    "transformation_step": "unknown",
                    "mapping_type": "unresolved",
                    "confidence": "unresolved",
                }
            )

    return mapped_pairs


def build_connection_label(connection_details):
    if not isinstance(connection_details, dict):
        return "unknown_connection"

    preferred_keys = [
        "server",
        "database",
        "url",
        "path",
        "domain",
        "account",
        "host",
    ]
    values = []
    for key in preferred_keys:
        val = connection_details.get(key)
        if val:
            values.append(str(val))
    return " | ".join(values) if values else "unknown_connection"


def build_source_system_lookup(scan_result, workspace_obj):
    lookup = {}
    datasource_instances = safe_list(scan_result.get("datasourceInstances"))

    if not datasource_instances:
        datasource_instances = safe_list(workspace_obj.get("datasourceInstances"))

    for instance in datasource_instances:
        source_id = (
            instance.get("datasourceId")
            or instance.get("id")
            or f"unkeyed_{len(lookup) + 1}"
        )
        connection_details = instance.get("connectionDetails") or {}
        lookup[source_id] = {
            "id": source_id,
            "name": build_connection_label(connection_details),
            "type": instance.get("datasourceType", "unknown"),
            "connection_details": connection_details,
            "gateway_id": instance.get("gatewayId"),
        }
    return lookup


def map_dataset_sources(dataset, source_lookup):
    usages = safe_list(dataset.get("datasourceUsages"))
    mapped_sources = []

    for usage in usages:
        usage_id = usage.get("datasourceInstanceId")
        if usage_id and usage_id in source_lookup:
            mapped_sources.append(source_lookup[usage_id])

    if mapped_sources:
        return mapped_sources

    if len(source_lookup) == 1:
        return list(source_lookup.values())

    if len(source_lookup) > 1:
        return [
            {
                "id": "unresolved_source_system",
                "name": "multiple_sources_not_mapped_to_dataset",
                "type": "unknown",
                "connection_details": {},
            }
        ]

    return [
        {
            "id": "unknown_source_system",
            "name": "unknown_source_system",
            "type": "unknown",
            "connection_details": {},
        }
    ]


def sanitize_node_key(value):
    return re.sub(r"[^A-Za-z0-9_\-\.:]", "_", str(value))


def normalize_urn_segment(value):
    normalized = re.sub(r"[^a-z0-9]+", "_", str(value or "").strip().lower())
    normalized = re.sub(r"_+", "_", normalized).strip("_")
    return normalized or "unknown"


def normalize_container_segment(value, fallback):
    text = str(value or "").strip()
    if not text or (text.startswith("<") and text.endswith(">")):
        return fallback
    return normalize_urn_segment(text)


def build_fabric_table_urn(workspace_name, dataset_name, table_name):
    return (
        f"fabric://{normalize_urn_segment(workspace_name)}/"
        f"{normalize_urn_segment(dataset_name)}/{normalize_urn_segment(table_name)}"
    )


def build_fabric_dataset_urn(workspace_name, dataset_name):
    return (
        f"fabric://{normalize_urn_segment(workspace_name)}/datasets/"
        f"{normalize_urn_segment(dataset_name)}"
    )


def build_fabric_report_urn(workspace_name, report_name):
    return (
        f"fabric://{normalize_urn_segment(workspace_name)}/reports/"
        f"{normalize_urn_segment(report_name)}"
    )


def build_fabric_column_urn(workspace_name, dataset_name, table_name, column_name):
    return (
        f"{build_fabric_table_urn(workspace_name, dataset_name, table_name)}"
        f"#{normalize_urn_segment(column_name)}"
    )


def split_source_object_name(object_name):
    cleaned = str(object_name or "").strip().strip('[]"')
    if not cleaned or cleaned == "unknown_source_object":
        return None, None

    parts = [part.strip().strip('[]"') for part in cleaned.split(".") if part.strip()]
    if len(parts) >= 2:
        return parts[-2], parts[-1]
    if len(parts) == 1:
        return None, parts[0]
    return None, None


def map_source_type_to_urn_scheme(source_type):
    normalized = normalize_urn_segment(source_type).replace("_", "")
    if "teradata" in normalized:
        return "teradata"
    return normalized or "source"


def build_source_object_urn(source_system, source_object_name):
    connection_details = source_system.get("connection_details") or {}
    scheme = map_source_type_to_urn_scheme(source_system.get("type"))
    host = normalize_urn_segment(
        connection_details.get("server")
        or connection_details.get("host")
        or source_system.get("name")
        or "unknown_source"
    )
    schema_name, table_name = split_source_object_name(source_object_name)
    default_container = normalize_container_segment(
        connection_details.get("database")
        or connection_details.get("schema")
        or connection_details.get("path")
        or connection_details.get("url"),
        fallback="unknown_container",
    )
    container = normalize_container_segment(schema_name, fallback=default_container)
    object_segment = normalize_urn_segment(table_name or source_object_name or "unknown_object")

    return f"{scheme}://{host}/{container}/{object_segment}"


def validate_canonical_payload(payload):
    errors = []

    if not isinstance(payload, dict):
        return ["Payload must be a JSON object."]

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

    reports = payload.get("reports")
    if reports is not None and not isinstance(reports, list):
        errors.append("Top-level 'reports' must be an array when provided.")
        reports = []

    report_links = payload.get("reportLinks")
    if report_links is not None and not isinstance(report_links, list):
        errors.append("Top-level 'reportLinks' must be an array when provided.")
        report_links = []

    fabric_column_ids = set()
    node_names = set()
    for node_index, node in enumerate(nodes, start=1):
        if not isinstance(node, dict):
            errors.append(f"Node #{node_index} must be an object.")
            continue

        name = node.get("name")
        container = node.get("container")
        schema_name = node.get("schema_name")
        node_type = node.get("type")
        columns = node.get("columns")

        if not isinstance(name, str) or not name.strip():
            errors.append(f"Node #{node_index} has invalid 'name'.")
            continue

        if name in node_names:
            errors.append(f"Duplicate node name '{name}'.")
        node_names.add(name)

        if not isinstance(container, str) or not container.strip():
            errors.append(f"Node '{name}' has invalid 'container'.")
        if not isinstance(schema_name, str) or not schema_name.strip():
            errors.append(f"Node '{name}' has invalid 'schema_name'.")
        if node_type != "dataset_table":
            errors.append(f"Node '{name}' must have type 'dataset_table'.")
        if not isinstance(columns, list):
            errors.append(f"Node '{name}' has invalid 'columns'.")
            continue

        for column_index, column in enumerate(columns, start=1):
            if not isinstance(column, dict):
                errors.append(f"Column #{column_index} in node '{name}' must be an object.")
                continue

            column_name = column.get("name")
            if not isinstance(column_name, str) or not column_name.strip():
                errors.append(f"Column #{column_index} in node '{name}' has invalid 'name'.")
                continue

            fabric_column_ids.add(
                build_fabric_column_urn(workspace, container, name, column_name)
            )

            if "isCalculated" in column and not isinstance(column.get("isCalculated"), bool):
                errors.append(
                    f"Column '{name}.{column_name}' has non-boolean 'isCalculated'."
                )

            if column.get("isCalculated"):
                if not isinstance(column.get("expression"), str) or not column.get("expression").strip():
                    errors.append(
                        f"Calculated column '{name}.{column_name}' is missing 'expression'."
                    )
                if not isinstance(column.get("transformationType"), str) or not column.get("transformationType").strip():
                    errors.append(
                        f"Calculated column '{name}.{column_name}' is missing 'transformationType'."
                    )

    urn_pattern = re.compile(r"^[a-z0-9]+://[a-z0-9_\-\.]+/[a-z0-9_\-\.]+/[a-z0-9_\-\.]+#[a-z0-9_\-\.]+$")
    for edge_index, edge in enumerate(edges, start=1):
        if not isinstance(edge, dict):
            errors.append(f"Edge #{edge_index} must be an object.")
            continue

        source_id = edge.get("sourceColumnId")
        target_id = edge.get("targetColumnId")
        transformation_type = edge.get("transformationType")

        if not isinstance(source_id, str) or not urn_pattern.match(source_id):
            errors.append(f"Edge #{edge_index} has invalid 'sourceColumnId'.")
        if not isinstance(target_id, str) or not urn_pattern.match(target_id):
            errors.append(f"Edge #{edge_index} has invalid 'targetColumnId'.")
        if isinstance(target_id, str) and target_id not in fabric_column_ids:
            errors.append(
                f"Edge #{edge_index} targets unknown Fabric column URN '{target_id}'."
            )
        if not isinstance(transformation_type, str) or not transformation_type.strip():
            errors.append(f"Edge #{edge_index} has invalid 'transformationType'.")

    if isinstance(reports, list):
        report_ids = set()
        for report_index, report in enumerate(reports, start=1):
            if not isinstance(report, dict):
                errors.append(f"Report #{report_index} must be an object.")
                continue

            report_id = report.get("id")
            report_name = report.get("name")
            report_urn = report.get("urn")

            if not isinstance(report_id, str) or not report_id.strip():
                errors.append(f"Report #{report_index} has invalid 'id'.")
                continue
            if report_id in report_ids:
                errors.append(f"Duplicate report id '{report_id}'.")
            report_ids.add(report_id)

            if not isinstance(report_name, str) or not report_name.strip():
                errors.append(f"Report '{report_id}' has invalid 'name'.")
            if not isinstance(report_urn, str) or not report_urn.strip():
                errors.append(f"Report '{report_id}' has invalid 'urn'.")

    if isinstance(report_links, list):
        for link_index, link in enumerate(report_links, start=1):
            if not isinstance(link, dict):
                errors.append(f"Report link #{link_index} must be an object.")
                continue

            required_str_fields = [
                "reportId",
                "reportUrn",
                "datasetId",
                "datasetUrn",
                "relationship",
            ]
            for field_name in required_str_fields:
                field_value = link.get(field_name)
                if not isinstance(field_value, str) or not field_value.strip():
                    errors.append(
                        f"Report link #{link_index} has invalid '{field_name}'."
                    )

    return errors


def build_source_column_urn(source_system, source_object_name, column_name):
    return (
        f"{build_source_object_urn(source_system, source_object_name)}"
        f"#{normalize_urn_segment(column_name)}"
    )


def build_source_column_expression(source_object_name, column_name):
    _, table_name = split_source_object_name(source_object_name)
    source_name = table_name or source_object_name or "SOURCE"
    return f"{source_name}[{column_name}]"


def parse_dax_dependencies(current_table_name, expression):
    dependencies = []
    seen = set()
    if not expression:
        return dependencies

    pattern = re.compile(r"(?:'([^']+)'|([A-Za-z0-9_ ]+))?\[([^\]]+)\]")
    for match in pattern.finditer(expression):
        table_name = match.group(1) or match.group(2) or current_table_name
        column_name = match.group(3)
        if not column_name:
            continue

        key = (table_name.strip(), column_name.strip())
        if key in seen:
            continue
        seen.add(key)
        dependencies.append(
            {
                "table_name": table_name.strip(),
                "column_name": column_name.strip(),
            }
        )

    return dependencies


def infer_dax_transformation_type(current_table_name, dependencies):
    current_segment = normalize_urn_segment(current_table_name)
    for dependency in dependencies:
        dependency_segment = normalize_urn_segment(dependency.get("table_name"))
        if dependency_segment != current_segment:
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
        if operation.endswith("AddColumn"):
            return "PowerQuery_Derived"
        return "PowerQuery_Expression"
    if mapping_type == "unresolved":
        return "Unresolved"
    return "Direct"


def add_canonical_edge(edges, seen_edges, source_column_id, target_column_id, transformation_type, expression):
    edge_key = (
        source_column_id,
        target_column_id,
        transformation_type,
        expression or "",
    )
    if edge_key in seen_edges:
        return

    seen_edges.add(edge_key)
    edge_payload = {
        "sourceColumnId": source_column_id,
        "targetColumnId": target_column_id,
        "transformationType": transformation_type,
    }
    if expression:
        edge_payload["expression"] = expression
    edges.append(edge_payload)


def add_node(nodes, node_ids, node_id, node_type, name, properties):
    if node_id in node_ids:
        return
    node_ids.add(node_id)
    nodes.append(
        {
            "id": node_id,
            "type": node_type,
            "name": name,
            "properties": properties,
        }
    )


def add_edge(edges, edge_ids, source, target, relationship, properties):
    edge_id = f"{source}|{relationship}|{target}"
    if edge_id in edge_ids:
        return
    edge_ids.add(edge_id)
    edges.append(
        {
            "source": source,
            "target": target,
            "relationship": relationship,
            "properties": properties,
        }
    )


def build_nested_lineage(scan_result, workspace_obj, dataset, report, match_mode, requested):
    source_lookup = build_source_system_lookup(scan_result, workspace_obj)
    dataset_sources = map_dataset_sources(dataset, source_lookup)
    dataset_tables = safe_list(dataset.get("tables"))

    source_object_tables = defaultdict(lambda: defaultdict(dict))
    table_transformations = {}
    table_model_columns = {}
    table_column_lineage = {}
    total_transformation_steps = 0

    for table in dataset_tables:
        table_name = table.get("name", "unknown_model_table")
        table_objects = extract_table_source_objects(table)
        transformations = extract_table_transformations(table)
        model_columns = extract_model_columns(table)
        column_lineage = build_column_lineage_for_table(model_columns, transformations)
        table_transformations[table_name] = transformations
        table_model_columns[table_name] = model_columns
        table_column_lineage[table_name] = column_lineage
        total_transformation_steps += len(transformations)

        for source in dataset_sources:
            source_id = source["id"]
            for obj in table_objects:
                object_key = (
                    obj["object_name"],
                    obj["object_type"],
                    obj["source_object_resolution"],
                )
                source_object_tables[source_id][object_key][table_name] = transformations

    source_systems_payload = []
    for source in dataset_sources:
        source_id = source["id"]
        source_objects_payload = []
        for object_key, model_tables in source_object_tables[source_id].items():
            object_name, object_type, resolution = object_key
            dedup_table_names = sorted(model_tables.keys())
            source_objects_payload.append(
                {
                    "object_name": object_name,
                    "object_type": object_type,
                    "source_object_resolution": resolution,
                    "dataset_model_tables": [
                        {
                            "name": table_name,
                            "transformations": model_tables[table_name],
                            "transformation_count": len(model_tables[table_name]),
                            "model_columns": table_model_columns.get(table_name, []),
                            "column_lineage": table_column_lineage.get(table_name, []),
                        }
                        for table_name in dedup_table_names
                    ],
                }
            )

        if not source_objects_payload and dataset_tables:
            source_objects_payload.append(
                {
                    "object_name": "unknown_source_object",
                    "object_type": "unknown",
                    "source_object_resolution": "unresolved",
                    "dataset_model_tables": [
                        {
                            "name": tbl.get("name", "unknown_model_table"),
                            "transformations": table_transformations.get(
                                tbl.get("name", "unknown_model_table"), []
                            ),
                            "transformation_count": len(
                                table_transformations.get(
                                    tbl.get("name", "unknown_model_table"), []
                                )
                            ),
                            "model_columns": table_model_columns.get(
                                tbl.get("name", "unknown_model_table"), []
                            ),
                            "column_lineage": table_column_lineage.get(
                                tbl.get("name", "unknown_model_table"), []
                            ),
                        }
                        for tbl in dataset_tables
                    ],
                }
            )

        source_systems_payload.append(
            {
                "source_system": source,
                "source_objects": source_objects_payload,
            }
        )

    return {
        "generated_at_utc": datetime.now(timezone.utc).isoformat(),
        "workspace": {
            "id": workspace_obj.get("id"),
            "name": workspace_obj.get("name"),
        },
        "report": {
            "id": report.get("id"),
            "name": report.get("name"),
            "dataset_id": report.get("datasetId"),
            "web_url": report.get("webUrl"),
            "matched_by": match_mode,
            "requested": {
                "report_id": requested.get("report_id"),
                "report_name": requested.get("report_name"),
            },
        },
        "dataset": {
            "id": dataset.get("id"),
            "name": dataset.get("name"),
            "model_table_count": len(dataset_tables),
        },
        "lineage": {
            "source_systems": source_systems_payload,
        },
        "transformations": {
            "by_dataset_model_table": [
                {
                    "table_name": table_name,
                    "transformation_count": len(steps),
                    "steps": steps,
                }
                for table_name, steps in sorted(table_transformations.items())
            ],
        },
        "stats": {
            "source_system_count": len(source_systems_payload),
            "dataset_model_table_count": len(dataset_tables),
            "dataset_model_column_count": sum(
                len(cols) for cols in table_model_columns.values()
            ),
            "transformation_step_count": total_transformation_steps,
            "report_count": 1,
        },
    }


def build_canonical_fabric_payload(nested_payload, dataset_tables):
    workspace_name = nested_payload.get("workspace", {}).get("name") or "unknown_workspace"
    dataset_name = nested_payload.get("dataset", {}).get("name") or "unknown_dataset"
    dataset_id = nested_payload.get("dataset", {}).get("id") or "unknown_dataset_id"
    report_info = nested_payload.get("report", {})
    source_systems = safe_list(nested_payload.get("lineage", {}).get("source_systems"))

    transformation_lookup = {
        item.get("table_name"): {
            step.get("step_name"): step for step in safe_list(item.get("steps"))
        }
        for item in safe_list(
            nested_payload.get("transformations", {}).get("by_dataset_model_table")
        )
        if item.get("table_name")
    }

    raw_table_lookup = {
        table.get("name"): table for table in safe_list(dataset_tables) if table.get("name")
    }
    nodes = []
    edges = []
    seen_edges = set()

    node_columns_by_table = {}
    node_column_order = {}

    for table_name, raw_table in sorted(raw_table_lookup.items()):
        columns = []
        columns_by_name = {}
        column_order = []

        for raw_column in extract_model_columns(raw_table):
            column_name = raw_column.get("name")
            if not column_name:
                continue

            column_payload = {
                "name": column_name,
                "dataType": raw_column.get("data_type"),
            }
            if raw_column.get("is_calculated") and raw_column.get("expression"):
                dependencies = parse_dax_dependencies(
                    table_name,
                    raw_column.get("expression"),
                )
                column_payload["isCalculated"] = True
                column_payload["expression"] = raw_column.get("expression")
                column_payload["transformationType"] = (
                    raw_column.get("transformation_type")
                    or infer_dax_transformation_type(table_name, dependencies)
                )

            columns.append(column_payload)
            columns_by_name[column_name] = column_payload
            column_order.append(column_name)

        node_columns_by_table[table_name] = columns_by_name
        node_column_order[table_name] = column_order
        nodes.append(
            {
                "name": table_name,
                "container": normalize_urn_segment(dataset_name),
                "schema_name": "Model",
                "type": "dataset_table",
                "columns": columns,
            }
        )

    for source_system_entry in source_systems:
        source_system = source_system_entry.get("source_system", {})
        for source_object in safe_list(source_system_entry.get("source_objects")):
            source_object_name = source_object.get("object_name")
            for model_table in safe_list(source_object.get("dataset_model_tables")):
                table_name = model_table.get("name")
                if not table_name:
                    continue

                columns_by_name = node_columns_by_table.setdefault(table_name, {})
                column_order = node_column_order.setdefault(table_name, [])
                model_columns = safe_list(model_table.get("model_columns"))
                for model_column in model_columns:
                    column_name = model_column.get("name")
                    if not column_name or column_name in columns_by_name:
                        continue

                    columns_by_name[column_name] = {
                        "name": column_name,
                        "dataType": model_column.get("data_type"),
                    }
                    column_order.append(column_name)

                step_lookup = transformation_lookup.get(table_name, {})
                for col_map in safe_list(model_table.get("column_lineage")):
                    model_column_name = col_map.get("model_column")
                    if not model_column_name:
                        continue

                    if model_column_name not in columns_by_name:
                        columns_by_name[model_column_name] = {
                            "name": model_column_name,
                            "dataType": None,
                        }
                        column_order.append(model_column_name)

                    step_name = col_map.get("transformation_step")
                    transformation_step = step_lookup.get(step_name, {})
                    transformation_type = infer_mapping_transformation_type(
                        col_map,
                        transformation_step,
                    )
                    if transformation_type == "PowerQuery_Derived":
                        column_entry = columns_by_name[model_column_name]
                        column_entry.setdefault("isCalculated", True)
                        if transformation_step.get("expression"):
                            column_entry.setdefault(
                                "expression",
                                transformation_step.get("expression"),
                            )
                        column_entry.setdefault(
                            "transformationType",
                            transformation_type,
                        )

                    source_column_name = col_map.get("source_column") or "unknown_source_column"
                    if source_column_name == "unknown_source_column":
                        continue

                    add_canonical_edge(
                        edges,
                        seen_edges,
                        build_source_column_urn(
                            source_system,
                            source_object_name,
                            source_column_name,
                        ),
                        build_fabric_column_urn(
                            workspace_name,
                            dataset_name,
                            table_name,
                            model_column_name,
                        ),
                        transformation_type,
                        transformation_step.get("expression")
                        or build_source_column_expression(
                            source_object_name,
                            source_column_name,
                        ),
                    )

    for table_name, raw_table in sorted(raw_table_lookup.items()):
        for raw_column in extract_model_columns(raw_table):
            expression = raw_column.get("expression")
            target_column_name = raw_column.get("name")
            if not expression or not target_column_name:
                continue

            dependencies = parse_dax_dependencies(table_name, expression)
            transformation_type = (
                raw_column.get("transformation_type")
                or infer_dax_transformation_type(table_name, dependencies)
            )
            target_column_urn = build_fabric_column_urn(
                workspace_name,
                dataset_name,
                table_name,
                target_column_name,
            )
            for dependency in dependencies:
                add_canonical_edge(
                    edges,
                    seen_edges,
                    build_fabric_column_urn(
                        workspace_name,
                        dataset_name,
                        dependency.get("table_name"),
                        dependency.get("column_name"),
                    ),
                    target_column_urn,
                    transformation_type,
                    expression,
                )

    for node in nodes:
        table_name = node.get("name")
        columns_by_name = node_columns_by_table.get(table_name, {})
        column_order = node_column_order.get(table_name, [])
        node["columns"] = [columns_by_name[column_name] for column_name in column_order]

    nodes.sort(key=lambda item: normalize_urn_segment(item.get("name")))
    edges.sort(
        key=lambda item: (
            item.get("sourceColumnId", ""),
            item.get("targetColumnId", ""),
            item.get("transformationType", ""),
        )
    )

    reports = []
    report_links = []

    report_id = report_info.get("id")
    report_name = report_info.get("name")
    if report_id and report_name:
        report_urn = build_fabric_report_urn(workspace_name, report_name)
        dataset_urn = build_fabric_dataset_urn(workspace_name, dataset_name)

        reports.append(
            {
                "id": report_id,
                "name": report_name,
                "urn": report_urn,
                "datasetId": report_info.get("dataset_id") or dataset_id,
                "datasetUrn": dataset_urn,
                "webUrl": report_info.get("web_url"),
                "matchedBy": report_info.get("matched_by"),
                "requested": report_info.get("requested"),
            }
        )
        report_links.append(
            {
                "reportId": report_id,
                "reportUrn": report_urn,
                "datasetId": report_info.get("dataset_id") or dataset_id,
                "datasetUrn": dataset_urn,
                "relationship": "consumes_dataset",
            }
        )

    return {
        "workspace": workspace_name,
        "nodes": nodes,
        "edges": edges,
        "reports": reports,
        "reportLinks": report_links,
    }


def build_graph_lineage(nested_payload):
    workspace = nested_payload.get("workspace", {})
    report = nested_payload.get("report", {})
    dataset = nested_payload.get("dataset", {})
    source_systems = safe_list(
        nested_payload.get("lineage", {}).get("source_systems")
    )

    nodes = []
    edges = []
    node_ids = set()
    edge_ids = set()

    workspace_node_id = f"workspace:{sanitize_node_key(workspace.get('id', 'unknown'))}"
    dataset_node_id = f"dataset:{sanitize_node_key(dataset.get('id', 'unknown'))}"
    report_node_id = f"report:{sanitize_node_key(report.get('id', 'unknown'))}"

    add_node(nodes, node_ids, workspace_node_id, "workspace", workspace.get("name"), workspace)
    add_node(nodes, node_ids, dataset_node_id, "dataset", dataset.get("name"), dataset)
    add_node(nodes, node_ids, report_node_id, "report", report.get("name"), report)

    add_edge(edges, edge_ids, workspace_node_id, dataset_node_id, "contains_dataset", {})
    add_edge(edges, edge_ids, workspace_node_id, report_node_id, "contains_report", {})
    add_edge(edges, edge_ids, dataset_node_id, report_node_id, "feeds_report", {})

    for source_system_entry in source_systems:
        source_system = source_system_entry.get("source_system", {})
        source_system_id = source_system.get("id", "unknown_source_system")
        source_system_node_id = f"source_system:{sanitize_node_key(source_system_id)}"

        add_node(
            nodes,
            node_ids,
            source_system_node_id,
            "source_system",
            source_system.get("name"),
            source_system,
        )

        source_objects = safe_list(source_system_entry.get("source_objects"))
        for source_object in source_objects:
            source_object_name = source_object.get("object_name", "unknown_source_object")
            source_object_node_id = (
                f"source_object:{sanitize_node_key(source_system_id)}:"
                f"{sanitize_node_key(source_object_name)}"
            )

            add_node(
                nodes,
                node_ids,
                source_object_node_id,
                "source_object",
                source_object_name,
                {
                    "object_type": source_object.get("object_type"),
                    "source_object_resolution": source_object.get(
                        "source_object_resolution"
                    ),
                },
            )
            add_edge(
                edges,
                edge_ids,
                source_system_node_id,
                source_object_node_id,
                "contains_source_object",
                {},
            )

            model_tables = safe_list(source_object.get("dataset_model_tables"))
            for model_table in model_tables:
                model_table_name = model_table.get("name", "unknown_model_table")
                model_table_node_id = (
                    f"model_table:{sanitize_node_key(dataset.get('id', 'unknown'))}:"
                    f"{sanitize_node_key(model_table_name)}"
                )

                add_node(
                    nodes,
                    node_ids,
                    model_table_node_id,
                    "dataset_model_table",
                    model_table_name,
                    {"dataset_id": dataset.get("id")},
                )
                add_edge(
                    edges,
                    edge_ids,
                    model_table_node_id,
                    report_node_id,
                    "feeds_report",
                    {},
                )

                model_columns = safe_list(model_table.get("model_columns"))
                for model_column in model_columns:
                    model_col_name = model_column.get("name") or "unknown_model_column"
                    model_col_node_id = (
                        f"model_column:{sanitize_node_key(dataset.get('id', 'unknown'))}:"
                        f"{sanitize_node_key(model_table_name)}:{sanitize_node_key(model_col_name)}"
                    )

                    add_node(
                        nodes,
                        node_ids,
                        model_col_node_id,
                        "model_column",
                        model_col_name,
                        {
                            "table_name": model_table_name,
                            "dataset_id": dataset.get("id"),
                            "data_type": model_column.get("data_type"),
                            "is_hidden": model_column.get("is_hidden", False),
                        },
                    )
                    add_edge(
                        edges,
                        edge_ids,
                        model_table_node_id,
                        model_col_node_id,
                        "contains_model_column",
                        {},
                    )
                    add_edge(
                        edges,
                        edge_ids,
                        model_col_node_id,
                        report_node_id,
                        "available_to_report",
                        {},
                    )

                column_lineage = safe_list(model_table.get("column_lineage"))
                for col_map in column_lineage:
                    model_col = col_map.get("model_column") or "unknown_model_column"
                    source_col = col_map.get("source_column") or "unknown_source_column"
                    model_col_node_id = (
                        f"model_column:{sanitize_node_key(dataset.get('id', 'unknown'))}:"
                        f"{sanitize_node_key(model_table_name)}:{sanitize_node_key(model_col)}"
                    )
                    source_col_node_id = (
                        f"source_column:{sanitize_node_key(source_system_id)}:"
                        f"{sanitize_node_key(source_object_name)}:{sanitize_node_key(source_col)}"
                    )

                    add_node(
                        nodes,
                        node_ids,
                        source_col_node_id,
                        "source_column",
                        source_col,
                        {
                            "source_object": source_object_name,
                            "source_system_id": source_system_id,
                        },
                    )
                    add_edge(
                        edges,
                        edge_ids,
                        source_object_node_id,
                        source_col_node_id,
                        "contains_source_column",
                        {},
                    )
                    add_edge(
                        edges,
                        edge_ids,
                        source_col_node_id,
                        model_col_node_id,
                        "maps_to_model_column",
                        {
                            "mapping_type": col_map.get("mapping_type"),
                            "transformation_step": col_map.get("transformation_step"),
                            "confidence": col_map.get("confidence"),
                        },
                    )

                transformations = safe_list(model_table.get("transformations"))
                if not transformations:
                    add_edge(
                        edges,
                        edge_ids,
                        source_object_node_id,
                        model_table_node_id,
                        "loads_to_model_table",
                        {},
                    )
                    continue

                for index, transformation in enumerate(transformations, start=1):
                    step_name = transformation.get("step_name", f"step_{index}")
                    operation = transformation.get("operation", "expression")
                    transform_node_id = (
                        f"transformation:{sanitize_node_key(dataset.get('id', 'unknown'))}:"
                        f"{sanitize_node_key(model_table_name)}:{index}"
                    )

                    add_node(
                        nodes,
                        node_ids,
                        transform_node_id,
                        "transformation",
                        f"{step_name}",
                        {
                            "operation": operation,
                            "expression_excerpt": transformation.get(
                                "expression_excerpt"
                            ),
                            "model_table": model_table_name,
                        },
                    )
                    add_edge(
                        edges,
                        edge_ids,
                        source_object_node_id,
                        transform_node_id,
                        "applies_transformation",
                        {},
                    )
                    add_edge(
                        edges,
                        edge_ids,
                        transform_node_id,
                        model_table_node_id,
                        "outputs_model_table",
                        {},
                    )

    return {
        "generated_at_utc": nested_payload.get("generated_at_utc"),
        "workspace": workspace,
        "dataset": dataset,
        "report": report,
        "nodes": nodes,
        "edges": edges,
        "stats": {
            "node_count": len(nodes),
            "edge_count": len(edges),
            "source_system_count": nested_payload.get("stats", {}).get(
                "source_system_count", 0
            ),
            "dataset_model_table_count": nested_payload.get("stats", {}).get(
                "dataset_model_table_count", 0
            ),
            "dataset_model_column_count": nested_payload.get("stats", {}).get(
                "dataset_model_column_count", 0
            ),
            "transformation_step_count": nested_payload.get("stats", {}).get(
                "transformation_step_count", 0
            ),
            "report_count": 1,
        },
    }


def verify_report_dataset_binding(token, proxies, workspace_id, report_id, expected_dataset_id):
    report_url = GROUP_REPORT_URL_TEMPLATE.format(
        workspace_id=workspace_id, report_id=report_id
    )

    try:
        report_payload = request_json("GET", report_url, token, proxies)
    except requests.HTTPError as exc:
        print(
            "Warning: Could not validate report-dataset binding with group report endpoint: "
            f"{exc}"
        )
        return

    actual_dataset_id = report_payload.get("datasetId")
    if actual_dataset_id and actual_dataset_id != expected_dataset_id:
        raise RuntimeError(
            "Dataset mismatch between scan result and group report endpoint. "
            f"Expected {expected_dataset_id}, but got {actual_dataset_id}."
        )


def parse_args():
    parser = argparse.ArgumentParser(
        description=(
            "Generate canonical Fabric lineage JSON for one Power BI report."
        )
    )
    parser.add_argument("--workspace-id", required=True)
    parser.add_argument("--report-id", required=True)
    parser.add_argument("--report-name", required=True)
    parser.add_argument("--output", default="lineage_output.json")
    parser.add_argument(
        "--var",
        action="append",
        default=[],
        metavar="name=value",
        help="Runtime variable to substitute into expressions. Repeat as needed.",
    )
    parser.add_argument("--p-entity")
    parser.add_argument("--p-environment")
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
        token = get_access_token(proxies, tenant_id, client_id, client_secret)
        scan_id = start_workspace_scan(token, proxies, args.workspace_id)
        wait_for_scan_completion(token, proxies, scan_id)
        scan_result = get_scan_result(token, proxies, scan_id)

        workspace_obj = find_workspace(scan_result, args.workspace_id)
        if not workspace_obj:
            raise RuntimeError(
                "Target workspace was not found in scan result. "
                "Ensure workspace ID is correct and scanner permissions are granted."
            )

        report, match_mode = find_report(workspace_obj, args.report_id, args.report_name)
        if not report:
            raise RuntimeError(
                "Target report was not found in scanned workspace. "
                f"Report ID: {args.report_id}, Report Name: {args.report_name}"
            )

        if match_mode == "report_name":
            print(
                "Warning: Requested report ID was not found in scanner payload. "
                f"Using exact report-name match: {args.report_name}"
            )

        dataset_id = report.get("datasetId")
        if not dataset_id:
            raise RuntimeError("Target report does not have a datasetId.")

        dataset = find_dataset(workspace_obj, dataset_id)
        if not dataset:
            raise RuntimeError(
                "Dataset referenced by report was not found in scan result. "
                f"Dataset ID: {dataset_id}"
            )
        dataset = apply_runtime_variables_to_dataset(dataset, runtime_variables)

        verify_report_dataset_binding(
            token, proxies, args.workspace_id, report.get("id"), dataset_id
        )

        lineage_payload = build_nested_lineage(
            scan_result,
            workspace_obj,
            dataset,
            report,
            match_mode,
            {"report_id": args.report_id, "report_name": args.report_name},
        )

        canonical_payload = build_canonical_fabric_payload(
            lineage_payload,
            dataset.get("tables"),
        )
        validation_errors = validate_canonical_payload(canonical_payload)
        if validation_errors:
            raise RuntimeError(
                "Canonical lineage payload failed validation: "
                + " | ".join(validation_errors)
            )

        with open(args.output, "w", encoding="utf-8") as output_file:
            json.dump(canonical_payload, output_file, indent=2)

        print(f"Canonical Fabric lineage JSON written to: {args.output}")
        print("Canonical payload validation: ok")
        if runtime_variables:
            print(
                "Runtime variables applied: "
                + ", ".join(
                    f"{key}={value}" for key, value in sorted(runtime_variables.items())
                )
            )
        print(
            "Summary: "
            f"workspace={workspace_obj.get('name')} | "
            f"report={report.get('name')} | "
            f"dataset={dataset.get('name')} | "
            f"fabricNodes={len(canonical_payload['nodes'])} | "
            f"fabricEdges={len(canonical_payload['edges'])} | "
            f"sourceSystems={lineage_payload['stats']['source_system_count']} | "
            f"modelTables={lineage_payload['stats']['dataset_model_table_count']} | "
            f"transformations={lineage_payload['stats']['transformation_step_count']}"
        )
        return 0

    except requests.HTTPError as exc:
        status_code = exc.response.status_code if exc.response else "unknown"
        response_text = exc.response.text if exc.response else "no response body"
        print(f"HTTP error ({status_code}): {response_text}")
        return 1
    except Exception as exc:  # noqa: BLE001
        print(f"Error: {exc}")
        return 1


if __name__ == "__main__":
    sys.exit(main())
