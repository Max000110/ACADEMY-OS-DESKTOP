import os
import sys

# Support PyInstaller frozen path imports resolution
if getattr(sys, 'frozen', False) and hasattr(sys, '_MEIPASS'):
    sys.path.insert(0, sys._MEIPASS)

import logging
from PySide6.QtWidgets import QApplication, QMessageBox, QDialog
from PySide6.QtCore import Qt

from src.utils.config import init_app_directories
from src.utils.logger import setup_logger
from src.database.connection import initialize_database
from src.engines.license import check_license_status, check_hardware_compatibility
from src.engines.backup import perform_backup
from src.ui.main_window import MainWindow
from src.ui.dialogs import ActivationDialog
from src.ui.styles import GLOBAL_STYLE_SHEET

def main():
    # 1. Initialize directories and settings.json
    init_app_directories()
    
    # 2. Setup rolling logger
    setup_logger()
    logging.info("Starting AcademyOS Desktop Application...")
    
    # 3. Initialize PySide6 Application
    app = QApplication(sys.argv)
    app.setStyleSheet(GLOBAL_STYLE_SHEET)
    
    # 4. Check Hardware Compatibility
    compatible, details, warnings = check_hardware_compatibility()
    logging.info(f"Hardware Check: {details}")
    if warnings:
        logging.warning(f"Hardware warning: {warnings}")
        # Show quick non-blocking warning to non-technical users if needed
        
    # 5. Initialize SQLite Database Schema & apply Migrations
    if not initialize_database():
        QMessageBox.critical(
            None, "Database Critical Error",
            "Failed to initialize SQLite local database. Access denied or write permissions missing on app folder."
        )
        sys.exit(1)
        
    # 6. Check Licensing and Activation Key Validation
    lic = check_license_status()
    if not lic["activated"]:
        logging.info(f"Unactivated client startup state: {lic['error']}. Displaying activation dialog...")
        activation_dlg = ActivationDialog()
        if activation_dlg.exec() != QDialog.Accepted:
            logging.info("User cancelled activation. Exiting application.")
            sys.exit(0)
            
    # 7. Perform Startup Automatic Backup
    logging.info("Executing startup database auto-backup task...")
    success, backup_path, err = perform_backup()
    if success:
        logging.info(f"Auto-backup successfully completed: {backup_path}")
    else:
        logging.error(f"Auto-backup failed: {err}")
        
    # 8. Start the Main Window
    window = MainWindow()
    window.show()
    
    # Run the application event loop
    sys.exit(app.exec())

if __name__ == "__main__":
    main()
