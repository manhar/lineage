# Multi-Scanner Ingestion API Reference

The Lineage service provides REST endpoints to ingest metadata from multiple automated scanners into the canonical SQLite graph engine:
1. **Teradata SQL Scanner** (`POST /api/ingest/teradata`): Ingests DDL, BTEQ scripts, views, and ELT insert-select queries.
2. **Azure Fabric / Power BI Scanner** (`POST /api/ingest/fabric`): Ingests Power BI semantic models, M-queries, DAX calculations, and report visual bindings.

Both scanners emit canonical Uniform Resource Names (URNs) so their graphs **automatically stitch together** at the Teradata $\rightarrow$ Power BI boundary.

---

## 1. Canonical URN Structure

Every entity and column in the lineage graph is uniquely identified by a URN:

| Entity Type | Format | Example |
| :--- | :--- | :--- |
| **Teradata Table/View** | `teradata://<server>/<database>/<table>` | `teradata://td_prod/edw_core/fact_transaction_summary` |
| **Teradata Column** | `teradata://<server>/<database>/<table>#<column>` | `teradata://td_prod/edw_core/fact_transaction_summary#net_paid_amount` |
| **Fabric Dataset Table** | `fabric://<workspace>/<dataset>/<table>` | `fabric://ws_finance/sales_dataset/fact_sales` |
| **Fabric Column** | `fabric://<workspace>/<dataset>/<table>#<column>` | `fabric://ws_finance/sales_dataset/fact_sales#net_paid_amount` |
| **Fabric Report Visual** | `fabric://<workspace>/<report>/<visual_view>` | `fabric://ws_finance/exec_dashboard/executive_kpi_summary` |

---

## 2. Ingesting Teradata SQL Lineage

### Endpoint
`POST http://localhost:8000/api/ingest/teradata`  
**Content-Type**: `application/json`

### Payload Schema
```json
{
  "server": "td_prod",
  "defaultDatabase": "EDW_CORE",
  "nodes": [
    {
      "name": "FACT_TRANSACTION_SUMMARY",
      "container": "EDW_CORE",
      "schema_name": "Core",
      "type": "dataset_table",
      "columns": [
        {
          "name": "transaction_id",
          "dataType": "Int64"
        },
        {
          "name": "net_paid_amount",
          "dataType": "Decimal",
          "isCalculated": true,
          "expression": "ROUND((sale_amt - discount_amt) * (1.0 + tax_rate), 2)",
          "transformationType": "SQL_Multi_Derivation"
        }
      ]
    }
  ],
  "edges": [
    {
      "sourceColumnId": "teradata://td_prod/stg_sales/stg_sales_txn#sale_amt",
      "targetColumnId": "teradata://td_prod/edw_core/fact_transaction_summary#net_paid_amount",
      "transformationType": "SQL_Multi_Derivation",
      "expression": "ROUND((sale_amt - discount_amt) * (1.0 + tax_rate), 2)"
    },
    {
      "sourceColumnId": "teradata://td_prod/stg_sales/stg_sales_txn#discount_amt",
      "targetColumnId": "teradata://td_prod/edw_core/fact_transaction_summary#net_paid_amount",
      "transformationType": "SQL_Multi_Derivation",
      "expression": "ROUND((sale_amt - discount_amt) * (1.0 + tax_rate), 2)"
    },
    {
      "sourceColumnId": "teradata://td_prod/stg_sales/stg_sales_txn#tax_rate",
      "targetColumnId": "teradata://td_prod/edw_core/fact_transaction_summary#net_paid_amount",
      "transformationType": "SQL_Multi_Derivation",
      "expression": "ROUND((sale_amt - discount_amt) * (1.0 + tax_rate), 2)"
    }
  ]
}
```

### Example: Using cURL
```bash
curl -X POST http://localhost:8000/api/ingest/teradata \
  -H "Content-Type: application/json" \
  -d '{
    "server": "td_prod",
    "defaultDatabase": "EDW_CORE",
    "nodes": [
      {
        "name": "FACT_TRANSACTION_SUMMARY",
        "container": "EDW_CORE",
        "schema_name": "Core",
        "type": "dataset_table",
        "columns": [
          { "name": "transaction_id", "dataType": "Int64" },
          { "name": "net_paid_amount", "dataType": "Decimal", "isCalculated": true, "expression": "ROUND((sale_amt - discount_amt) * (1.0 + tax_rate), 2)", "transformationType": "SQL_Multi_Derivation" }
        ]
      }
    ],
    "edges": [
      {
        "sourceColumnId": "teradata://td_prod/stg_sales/stg_sales_txn#sale_amt",
        "targetColumnId": "teradata://td_prod/edw_core/fact_transaction_summary#net_paid_amount",
        "transformationType": "SQL_Multi_Derivation",
        "expression": "ROUND((sale_amt - discount_amt) * (1.0 + tax_rate), 2)"
      },
      {
        "sourceColumnId": "teradata://td_prod/stg_sales/stg_sales_txn#discount_amt",
        "targetColumnId": "teradata://td_prod/edw_core/fact_transaction_summary#net_paid_amount",
        "transformationType": "SQL_Multi_Derivation",
        "expression": "ROUND((sale_amt - discount_amt) * (1.0 + tax_rate), 2)"
      },
      {
        "sourceColumnId": "teradata://td_prod/stg_sales/stg_sales_txn#tax_rate",
        "targetColumnId": "teradata://td_prod/edw_core/fact_transaction_summary#net_paid_amount",
        "transformationType": "SQL_Multi_Derivation",
        "expression": "ROUND((sale_amt - discount_amt) * (1.0 + tax_rate), 2)"
      }
    ]
  }'
```

### Example: Using Python (`requests` or `urllib`)
```python
import requests

payload = {
    "server": "td_prod",
    "defaultDatabase": "EDW_CORE",
    "nodes": [
        {
            "name": "FACT_TRANSACTION_SUMMARY",
            "container": "EDW_CORE",
            "schema_name": "Core",
            "type": "dataset_table",
            "columns": [
                {"name": "transaction_id", "dataType": "Int64"},
                {
                    "name": "net_paid_amount",
                    "dataType": "Decimal",
                    "isCalculated": True,
                    "expression": "ROUND((sale_amt - discount_amt) * (1.0 + tax_rate), 2)",
                    "transformationType": "SQL_Multi_Derivation"
                }
            ]
        }
    ],
    "edges": [
        {
            "sourceColumnId": "teradata://td_prod/stg_sales/stg_sales_txn#sale_amt",
            "targetColumnId": "teradata://td_prod/edw_core/fact_transaction_summary#net_paid_amount",
            "transformationType": "SQL_Multi_Derivation",
            "expression": "ROUND((sale_amt - discount_amt) * (1.0 + tax_rate), 2)"
        },
        {
            "sourceColumnId": "teradata://td_prod/stg_sales/stg_sales_txn#discount_amt",
            "targetColumnId": "teradata://td_prod/edw_core/fact_transaction_summary#net_paid_amount",
            "transformationType": "SQL_Multi_Derivation",
            "expression": "ROUND((sale_amt - discount_amt) * (1.0 + tax_rate), 2)"
        },
        {
            "sourceColumnId": "teradata://td_prod/stg_sales/stg_sales_txn#tax_rate",
            "targetColumnId": "teradata://td_prod/edw_core/fact_transaction_summary#net_paid_amount",
            "transformationType": "SQL_Multi_Derivation",
            "expression": "ROUND((sale_amt - discount_amt) * (1.0 + tax_rate), 2)"
        }
    ]
}

response = requests.post("http://localhost:8000/api/ingest/teradata", json=payload)
print(response.json())
```

---

## 3. Ingesting Azure Fabric / Power BI Lineage (Bridging to Teradata)

The Fabric scanner extracts Power BI datasets, tables, DAX measures, and report visual bindings. It creates the **bridge edge** by referencing the Teradata Core URN as the `sourceColumnId`.

### Endpoint
`POST http://localhost:8000/api/ingest/fabric`  
**Content-Type**: `application/json`

### Payload Schema
```json
{
  "workspace": "Finance & Sales Analytics",
  "nodes": [
    {
      "name": "Fact_Sales",
      "container": "sales_dataset",
      "schema_name": "Model",
      "type": "dataset_table",
      "columns": [
        {
          "name": "Transaction_ID",
          "dataType": "Int64"
        },
        {
          "name": "Net_Paid_Amount",
          "dataType": "Decimal"
        },
        {
          "name": "Risk_Adjusted_Revenue",
          "dataType": "Decimal",
          "isCalculated": true,
          "expression": "Fact_Sales[Net_Paid_Amount] * IF(RELATED(Dim_Customer[Risk_Tier]) = \"Tier 3 - Subprime\", 0.85, 1.0)",
          "transformationType": "DAX_Cross_Table"
        }
      ]
    }
  ],
  "edges": [
    {
      "sourceColumnId": "teradata://td_prod/edw_core/fact_transaction_summary#net_paid_amount",
      "targetColumnId": "fabric://finance___sales_analytics/sales_dataset/fact_sales#net_paid_amount",
      "transformationType": "Direct",
      "expression": "FACT_TRANSACTION_SUMMARY[net_paid_amount]"
    },
    {
      "sourceColumnId": "fabric://finance___sales_analytics/sales_dataset/fact_sales#net_paid_amount",
      "targetColumnId": "fabric://finance___sales_analytics/sales_dataset/fact_sales#risk_adjusted_revenue",
      "transformationType": "DAX_Cross_Table",
      "expression": "Fact_Sales[Net_Paid_Amount] * IF(RELATED(Dim_Customer[Risk_Tier]) = \"Tier 3 - Subprime\", 0.85, 1.0)"
    },
    {
      "sourceColumnId": "fabric://finance___sales_analytics/sales_dataset/dim_customer#risk_tier",
      "targetColumnId": "fabric://finance___sales_analytics/sales_dataset/fact_sales#risk_adjusted_revenue",
      "transformationType": "DAX_Cross_Table",
      "expression": "Fact_Sales[Net_Paid_Amount] * IF(RELATED(Dim_Customer[Risk_Tier]) = \"Tier 3 - Subprime\", 0.85, 1.0)"
    }
  ]
}
```

### Example: Using cURL
```bash
curl -X POST http://localhost:8000/api/ingest/fabric \
  -H "Content-Type: application/json" \
  -d '{
    "workspace": "Finance & Sales Analytics",
    "nodes": [
      {
        "name": "Fact_Sales",
        "container": "sales_dataset",
        "schema_name": "Model",
        "type": "dataset_table",
        "columns": [
          { "name": "Transaction_ID", "dataType": "Int64" },
          { "name": "Net_Paid_Amount", "dataType": "Decimal" },
          { 
            "name": "Risk_Adjusted_Revenue", 
            "dataType": "Decimal", 
            "isCalculated": true, 
            "expression": "Fact_Sales[Net_Paid_Amount] * IF(RELATED(Dim_Customer[Risk_Tier]) = \"Tier 3 - Subprime\", 0.85, 1.0)",
            "transformationType": "DAX_Cross_Table"
          }
        ]
      }
    ],
    "edges": [
      {
        "sourceColumnId": "teradata://td_prod/edw_core/fact_transaction_summary#net_paid_amount",
        "targetColumnId": "fabric://finance___sales_analytics/sales_dataset/fact_sales#net_paid_amount",
        "transformationType": "Direct",
        "expression": "FACT_TRANSACTION_SUMMARY[net_paid_amount]"
      },
      {
        "sourceColumnId": "fabric://finance___sales_analytics/sales_dataset/fact_sales#net_paid_amount",
        "targetColumnId": "fabric://finance___sales_analytics/sales_dataset/fact_sales#risk_adjusted_revenue",
        "transformationType": "DAX_Cross_Table",
        "expression": "Fact_Sales[Net_Paid_Amount] * IF(RELATED(Dim_Customer[Risk_Tier]) = \"Tier 3 - Subprime\", 0.85, 1.0)"
      },
      {
        "sourceColumnId": "fabric://finance___sales_analytics/sales_dataset/dim_customer#risk_tier",
        "targetColumnId": "fabric://finance___sales_analytics/sales_dataset/fact_sales#risk_adjusted_revenue",
        "transformationType": "DAX_Cross_Table",
        "expression": "Fact_Sales[Net_Paid_Amount] * IF(RELATED(Dim_Customer[Risk_Tier]) = \"Tier 3 - Subprime\", 0.85, 1.0)"
      }
    ]
  }'
```

---

## 4. Resetting & Clearing the Database

### Complete Purge (Zero Nodes, Zero Edges)
To clear all entities, columns, and lineage edges completely (even sample lineage):

```bash
curl -X POST http://localhost:8000/api/reset
```

Response:
```json
{
  "status": "ok",
  "message": "Lineage database successfully cleared (0 nodes, 0 edges)."
}
```

### Re-seeding Sample Lineage
To reset and re-seed the SQLite database back to the default sample dataset:

```bash
curl -X POST "http://localhost:8000/api/reset?seed_sample=true"
```

Response:
```json
{
  "status": "ok",
  "message": "Lineage database successfully reset and re-seeded with sample data."
}
```

---

## 5. Interactive Swagger UI

You can test both endpoints visually without writing code:
1. Open [http://localhost:8000/docs](http://localhost:8000/docs) in your browser.
2. Locate `/api/ingest/teradata` or `/api/ingest/fabric`.
3. Click **"Try it out"**, paste your payload, and click **"Execute"**.
4. The React Flow UI canvas at [http://localhost:8000](http://localhost:8000) updates on your next page refresh!
