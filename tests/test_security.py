import os
import unittest
import tempfile
import json
import zipfile
import datetime
from src.database.connection import set_db_path, initialize_database, get_connection, close_thread_connection
from src.database.queries import add_student, search_students
import src.utils.config as config
import src.engines.license as license_engine
from src.engines.backup import restore_backup
from src.engines.excel_export import sanitize_formula_injection

class TestAcademyOSSecurity(unittest.TestCase):
    def setUp(self):
        # Create a temporary directory for config/license files
        self.temp_dir = tempfile.TemporaryDirectory()
        
        # Save original config variables
        self.orig_app_dir = config.APP_DIR
        self.orig_settings_path = config.SETTINGS_PATH
        self.orig_license_path = license_engine.LICENSE_PATH
        
        # Override config variables to redirect all tests to temp_dir
        config.APP_DIR = self.temp_dir.name
        config.SETTINGS_PATH = os.path.join(self.temp_dir.name, "settings.json")
        license_engine.APP_DIR = self.temp_dir.name
        license_engine.LICENSE_PATH = os.path.join(self.temp_dir.name, "license.json")
        
        # Write default temp settings
        config.save_settings(config.DEFAULT_SETTINGS)
        
        # Set up a temporary database file
        self.db_fd, self.db_path = tempfile.mkstemp()
        set_db_path(self.db_path)
        initialize_database()
        
    def tearDown(self):
        close_thread_connection()
        os.close(self.db_fd)
        try:
            os.remove(self.db_path)
        except OSError:
            pass
            
        # Restore original config variables
        config.APP_DIR = self.orig_app_dir
        config.SETTINGS_PATH = self.orig_settings_path
        license_engine.APP_DIR = self.orig_app_dir
        license_engine.LICENSE_PATH = self.orig_license_path
        
        self.temp_dir.cleanup()
        
    def test_clock_tampering_detection(self):
        # 1. Normal execution (today) should not report tampering
        self.assertFalse(license_engine.check_clock_tampering())
        
        # 2. Tamper settings to set last run date to tomorrow
        settings = config.load_settings()
        tomorrow = (datetime.date.today() + datetime.timedelta(days=1)).strftime("%Y-%m-%d")
        settings["last_run_date"] = tomorrow
        config.save_settings(settings)
        
        # 3. Check clock tampering should now return True
        self.assertTrue(license_engine.check_clock_tampering())
        
    def test_excel_formula_escaping(self):
        # Test values starting with formula chars
        self.assertEqual(sanitize_formula_injection("=SUM(A1:A10)"), "'=SUM(A1:A10)")
        self.assertEqual(sanitize_formula_injection("+123"), "'+123")
        self.assertEqual(sanitize_formula_injection("-5.50"), "'-5.50")
        self.assertEqual(sanitize_formula_injection("@CMD"), "'@CMD")
        
        # Test safe values
        self.assertEqual(sanitize_formula_injection("John Doe"), "John Doe")
        self.assertEqual(sanitize_formula_injection("123"), "123")
        self.assertEqual(sanitize_formula_injection("user@example.com"), "user@example.com")
        self.assertEqual(sanitize_formula_injection(100.5), 100.5)

    def test_zip_slip_prevention(self):
        # Create a malicious zip file with path traversal entries
        zip_path = os.path.join(self.temp_dir.name, "malicious.zip")
        extract_dir = os.path.join(self.temp_dir.name, "extract")
        os.makedirs(extract_dir, exist_ok=True)
        
        # We will attempt to write outside extract_dir by traversing up
        traversal_filename = "../outside_exploit.txt"
        
        with zipfile.ZipFile(zip_path, 'w') as zf:
            zf.writestr(traversal_filename, "malicious payload")
            zf.writestr("safe_file.txt", "safe payload")
            
        # Call restore_backup and verify it detects and blocks path traversal
        success, error = restore_backup(zip_path, extract_dir)
        self.assertFalse(success)
        self.assertIn("Security Warning", error)
        self.assertIn("Path traversal attempt detected", error)
        
        # Verify that safe_file.txt was NOT extracted because the whole operation was aborted
        safe_path = os.path.join(extract_dir, "safe_file.txt")
        self.assertFalse(os.path.exists(safe_path))
        
        # Verify that no file was created outside the extract directory
        outside_path = os.path.abspath(os.path.join(extract_dir, traversal_filename))
        self.assertFalse(os.path.exists(outside_path))

    def test_sql_injection_resilience(self):
        # Inject standard student payload
        student_id = add_student("Attack", "Student", "attacker@mail.com", "9876543210", "2000-01-01", "Male", "Target Addr")
        self.assertIsNotNone(student_id)
        
        # Attempt sql injection input into student search
        sqli_query = "' OR '1'='1"
        results = search_students(sqli_query)
        
        # Search should not return all students, only matches (which should be 0 because no student has name like the sqli string)
        self.assertEqual(len(results), 0)

if __name__ == "__main__":
    unittest.main()
