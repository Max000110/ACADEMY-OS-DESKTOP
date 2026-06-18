import sys
import os
import unittest
import tempfile
from PySide6.QtWidgets import QApplication
from PySide6.QtCore import Qt

# Ensure we run offscreen if a display is missing
os.environ["QT_QPA_PLATFORM"] = "offscreen"

from src.database.connection import set_db_path, initialize_database, close_thread_connection
from src.ui.main_window import MainWindow
from src.utils.config import load_settings, save_settings
import src.engines.license as license_engine
from src.utils.crypto import generate_signature

class TestAcademyOSUIHeadless(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        # Create QApplication singleton for the whole test class
        cls.app = QApplication.instance()
        if not cls.app:
            cls.app = QApplication(sys.argv)
            
    def setUp(self):
        # Setup temporary directories and database
        self.temp_dir = tempfile.TemporaryDirectory()
        self.db_path = os.path.join(self.temp_dir.name, "test_ui.db")
        set_db_path(self.db_path)
        initialize_database()
        
        # Isolate licensing config
        self.original_app_dir = license_engine.APP_DIR
        self.original_license_path = license_engine.LICENSE_PATH
        license_engine.APP_DIR = self.temp_dir.name
        license_engine.LICENSE_PATH = os.path.join(self.temp_dir.name, "license.json")
        
        # Automatically activate database for UI test loading
        fp = license_engine.get_device_fingerprint()
        expiry_date = "2030-12-31"
        license_key = f"AOS-KEY-{expiry_date}"
        sig = generate_signature(license_key, expiry_date, fp)
        activation_key = f"AOS-KEY-{expiry_date}-{sig}"
        license_engine.activate_license(activation_key)
        
        # Override config paths for testing
        settings = load_settings()
        settings["reports_directory"] = os.path.join(self.temp_dir.name, "reports")
        settings["backup_directory"] = os.path.join(self.temp_dir.name, "backups")
        save_settings(settings)
        
    def tearDown(self):
        close_thread_connection()
        license_engine.APP_DIR = self.original_app_dir
        license_engine.LICENSE_PATH = self.original_license_path
        self.temp_dir.cleanup()
        
    def test_main_window_tabs(self):
        window = MainWindow()
        self.assertIsNotNone(window)
        self.assertEqual(window.sidebar.count(), 6)
        
        # Test tab switching updates stacked index
        window.sidebar.setCurrentRow(1) # Student tab
        self.assertEqual(window.content_stack.currentIndex(), 1)
        
        window.sidebar.setCurrentRow(2) # Lead tab
        self.assertEqual(window.content_stack.currentIndex(), 2)
        
        window.sidebar.setCurrentRow(5) # Settings tab
        self.assertEqual(window.content_stack.currentIndex(), 5)
        
        window.close()

if __name__ == "__main__":
    unittest.main()
