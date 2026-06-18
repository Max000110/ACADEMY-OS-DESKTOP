import os
import sqlite3
import threading
import logging
from src.utils.config import load_settings
from src.database.schema import SCHEMA_TABLES, INDEXES

_thread_local = threading.local()
_db_path = None

def get_db_path() -> str:
    """Resolve database path from application configuration."""
    global _db_path
    if not _db_path:
        settings = load_settings()
        _db_path = settings["database_path"]
    return _db_path

def set_db_path(path: str):
    """Override database path (useful for testing or switching DB)."""
    global _db_path
    _db_path = path
    # Clear thread local connections to force reconnection
    if hasattr(_thread_local, "connection"):
        try:
            _thread_local.connection.close()
        except Exception:
            pass
        delattr(_thread_local, "connection")

def get_connection() -> sqlite3.Connection:
    """Retrieve or create a thread-local SQLite connection."""
    db_path = get_db_path()
    
    # Ensure directory exists
    db_dir = os.path.dirname(db_path)
    if db_dir:
        os.makedirs(db_dir, exist_ok=True)
        
    if not hasattr(_thread_local, "connection"):
        try:
            conn = sqlite3.connect(db_path, timeout=5.0)  # Wait up to 5s on locked operations
            conn.row_factory = sqlite3.Row              # Retrieve rows as dictionary-like objects
            
            # Configure database pragmas
            cursor = conn.cursor()
            cursor.execute("PRAGMA foreign_keys = ON;")
            cursor.execute("PRAGMA journal_mode = WAL;")  # Concurrency enhancement
            cursor.execute("PRAGMA synchronous = NORMAL;")
            cursor.close()
            
            _thread_local.connection = conn
            logging.debug(f"Created new thread-local connection for thread: {threading.current_thread().name}")
        except Exception as e:
            logging.error(f"Failed to connect to SQLite database at {db_path}: {e}")
            raise e
            
    return _thread_local.connection

def close_thread_connection():
    """Close the database connection associated with the current thread."""
    if hasattr(_thread_local, "connection"):
        try:
            _thread_local.connection.close()
            logging.debug(f"Closed thread-local connection for thread: {threading.current_thread().name}")
        except Exception as e:
            logging.error(f"Error closing SQLite connection: {e}")
        finally:
            delattr(_thread_local, "connection")

def initialize_database() -> bool:
    """Initialize the schema tables, default settings, and apply indexes."""
    try:
        conn = get_connection()
        cursor = conn.cursor()
        
        # Execute create table SQL commands
        for ddl in SCHEMA_TABLES:
            cursor.execute(ddl)
            
        # Execute index creations
        for index in INDEXES:
            cursor.execute(index)
            
        conn.commit()
        cursor.close()
        
        # Run schema migrations check
        apply_migrations()
        
        logging.info("Database initialized successfully.")
        return True
    except Exception as e:
        logging.critical(f"Failed to initialize database schema: {e}")
        return False

def apply_migrations():
    """Apply schema migrations using PRAGMA user_version to version-control schema updates."""
    try:
        conn = get_connection()
        cursor = conn.cursor()
        
        # Get current schema version
        cursor.execute("PRAGMA user_version;")
        current_version = cursor.fetchone()[0]
        
        # Version 1: Initial schema
        # If we need future updates, we increments version and apply DDL changes
        target_version = 1
        
        if current_version < target_version:
            logging.info(f"Migrating database schema from version {current_version} to {target_version}...")
            # Perform migration steps here (none needed for version 1)
            cursor.execute(f"PRAGMA user_version = {target_version};")
            conn.commit()
            logging.info(f"Database migrated successfully to version {target_version}.")
            
        cursor.close()
    except Exception as e:
        logging.error(f"Error applying database migrations: {e}")
        raise e
