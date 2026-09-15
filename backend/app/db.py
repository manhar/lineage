import sqlite3
import os
from contextlib import contextmanager

DB_PATH = os.path.join(os.path.dirname(__file__), "data", "lineage.db")

def init_db(db_path: str = DB_PATH):
    os.makedirs(os.path.dirname(db_path), exist_ok=True)
    with sqlite3.connect(db_path) as conn:
        cursor = conn.cursor()

        # 1. Nodes table (Tables, Views, Reports)
        cursor.execute("""
        CREATE TABLE IF NOT EXISTS nodes (
            id TEXT PRIMARY KEY,
            system TEXT NOT NULL,
            container TEXT NOT NULL,
            name TEXT NOT NULL,
            schema_name TEXT NOT NULL,
            type TEXT NOT NULL
        );
        """)

        # 2. Columns table
        cursor.execute("""
        CREATE TABLE IF NOT EXISTS columns (
            id TEXT PRIMARY KEY,
            node_id TEXT NOT NULL,
            name TEXT NOT NULL,
            data_type TEXT NOT NULL,
            is_calculated INTEGER DEFAULT 0,
            expression TEXT,
            transformation_type TEXT,
            FOREIGN KEY (node_id) REFERENCES nodes(id) ON DELETE CASCADE
        );
        """)

        # 3. Column-Level Edges (supports N-to-1 derivations)
        cursor.execute("""
        CREATE TABLE IF NOT EXISTS column_edges (
            id TEXT PRIMARY KEY,
            source_node_id TEXT NOT NULL,
            source_column_id TEXT NOT NULL,
            target_node_id TEXT NOT NULL,
            target_column_id TEXT NOT NULL,
            transformation_type TEXT,
            expression TEXT,
            scanner_source TEXT,
            FOREIGN KEY (source_column_id) REFERENCES columns(id),
            FOREIGN KEY (target_column_id) REFERENCES columns(id)
        );
        """)

        # Performance indexes for graph traversal
        cursor.execute("CREATE INDEX IF NOT EXISTS idx_cols_node ON columns(node_id);")
        cursor.execute("CREATE INDEX IF NOT EXISTS idx_edge_target_col ON column_edges(target_column_id);")
        cursor.execute("CREATE INDEX IF NOT EXISTS idx_edge_source_col ON column_edges(source_column_id);")
        cursor.execute("CREATE INDEX IF NOT EXISTS idx_edge_target_node ON column_edges(target_node_id);")
        cursor.execute("CREATE INDEX IF NOT EXISTS idx_edge_source_node ON column_edges(source_node_id);")

        conn.commit()

def clear_db(db_path: str = DB_PATH):
    """
    Clears all entities, columns, and lineage edges from the database,
    leaving clean, empty tables.
    """
    init_db(db_path)
    with get_db(db_path) as conn:
        cursor = conn.cursor()
        cursor.execute("DELETE FROM column_edges;")
        cursor.execute("DELETE FROM columns;")
        cursor.execute("DELETE FROM nodes;")
        conn.commit()
        try:
            cursor.execute("VACUUM;")
        except Exception:
            pass

def prune_orphaned_edges(db_path: str = DB_PATH) -> int:
    """
    Prunes any edges in SQLite where source or target node or column does not exist.
    Guarantees 100% referential integrity and no dangling edges.
    """
    init_db(db_path)
    with get_db(db_path) as conn:
        cursor = conn.cursor()
        cursor.execute("""
            DELETE FROM column_edges
            WHERE id NOT IN (
                SELECT e.id
                FROM column_edges e
                JOIN nodes sn ON e.source_node_id = sn.id
                JOIN nodes tn ON e.target_node_id = tn.id
                JOIN columns sc ON e.source_column_id = sc.id AND sc.node_id = sn.id
                JOIN columns tc ON e.target_column_id = tc.id AND tc.node_id = tn.id
            );
        """)
        pruned = cursor.rowcount
        conn.commit()
        return pruned

@contextmanager
def get_db(db_path: str = DB_PATH):
    conn = sqlite3.connect(db_path)
    conn.row_factory = sqlite3.Row
    try:
        yield conn
    finally:
        conn.close()
