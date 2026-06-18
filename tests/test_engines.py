import os
import unittest
import tempfile
import json
import datetime
from src.utils.config import APP_DIR
import src.engines.license as license_engine
from src.utils.crypto import generate_signature

class TestAcademyOSEngines(unittest.TestCase):
    def setUp(self):
        # Override app data directory for tests to isolate them from ~/.academyos
        self.temp_dir = tempfile.TemporaryDirectory()
        self.original_app_dir = license_engine.APP_DIR
        self.original_license_path = license_engine.LICENSE_PATH
        
        license_engine.APP_DIR = self.temp_dir.name
        license_engine.LICENSE_PATH = os.path.join(self.temp_dir.name, "license.json")
        
    def tearDown(self):
        license_engine.APP_DIR = self.original_app_dir
        license_engine.LICENSE_PATH = self.original_license_path
        self.temp_dir.cleanup()
        
    def test_fingerprint_generation(self):
        fp = license_engine.get_device_fingerprint()
        self.assertEqual(len(fp), 64)  # SHA-256 hash length is 64 hex characters
        
    def test_hardware_compatibility(self):
        compatible, details, warnings = license_engine.check_hardware_compatibility()
        self.assertTrue(compatible)
        self.assertIn("CPU Cores", details)
        self.assertIsInstance(warnings, list)
        
    def test_activation_flow(self):
        # Initial status should be unactivated
        status = license_engine.check_license_status()
        self.assertFalse(status["activated"])
        self.assertEqual(status["error"], "Not Activated")
        
        # Generate a valid activation key for current device fingerprint
        fingerprint = license_engine.get_device_fingerprint()
        expiry_date = (datetime.date.today() + datetime.timedelta(days=365)).strftime("%Y-%m-%d")
        
        # Format of key signature input: license_key + expiry_date + fingerprint
        license_key = f"AOS-KEY-{expiry_date}"
        sig = generate_signature(license_key, expiry_date, fingerprint)
        
        # Key format: AOS-KEY-<expiry>-<signature>
        activation_key = f"AOS-KEY-{expiry_date}-{sig}"
        
        # Test activation
        success = license_engine.activate_license(activation_key)
        self.assertTrue(success)
        
        # Re-check status
        status = license_engine.check_license_status()
        self.assertTrue(status["activated"])
        self.assertEqual(status["expiry_date"], expiry_date)
        self.assertGreaterEqual(status["days_remaining"], 364)
        
    def test_tampered_license(self):
        # Generate valid activation first
        fingerprint = license_engine.get_device_fingerprint()
        expiry_date = "2030-12-31"
        license_key = f"AOS-KEY-{expiry_date}"
        sig = generate_signature(license_key, expiry_date, fingerprint)
        activation_key = f"AOS-KEY-{expiry_date}-{sig}"
        
        license_engine.activate_license(activation_key)
        
        # Now tamper with license file (extend date manually in json)
        with open(license_engine.LICENSE_PATH, 'r') as f:
            data = json.load(f)
            
        data["expiry_date"] = "2040-12-31"  # Modifying expiration date
        
        with open(license_engine.LICENSE_PATH, 'w') as f:
            json.dump(data, f)
            
        # Check status should identify tampering
        status = license_engine.check_license_status()
        self.assertFalse(status["activated"])
        self.assertEqual(status["error"], "License Tampered")

    def test_backup_execution(self):
        import src.engines.backup as backup_engine
        from src.utils.config import load_settings, save_settings
        import zipfile
        
        # Configure custom directories under temporary folder for testing backups
        settings = load_settings()
        backup_dir = os.path.join(self.temp_dir.name, "backups")
        reports_dir = os.path.join(self.temp_dir.name, "reports")
        os.makedirs(backup_dir, exist_ok=True)
        os.makedirs(reports_dir, exist_ok=True)
        
        # Save temp mock report file
        mock_report = os.path.join(reports_dir, "test_report.pdf")
        with open(mock_report, "w") as f:
            f.write("mock pdf content")
            
        settings["backup_directory"] = backup_dir
        settings["reports_directory"] = reports_dir
        settings["backup_retention_count"] = 2  # Set low retention for testing rotation
        save_settings(settings)
        
        # 1. Run first backup
        success, path, error = backup_engine.perform_backup()
        self.assertTrue(success)
        self.assertIsNotNone(path)
        self.assertTrue(os.path.exists(path))
        self.assertIsNone(error)
        
        # Verify ZIP contains the DB and reports
        with zipfile.ZipFile(path, 'r') as zipf:
            namelist = zipf.namelist()
            self.assertIn("academyos.db", namelist)
            self.assertIn("settings.json", namelist)
            self.assertTrue(any(f.endswith("test_report.pdf") for f in namelist))
            
        # 2. Run two more backups (making 3 total) to trigger rotation
        success2, path2, _ = backup_engine.perform_backup()
        self.assertTrue(success2)
        
        # Sleep briefly to ensure distinct file modification times
        import time
        time.sleep(0.1)
        
        success3, path3, _ = backup_engine.perform_backup()
        self.assertTrue(success3)
        
        # Confirm that the oldest backup (the first one) was rotated (deleted)
        # and we only have retention_count = 2 files left.
        self.assertFalse(os.path.exists(path))
        self.assertTrue(os.path.exists(path2))
        self.assertTrue(os.path.exists(path3))
        
        files = [f for f in os.listdir(backup_dir) if f.startswith("academyos_backup_")]
        self.assertEqual(len(files), 2)
    def test_admission_validation(self):
        from src.engines.admission import register_new_student, modify_existing_student, AdmissionValidationError
        
        # Initialize database for thread-local
        from src.database.connection import initialize_database
        initialize_database()
        
        # Name validation test
        with self.assertRaises(AdmissionValidationError):
            register_new_student(" ", "Doe", "john@mail.com", "9876543210", "2000-01-01", "Male", "Address")
            
        # Phone validation test
        with self.assertRaises(AdmissionValidationError):
            register_new_student("John", "Doe", "john@mail.com", "123", "2000-01-01", "Male", "Address")
            
        # DOB validation test (future date)
        with self.assertRaises(AdmissionValidationError):
            register_new_student("John", "Doe", "john@mail.com", "9876543210", "2050-01-01", "Male", "Address")
            
    def test_lead_promotion(self):
        from src.engines.lead import create_lead, promote_lead_to_student
        from src.database.queries import add_course, search_students, get_student_enrollments
        from src.database.connection import initialize_database
        initialize_database()
        
        # Create course for promotion enrollment
        course_id = add_course("Web App Development", "WEB-201", "Fullstack Javascript", 6, 25000.0)
        
        # Create lead interested in the course
        lead_id = create_lead(
            first_name="Jane", last_name="Smith", phone="9998887776", email="jane@smith.com",
            source="Walk-in", course_id=course_id, remarks="Interested in fullstack"
        )
        self.assertIsNotNone(lead_id)
        
        # Promote lead to student
        student_id, enrollment_id = promote_lead_to_student(
            lead_id=lead_id, dob="1998-05-15", gender="Female", address="North Avenue", course_discount=5000.0
        )
        self.assertIsNotNone(student_id)
        self.assertIsNotNone(enrollment_id)
        
        # Verify student details exist
        students = search_students("Jane")
        self.assertEqual(len(students), 1)
        self.assertEqual(students[0]["phone"], "9998887776")
        
        # Verify enrollment net_fee reflects discount (25000 - 5000 = 20000)
        enrollments = get_student_enrollments(student_id)
        self.assertEqual(len(enrollments), 1)
        self.assertEqual(enrollments[0]["net_fee"], 20000.0)
        
    def test_fee_ledger_financials(self):
        from src.engines.fee import get_enrollment_financials, get_outstanding_fees_list
        from src.database.queries import add_student, add_course, enroll_student, add_fee_payment
        from src.database.connection import initialize_database
        initialize_database()
        
        stud_id = add_student("Fin", "Test", "fin@test.com", "9900990099", "1995-10-10", "Male", "St.")
        course_id = add_course("QA Testing", "QA-301", "Software testing", 2, 10000.0)
        enroll_id = enroll_student(stud_id, course_id, discount=1000.0, net_fee=9000.0)
        
        add_fee_payment(enroll_id, amount_paid=4000.0, payment_method="Card", receipt_number="REC-99", remarks="First part")
        
        # Validate calculations
        fin = get_enrollment_financials(enroll_id)
        self.assertEqual(fin["course_base_fee"], 10000.0)
        self.assertEqual(fin["discount"], 1000.0)
        self.assertEqual(fin["net_fee"], 9000.0)
        self.assertEqual(fin["total_paid"], 4000.0)
        self.assertEqual(fin["due_amount"], 5000.0)
        
        # Verify outstanding fee checklist includes this enrollment
        out_list = get_outstanding_fees_list()
        self.assertEqual(len(out_list), 1)
        self.assertEqual(out_list[0]["due_amount"], 5000.0)
        self.assertEqual(out_list[0]["student_name"], "Fin Test")
        
    def test_staging_import_flow(self):
        from src.engines.staging import stage_and_validate_records, approve_and_commit_staging
        from src.database.queries import get_staging_by_status, search_students
        from src.database.connection import initialize_database
        initialize_database()
        
        raw_rows = [
            # Valid record
            {"first_name": "Valid1", "last_name": "Student1", "phone": "9990008880", "email": "valid1@student.com", "dob": "2000-02-02", "gender": "Male", "address": "Addr1"},
            # Invalid record (missing last name, invalid phone)
            {"first_name": "Invalid1", "last_name": "", "phone": "123", "email": "bademail", "dob": "2000-02-02", "gender": "Male", "address": "Addr2"}
        ]
        
        # Stage
        count = stage_and_validate_records("Students", raw_rows, "test_file.csv")
        self.assertEqual(count, 2)
        
        # Verify status lists in database
        val_records = get_staging_by_status("Valid")
        err_records = get_staging_by_status("Error")
        self.assertEqual(len(val_records), 1)
        self.assertEqual(len(err_records), 1)
        
        # Commit valid records
        success, failed = approve_and_commit_staging("Students")
        self.assertEqual(success, 1)
        self.assertEqual(failed, 0)
        
        # Validate that the valid student was committed
        students = search_students("Valid1")
        self.assertEqual(len(students), 1)
        
        # Validate staging table now contains only the invalid record
        self.assertEqual(len(get_staging_by_status("Valid")), 0)
        self.assertEqual(len(get_staging_by_status("Error")), 1)

if __name__ == "__main__":
    unittest.main()
