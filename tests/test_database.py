import os
import unittest
import tempfile
from src.database.connection import set_db_path, initialize_database, get_connection, close_thread_connection
from src.database.queries import (
    add_course, get_courses, add_student, search_students, enroll_student, 
    add_fee_payment, get_dashboard_stats, add_lead, search_leads, log_action
)

class TestAcademyOSDatabase(unittest.TestCase):
    def setUp(self):
        # Set up a temporary database file
        self.db_fd, self.db_path = tempfile.mkstemp()
        set_db_path(self.db_path)
        initialize_database()
        
    def tearDown(self):
        # Close database connection and remove temp file
        close_thread_connection()
        os.close(self.db_fd)
        try:
            os.remove(self.db_path)
        except OSError:
            pass
            
    def test_database_initialization(self):
        conn = get_connection()
        cursor = conn.cursor()
        cursor.execute("SELECT name FROM sqlite_master WHERE type='table';")
        tables = [row[0] for row in cursor.fetchall()]
        self.assertIn("students", tables)
        self.assertIn("courses", tables)
        self.assertIn("enrollments", tables)
        self.assertIn("fee_payments", tables)
        self.assertIn("leads", tables)
        self.assertIn("audit_logs", tables)
        cursor.close()
        
    def test_course_crud(self):
        course_id = add_course("Python Desktop Development", "PY-101", "Learn GUI coding", 3, 15000.0)
        self.assertIsNotNone(course_id)
        
        courses = get_courses()
        self.assertEqual(len(courses), 1)
        self.assertEqual(courses[0]["name"], "Python Desktop Development")
        self.assertEqual(courses[0]["code"], "PY-101")
        self.assertEqual(courses[0]["total_fee"], 15000.0)
        
    def test_student_and_enrollment(self):
        # Add a student
        student_id = add_student("John", "Doe", "john.doe@example.com", "9876543210", "2000-01-01", "Male", "Main Street")
        self.assertIsNotNone(student_id)
        
        # Verify search works
        results = search_students("Doe")
        self.assertEqual(len(results), 1)
        self.assertEqual(results[0]["first_name"], "John")
        
        # Add course and enrollment
        course_id = add_course("C++ Programming", "CPP-202", "Learn standard C++", 4, 18000.0)
        enrollment_id = enroll_student(student_id, course_id, discount=2000.0, net_fee=16000.0)
        self.assertIsNotNone(enrollment_id)
        
        # Record a payment
        payment_id = add_fee_payment(enrollment_id, amount_paid=5000.0, payment_method="Cash", receipt_number="REC-1001", remarks="First Installment")
        self.assertIsNotNone(payment_id)
        
        # Check dashboard stats
        stats = get_dashboard_stats()
        self.assertEqual(stats["active_students"], 1)
        self.assertEqual(stats["total_courses"], 1)
        self.assertEqual(stats["total_receivable"], 16000.0)
        self.assertEqual(stats["total_collected"], 5000.0)
        self.assertEqual(stats["pending_receivable"], 11000.0)
        
    def test_leads_module(self):
        lead_id = add_lead("Sarah", "Smith", "9988776655", "sarah@gmail.com", "Walk-in", None, "New", None, "Interested in python")
        self.assertIsNotNone(lead_id)
        
        results = search_leads("Sarah")
        self.assertEqual(len(results), 1)
        self.assertEqual(results[0]["phone"], "9988776655")
        
    def test_audit_logs(self):
        log_action("TEST_ACTION", {"key": "val"})
        conn = get_connection()
        cursor = conn.cursor()
        cursor.execute("SELECT user_action, details FROM audit_logs ORDER BY id DESC LIMIT 1;")
        row = cursor.fetchone()
        self.assertEqual(row[0], "TEST_ACTION")
        self.assertIn("key", row[1])
        cursor.close()

if __name__ == "__main__":
    unittest.main()
