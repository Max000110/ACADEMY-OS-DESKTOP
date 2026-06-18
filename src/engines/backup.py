import os
import sqlite3
import shutil
import zipfile
import logging
from datetime import datetime
from src.utils.config import load_settings, SETTINGS_PATH
from src.database.connection import get_connection

def perform_backup() -> tuple:
    """
    Perform a full, transactionally safe backup.
    Packs database (using SQLite Backup API), settings.json, and the reports folder
    into a compressed ZIP archive.
    
    Returns (success: bool, archive_path: str or None, error_message: str or None)
    """
    try:
        settings = load_settings()
        db_path = settings["database_path"]
        backup_dir = settings["backup_directory"]
        reports_dir = settings["reports_directory"]
        retention_count = settings.get("backup_retention_count", 30)
        
        os.makedirs(backup_dir, exist_ok=True)
        
        # 1. Create a safe, transaction-consistent copy of the SQLite database
        temp_db_copy = os.path.join(backup_dir, "temp_backup.db")
        if os.path.exists(temp_db_copy):
            os.remove(temp_db_copy)
            
        try:
            # Connect to destination temp DB
            dest_conn = sqlite3.connect(temp_db_copy)
            # Retrieve source thread-local connection
            src_conn = get_connection()
            # Perform native SQLite backup
            src_conn.backup(dest_conn)
            dest_conn.close()
        except Exception as db_err:
            logging.error(f"Failed to copy SQLite database via backup API: {db_err}")
            if os.path.exists(temp_db_copy):
                os.remove(temp_db_copy)
            return False, None, f"Database backup copy failed: {db_err}"
            
        # 2. Package everything in a ZIP file
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S_%f")
        backup_filename = f"academyos_backup_{timestamp}.zip"
        backup_filepath = os.path.join(backup_dir, backup_filename)
        
        try:
            with zipfile.ZipFile(backup_filepath, 'w', zipfile.ZIP_DEFLATED) as zipf:
                # Add database copy
                zipf.write(temp_db_copy, "academyos.db")
                
                # Add settings file if it exists
                if os.path.exists(SETTINGS_PATH):
                    zipf.write(SETTINGS_PATH, "settings.json")
                    
                # Add reports directory recursively
                if os.path.exists(reports_dir):
                    for root, _, files in os.walk(reports_dir):
                        for file in files:
                            full_path = os.path.join(root, file)
                            rel_path = os.path.relpath(full_path, os.path.dirname(reports_dir))
                            zipf.write(full_path, rel_path)
                            
            logging.info(f"Backup package created successfully at: {backup_filepath}")
        except Exception as zip_err:
            logging.error(f"Failed to compile backup ZIP archive: {zip_err}")
            if os.path.exists(backup_filepath):
                os.remove(backup_filepath)
            return False, None, f"ZIP packaging failed: {zip_err}"
        finally:
            # Clean up the temporary database copy
            if os.path.exists(temp_db_copy):
                os.remove(temp_db_copy)
                
        # 3. Apply rolling retention (delete files beyond the count limit)
        rotate_backups(backup_dir, retention_count)
        
        return True, backup_filepath, None
        
    except Exception as e:
        logging.error(f"Backup process failed: {e}")
        return False, None, str(e)

def rotate_backups(backup_dir: str, max_retention: int):
    """Scan backup folder, identify matching zip files, and remove the oldest ones."""
    try:
        backups = []
        for file in os.listdir(backup_dir):
            if file.startswith("academyos_backup_") and file.endswith(".zip"):
                path = os.path.join(backup_dir, file)
                mtime = os.path.getmtime(path)
                backups.append((path, mtime))
                
        # Sort backups by modification time (oldest first)
        backups.sort(key=lambda x: x[1])
        
        # Determine if we exceed retention threshold
        excess = len(backups) - max_retention
        if excess > 0:
            logging.info(f"Backup directory exceeds retention limit ({len(backups)}/{max_retention}). Trimming oldest {excess} files.")
            for i in range(excess):
                oldest_file = backups[i][0]
                try:
                    os.remove(oldest_file)
                    logging.info(f"Removed expired backup archive: {oldest_file}")
                except Exception as del_err:
                    logging.error(f"Failed to remove expired backup {oldest_file}: {del_err}")
    except Exception as e:
        logging.error(f"Error executing backup retention cleanup: {e}")

def restore_backup(zip_path: str, target_dir: str) -> tuple:
    """
    Restore backup from a ZIP archive securely to target_dir.
    Checks for path traversal vulnerabilities (Zip Slip) to ensure files are only
    written inside the target directory.
    
    Returns (success: bool, error_message: str or None)
    """
    try:
        if not os.path.exists(zip_path):
            return False, f"Backup file not found: {zip_path}"
            
        os.makedirs(target_dir, exist_ok=True)
        abs_target_dir = os.path.abspath(target_dir)
        
        with zipfile.ZipFile(zip_path, 'r') as zipf:
            # First pass: validate all paths to prevent Zip Slip
            for member in zipf.namelist():
                # Resolve destination path
                dest_path = os.path.abspath(os.path.join(abs_target_dir, member))
                # Check prefix
                if not dest_path.startswith(abs_target_dir + os.sep) and dest_path != abs_target_dir:
                    return False, f"Security Warning: Path traversal attempt detected in ZIP member: {member}"
            
            # Second pass: execute extraction safely
            for member in zipf.infolist():
                dest_path = os.path.abspath(os.path.join(abs_target_dir, member.filename))
                
                # Ensure directory exists for files nested under directories
                if member.is_dir():
                    os.makedirs(dest_path, exist_ok=True)
                else:
                    os.makedirs(os.path.dirname(dest_path), exist_ok=True)
                    with zipf.open(member) as source, open(dest_path, "wb") as target:
                        shutil.copyfileobj(source, target)
                        
        return True, None
    except Exception as e:
        logging.error(f"Failed to restore backup: {e}")
        return False, str(e)

