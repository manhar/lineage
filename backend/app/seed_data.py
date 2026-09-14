from .db import get_db, init_db, DB_PATH

def seed_lineage_database(db_path: str = DB_PATH):
    init_db(db_path)

    with get_db(db_path) as conn:
        cursor = conn.cursor()

        # Clear existing data
        cursor.execute("DELETE FROM column_edges;")
        cursor.execute("DELETE FROM columns;")
        cursor.execute("DELETE FROM nodes;")

        # =====================================================================
        # 1. NODES
        # =====================================================================
        nodes = [
            # Teradata Staging
            ("teradata://td_prod/stg_sales/stg_sales_txn", "Teradata EDW", "STG_SALES", "STG_SALES_TXN", "Staging", "source_table"),
            ("teradata://td_prod/stg_crm/stg_cust_master", "Teradata EDW", "STG_CRM", "STG_CUST_MASTER", "Staging", "source_table"),

            # Teradata Core Layer (ELT transformations)
            ("teradata://td_prod/edw_core/fact_transaction_summary", "Teradata EDW", "EDW_CORE", "FACT_TRANSACTION_SUMMARY", "Core", "dataset_table"),
            ("teradata://td_prod/edw_core/dim_customer_enriched", "Teradata EDW", "EDW_CORE", "DIM_CUSTOMER_ENRICHED", "Core", "dataset_table"),

            # Azure Fabric / Power BI Dataset
            ("fabric://ws_finance/sales_dataset/dim_customer", "Fabric Semantic Layer", "Finance & Sales Analytics", "Dim_Customer", "Model", "dataset_table"),
            ("fabric://ws_finance/sales_dataset/fact_sales", "Fabric Semantic Layer", "Finance & Sales Analytics", "Fact_Sales", "Model", "dataset_table"),

            # Azure Fabric / Power BI Report
            ("fabric://ws_finance/exec_dashboard/executive_kpi_summary", "Fabric Reporting", "Executive Reporting", "Executive_KPI_Summary", "Visual", "report"),
        ]

        cursor.executemany(
            "INSERT INTO nodes (id, system, container, name, schema_name, type) VALUES (?, ?, ?, ?, ?, ?);",
            nodes
        )

        # =====================================================================
        # 2. COLUMNS
        # =====================================================================
        columns = [
            # 1. STG_SALES_TXN
            ("teradata://td_prod/stg_sales/stg_sales_txn#txn_id", "teradata://td_prod/stg_sales/stg_sales_txn", "txn_id", "Int64", 0, None, "Direct"),
            ("teradata://td_prod/stg_sales/stg_sales_txn#cust_nbr", "teradata://td_prod/stg_sales/stg_sales_txn", "cust_nbr", "Int64", 0, None, "Direct"),
            ("teradata://td_prod/stg_sales/stg_sales_txn#sale_amt", "teradata://td_prod/stg_sales/stg_sales_txn", "sale_amt", "Decimal", 0, None, "Direct"),
            ("teradata://td_prod/stg_sales/stg_sales_txn#discount_amt", "teradata://td_prod/stg_sales/stg_sales_txn", "discount_amt", "Decimal", 0, None, "Direct"),
            ("teradata://td_prod/stg_sales/stg_sales_txn#tax_rate", "teradata://td_prod/stg_sales/stg_sales_txn", "tax_rate", "Decimal", 0, None, "Direct"),
            ("teradata://td_prod/stg_sales/stg_sales_txn#txn_dt", "teradata://td_prod/stg_sales/stg_sales_txn", "txn_dt", "Date", 0, None, "Direct"),

            # 2. STG_CUST_MASTER
            ("teradata://td_prod/stg_crm/stg_cust_master#cust_nbr", "teradata://td_prod/stg_crm/stg_cust_master", "cust_nbr", "Int64", 0, None, "Direct"),
            ("teradata://td_prod/stg_crm/stg_cust_master#first_name", "teradata://td_prod/stg_crm/stg_cust_master", "first_name", "String", 0, None, "Direct"),
            ("teradata://td_prod/stg_crm/stg_cust_master#last_name", "teradata://td_prod/stg_crm/stg_cust_master", "last_name", "String", 0, None, "Direct"),
            ("teradata://td_prod/stg_crm/stg_cust_master#credit_score", "teradata://td_prod/stg_crm/stg_cust_master", "credit_score", "Int64", 0, None, "Direct"),
            ("teradata://td_prod/stg_crm/stg_cust_master#state_code", "teradata://td_prod/stg_crm/stg_cust_master", "state_code", "String", 0, None, "Direct"),

            # 3. FACT_TRANSACTION_SUMMARY (Teradata Core)
            ("teradata://td_prod/edw_core/fact_transaction_summary#transaction_id", "teradata://td_prod/edw_core/fact_transaction_summary", "transaction_id", "Int64", 0, "STG_SALES_TXN.txn_id", "Direct"),
            ("teradata://td_prod/edw_core/fact_transaction_summary#customer_id", "teradata://td_prod/edw_core/fact_transaction_summary", "customer_id", "Int64", 0, "STG_SALES_TXN.cust_nbr", "Direct"),
            ("teradata://td_prod/edw_core/fact_transaction_summary#net_paid_amount", "teradata://td_prod/edw_core/fact_transaction_summary", "net_paid_amount", "Decimal", 1, "ROUND((sale_amt - discount_amt) * (1.0 + tax_rate), 2)", "SQL_Multi_Derivation"),
            ("teradata://td_prod/edw_core/fact_transaction_summary#transaction_date", "teradata://td_prod/edw_core/fact_transaction_summary", "transaction_date", "Date", 0, "STG_SALES_TXN.txn_dt", "Direct"),

            # 4. DIM_CUSTOMER_ENRICHED (Teradata Core)
            ("teradata://td_prod/edw_core/dim_customer_enriched#customer_id", "teradata://td_prod/edw_core/dim_customer_enriched", "customer_id", "Int64", 0, "STG_CUST_MASTER.cust_nbr", "Direct"),
            ("teradata://td_prod/edw_core/dim_customer_enriched#full_name", "teradata://td_prod/edw_core/dim_customer_enriched", "full_name", "String", 1, "TRIM(last_name) || ', ' || TRIM(first_name)", "SQL_Multi_Derivation"),
            ("teradata://td_prod/edw_core/dim_customer_enriched#risk_tier", "teradata://td_prod/edw_core/dim_customer_enriched", "risk_tier", "String", 1, "CASE WHEN credit_score >= 750 THEN 'Tier 1 - Prime' WHEN credit_score >= 650 THEN 'Tier 2 - Near Prime' ELSE 'Tier 3 - Subprime' END", "SQL_Derivation"),
            ("teradata://td_prod/edw_core/dim_customer_enriched#state_code", "teradata://td_prod/edw_core/dim_customer_enriched", "state_code", "String", 0, "STG_CUST_MASTER.state_code", "Direct"),

            # 5. Fabric Dim_Customer
            ("fabric://ws_finance/sales_dataset/dim_customer#Customer_ID", "fabric://ws_finance/sales_dataset/dim_customer", "Customer_ID", "Int64", 0, "DIM_CUSTOMER_ENRICHED[customer_id]", "Direct"),
            ("fabric://ws_finance/sales_dataset/dim_customer#Full_Name", "fabric://ws_finance/sales_dataset/dim_customer", "Full_Name", "String", 0, "DIM_CUSTOMER_ENRICHED[full_name]", "Direct"),
            ("fabric://ws_finance/sales_dataset/dim_customer#Risk_Tier", "fabric://ws_finance/sales_dataset/dim_customer", "Risk_Tier", "String", 0, "DIM_CUSTOMER_ENRICHED[risk_tier]", "Direct"),
            ("fabric://ws_finance/sales_dataset/dim_customer#State_Code", "fabric://ws_finance/sales_dataset/dim_customer", "State_Code", "String", 0, "DIM_CUSTOMER_ENRICHED[state_code]", "Direct"),

            # 6. Fabric Fact_Sales
            ("fabric://ws_finance/sales_dataset/fact_sales#Transaction_ID", "fabric://ws_finance/sales_dataset/fact_sales", "Transaction_ID", "Int64", 0, "FACT_TRANSACTION_SUMMARY[transaction_id]", "Direct"),
            ("fabric://ws_finance/sales_dataset/fact_sales#Customer_ID", "fabric://ws_finance/sales_dataset/fact_sales", "Customer_ID", "Int64", 0, "FACT_TRANSACTION_SUMMARY[customer_id]", "Direct"),
            ("fabric://ws_finance/sales_dataset/fact_sales#Net_Paid_Amount", "fabric://ws_finance/sales_dataset/fact_sales", "Net_Paid_Amount", "Decimal", 0, "FACT_TRANSACTION_SUMMARY[net_paid_amount]", "Direct"),
            ("fabric://ws_finance/sales_dataset/fact_sales#Risk_Adjusted_Revenue", "fabric://ws_finance/sales_dataset/fact_sales", "Risk_Adjusted_Revenue", "Decimal", 1, "Fact_Sales[Net_Paid_Amount] * IF(RELATED(Dim_Customer[Risk_Tier]) = \"Tier 3 - Subprime\", 0.85, 1.0)", "DAX_Cross_Table"),

            # 7. Fabric Executive_KPI_Summary (Report)
            ("fabric://ws_finance/exec_dashboard/executive_kpi_summary#Customer", "fabric://ws_finance/exec_dashboard/executive_kpi_summary", "Customer", "String", 0, "Dim_Customer[Full_Name]", "Report_Binding"),
            ("fabric://ws_finance/exec_dashboard/executive_kpi_summary#Risk_Profile", "fabric://ws_finance/exec_dashboard/executive_kpi_summary", "Risk_Profile", "String", 0, "Dim_Customer[Risk_Tier]", "Report_Binding"),
            ("fabric://ws_finance/exec_dashboard/executive_kpi_summary#Total_Revenue", "fabric://ws_finance/exec_dashboard/executive_kpi_summary", "Total_Revenue", "Decimal", 0, "SUM('Fact_Sales'[Net_Paid_Amount])", "Report_Measure"),
            ("fabric://ws_finance/exec_dashboard/executive_kpi_summary#Risk_Adjusted_Total", "fabric://ws_finance/exec_dashboard/executive_kpi_summary", "Risk_Adjusted_Total", "Decimal", 0, "SUM('Fact_Sales'[Risk_Adjusted_Revenue])", "Report_Measure"),
        ]

        cursor.executemany(
            "INSERT INTO columns (id, node_id, name, data_type, is_calculated, expression, transformation_type) VALUES (?, ?, ?, ?, ?, ?, ?);",
            columns
        )

        # =====================================================================
        # 3. COLUMN EDGES (Includes 3-to-1 and 2-to-1 derivations)
        # =====================================================================
        edges = [
            # --- Teradata Staging -> Teradata Core FACT_TRANSACTION_SUMMARY ---
            ("edge-stg-fact-txnid", 
             "teradata://td_prod/stg_sales/stg_sales_txn", "teradata://td_prod/stg_sales/stg_sales_txn#txn_id",
             "teradata://td_prod/edw_core/fact_transaction_summary", "teradata://td_prod/edw_core/fact_transaction_summary#transaction_id",
             "Direct", "STG_SALES_TXN.txn_id", "teradata_sql_scanner"),

            ("edge-stg-fact-custid", 
             "teradata://td_prod/stg_sales/stg_sales_txn", "teradata://td_prod/stg_sales/stg_sales_txn#cust_nbr",
             "teradata://td_prod/edw_core/fact_transaction_summary", "teradata://td_prod/edw_core/fact_transaction_summary#customer_id",
             "Direct", "STG_SALES_TXN.cust_nbr", "teradata_sql_scanner"),

            # MULTI-COLUMN DERIVATION 1: sale_amt + discount_amt + tax_rate -> net_paid_amount (3-to-1)
            ("edge-stg-fact-sale-amt", 
             "teradata://td_prod/stg_sales/stg_sales_txn", "teradata://td_prod/stg_sales/stg_sales_txn#sale_amt",
             "teradata://td_prod/edw_core/fact_transaction_summary", "teradata://td_prod/edw_core/fact_transaction_summary#net_paid_amount",
             "SQL_Multi_Derivation", "ROUND((sale_amt - discount_amt) * (1.0 + tax_rate), 2)", "teradata_sql_scanner"),

            ("edge-stg-fact-discount-amt", 
             "teradata://td_prod/stg_sales/stg_sales_txn", "teradata://td_prod/stg_sales/stg_sales_txn#discount_amt",
             "teradata://td_prod/edw_core/fact_transaction_summary", "teradata://td_prod/edw_core/fact_transaction_summary#net_paid_amount",
             "SQL_Multi_Derivation", "ROUND((sale_amt - discount_amt) * (1.0 + tax_rate), 2)", "teradata_sql_scanner"),

            ("edge-stg-fact-tax-rate", 
             "teradata://td_prod/stg_sales/stg_sales_txn", "teradata://td_prod/stg_sales/stg_sales_txn#tax_rate",
             "teradata://td_prod/edw_core/fact_transaction_summary", "teradata://td_prod/edw_core/fact_transaction_summary#net_paid_amount",
             "SQL_Multi_Derivation", "ROUND((sale_amt - discount_amt) * (1.0 + tax_rate), 2)", "teradata_sql_scanner"),

            ("edge-stg-fact-txndt", 
             "teradata://td_prod/stg_sales/stg_sales_txn", "teradata://td_prod/stg_sales/stg_sales_txn#txn_dt",
             "teradata://td_prod/edw_core/fact_transaction_summary", "teradata://td_prod/edw_core/fact_transaction_summary#transaction_date",
             "Direct", "STG_SALES_TXN.txn_dt", "teradata_sql_scanner"),

            # --- Teradata Staging -> Teradata Core DIM_CUSTOMER_ENRICHED ---
            ("edge-stg-dim-custid", 
             "teradata://td_prod/stg_crm/stg_cust_master", "teradata://td_prod/stg_crm/stg_cust_master#cust_nbr",
             "teradata://td_prod/edw_core/dim_customer_enriched", "teradata://td_prod/edw_core/dim_customer_enriched#customer_id",
             "Direct", "STG_CUST_MASTER.cust_nbr", "teradata_sql_scanner"),

            # MULTI-COLUMN DERIVATION 2: first_name + last_name -> full_name (2-to-1)
            ("edge-stg-dim-fname", 
             "teradata://td_prod/stg_crm/stg_cust_master", "teradata://td_prod/stg_crm/stg_cust_master#first_name",
             "teradata://td_prod/edw_core/dim_customer_enriched", "teradata://td_prod/edw_core/dim_customer_enriched#full_name",
             "SQL_Multi_Derivation", "TRIM(last_name) || ', ' || TRIM(first_name)", "teradata_sql_scanner"),

            ("edge-stg-dim-lname", 
             "teradata://td_prod/stg_crm/stg_cust_master", "teradata://td_prod/stg_crm/stg_cust_master#last_name",
             "teradata://td_prod/edw_core/dim_customer_enriched", "teradata://td_prod/edw_core/dim_customer_enriched#full_name",
             "SQL_Multi_Derivation", "TRIM(last_name) || ', ' || TRIM(first_name)", "teradata_sql_scanner"),

            # CASE DERIVATION: credit_score -> risk_tier
            ("edge-stg-dim-risk", 
             "teradata://td_prod/stg_crm/stg_cust_master", "teradata://td_prod/stg_crm/stg_cust_master#credit_score",
             "teradata://td_prod/edw_core/dim_customer_enriched", "teradata://td_prod/edw_core/dim_customer_enriched#risk_tier",
             "SQL_Derivation", "CASE WHEN credit_score >= 750 THEN 'Tier 1 - Prime' ...", "teradata_sql_scanner"),

            ("edge-stg-dim-state", 
             "teradata://td_prod/stg_crm/stg_cust_master", "teradata://td_prod/stg_crm/stg_cust_master#state_code",
             "teradata://td_prod/edw_core/dim_customer_enriched", "teradata://td_prod/edw_core/dim_customer_enriched#state_code",
             "Direct", "STG_CUST_MASTER.state_code", "teradata_sql_scanner"),

            # --- Bridge: Teradata Core -> Fabric Dataset (Dim_Customer) ---
            ("edge-pbi-dim-custid",
             "teradata://td_prod/edw_core/dim_customer_enriched", "teradata://td_prod/edw_core/dim_customer_enriched#customer_id",
             "fabric://ws_finance/sales_dataset/dim_customer", "fabric://ws_finance/sales_dataset/dim_customer#Customer_ID",
             "Direct", "DIM_CUSTOMER_ENRICHED[customer_id]", "fabric_scanner"),

            ("edge-pbi-dim-fullname",
             "teradata://td_prod/edw_core/dim_customer_enriched", "teradata://td_prod/edw_core/dim_customer_enriched#full_name",
             "fabric://ws_finance/sales_dataset/dim_customer", "fabric://ws_finance/sales_dataset/dim_customer#Full_Name",
             "Direct", "DIM_CUSTOMER_ENRICHED[full_name]", "fabric_scanner"),

            ("edge-pbi-dim-risktier",
             "teradata://td_prod/edw_core/dim_customer_enriched", "teradata://td_prod/edw_core/dim_customer_enriched#risk_tier",
             "fabric://ws_finance/sales_dataset/dim_customer", "fabric://ws_finance/sales_dataset/dim_customer#Risk_Tier",
             "Direct", "DIM_CUSTOMER_ENRICHED[risk_tier]", "fabric_scanner"),

            ("edge-pbi-dim-state",
             "teradata://td_prod/edw_core/dim_customer_enriched", "teradata://td_prod/edw_core/dim_customer_enriched#state_code",
             "fabric://ws_finance/sales_dataset/dim_customer", "fabric://ws_finance/sales_dataset/dim_customer#State_Code",
             "Direct", "DIM_CUSTOMER_ENRICHED[state_code]", "fabric_scanner"),

            # --- Bridge: Teradata Core -> Fabric Dataset (Fact_Sales) ---
            ("edge-pbi-fact-txnid",
             "teradata://td_prod/edw_core/fact_transaction_summary", "teradata://td_prod/edw_core/fact_transaction_summary#transaction_id",
             "fabric://ws_finance/sales_dataset/fact_sales", "fabric://ws_finance/sales_dataset/fact_sales#Transaction_ID",
             "Direct", "FACT_TRANSACTION_SUMMARY[transaction_id]", "fabric_scanner"),

            ("edge-pbi-fact-custid",
             "teradata://td_prod/edw_core/fact_transaction_summary", "teradata://td_prod/edw_core/fact_transaction_summary#customer_id",
             "fabric://ws_finance/sales_dataset/fact_sales", "fabric://ws_finance/sales_dataset/fact_sales#Customer_ID",
             "Direct", "FACT_TRANSACTION_SUMMARY[customer_id]", "fabric_scanner"),

            ("edge-pbi-fact-netpaid",
             "teradata://td_prod/edw_core/fact_transaction_summary", "teradata://td_prod/edw_core/fact_transaction_summary#net_paid_amount",
             "fabric://ws_finance/sales_dataset/fact_sales", "fabric://ws_finance/sales_dataset/fact_sales#Net_Paid_Amount",
             "Direct", "FACT_TRANSACTION_SUMMARY[net_paid_amount]", "fabric_scanner"),

            # MULTI-TABLE DAX DERIVATION 3: Net_Paid_Amount (Fact) + Risk_Tier (Dim) -> Risk_Adjusted_Revenue
            ("edge-pbi-dax-netpaid",
             "fabric://ws_finance/sales_dataset/fact_sales", "fabric://ws_finance/sales_dataset/fact_sales#Net_Paid_Amount",
             "fabric://ws_finance/sales_dataset/fact_sales", "fabric://ws_finance/sales_dataset/fact_sales#Risk_Adjusted_Revenue",
             "DAX_Cross_Table", "Fact_Sales[Net_Paid_Amount] * IF(RELATED(Dim_Customer[Risk_Tier]) = \"Tier 3 - Subprime\", 0.85, 1.0)", "fabric_scanner"),

            ("edge-pbi-dax-risktier",
             "fabric://ws_finance/sales_dataset/dim_customer", "fabric://ws_finance/sales_dataset/dim_customer#Risk_Tier",
             "fabric://ws_finance/sales_dataset/fact_sales", "fabric://ws_finance/sales_dataset/fact_sales#Risk_Adjusted_Revenue",
             "DAX_Cross_Table", "Fact_Sales[Net_Paid_Amount] * IF(RELATED(Dim_Customer[Risk_Tier]) = \"Tier 3 - Subprime\", 0.85, 1.0)", "fabric_scanner"),

            # --- Fabric Dataset -> Fabric Executive Report Visual ---
            ("edge-rpt-customer",
             "fabric://ws_finance/sales_dataset/dim_customer", "fabric://ws_finance/sales_dataset/dim_customer#Full_Name",
             "fabric://ws_finance/exec_dashboard/executive_kpi_summary", "fabric://ws_finance/exec_dashboard/executive_kpi_summary#Customer",
             "Report_Binding", "Dim_Customer[Full_Name]", "fabric_scanner"),

            ("edge-rpt-risk",
             "fabric://ws_finance/sales_dataset/dim_customer", "fabric://ws_finance/sales_dataset/dim_customer#Risk_Tier",
             "fabric://ws_finance/exec_dashboard/executive_kpi_summary", "fabric://ws_finance/exec_dashboard/executive_kpi_summary#Risk_Profile",
             "Report_Binding", "Dim_Customer[Risk_Tier]", "fabric_scanner"),

            ("edge-rpt-revenue",
             "fabric://ws_finance/sales_dataset/fact_sales", "fabric://ws_finance/sales_dataset/fact_sales#Net_Paid_Amount",
             "fabric://ws_finance/exec_dashboard/executive_kpi_summary", "fabric://ws_finance/exec_dashboard/executive_kpi_summary#Total_Revenue",
             "Report_Measure", "SUM('Fact_Sales'[Net_Paid_Amount])", "fabric_scanner"),

            ("edge-rpt-adj-revenue",
             "fabric://ws_finance/sales_dataset/fact_sales", "fabric://ws_finance/sales_dataset/fact_sales#Risk_Adjusted_Revenue",
             "fabric://ws_finance/exec_dashboard/executive_kpi_summary", "fabric://ws_finance/exec_dashboard/executive_kpi_summary#Risk_Adjusted_Total",
             "Report_Measure", "SUM('Fact_Sales'[Risk_Adjusted_Revenue])", "fabric_scanner"),
        ]

        cursor.executemany(
            """INSERT INTO column_edges 
               (id, source_node_id, source_column_id, target_node_id, target_column_id, transformation_type, expression, scanner_source) 
               VALUES (?, ?, ?, ?, ?, ?, ?, ?);""",
            edges
        )

        conn.commit()
        print(f"Successfully seeded SQLite lineage database: {len(nodes)} nodes, {len(columns)} columns, {len(edges)} column edges.")

if __name__ == "__main__":
    seed_lineage_database()
