import os
import sys
import time
import random
import sqlite3
import datetime
import zipfile
import shutil
import psutil

# Ensure sys path includes the project root
sys.path.append(os.path.abspath(os.path.dirname(os.path.dirname(__file__))))

from src.database.connection import set_db_path, initialize_database, get_connection, close_thread_connection
from src.database.queries import (
    add_course, add_student, enroll_student, add_fee_payment, 
    search_students, get_courses, get_dashboard_stats
)
from src.engines.excel_export import export_all_data_to_excel
from src.engines.backup import perform_backup, restore_backup
from src.utils.config import load_settings, save_settings

def generate_stress_data(db_path):
    print("Initializing Database Schema...")
    set_db_path(db_path)
    initialize_database()
    
    conn = get_connection()
    cursor = conn.cursor()
    
    print("Generating 100 Courses...")
    start = time.time()
    cursor.execute("BEGIN TRANSACTION;")
    course_ids = []
    for i in range(1, 101):
        cursor.execute(
            "INSERT INTO courses (name, code, description, duration_months, total_fee) VALUES (?, ?, ?, ?, ?);",
            (f"Course Pro {i}", f"CRS-{i:03d}", f"Description for Course {i}", random.randint(1, 12), float(random.randint(5000, 30000)))
        )
        course_ids.append(cursor.lastrowid)
    conn.commit()
    print(f"Generated 100 courses in {time.time() - start:.3f}s")
    
    print("Generating 5000 Students...")
    start = time.time()
    cursor.execute("BEGIN TRANSACTION;")
    student_ids = []
    for i in range(1, 5001):
        cursor.execute(
            "INSERT INTO students (first_name, last_name, email, phone, dob, gender, address, status) VALUES (?, ?, ?, ?, ?, ?, ?, ?);",
            (f"John{i}", f"Doe{i}", f"student{i}@example.com", f"98765432{i:02d}", "2000-01-01", random.choice(["Male", "Female", "Other"]), f"Street Address {i}", "Active")
        )
        student_ids.append(cursor.lastrowid)
    conn.commit()
    print(f"Generated 5000 students in {time.time() - start:.3f}s")
    
    print("Generating 5000 Enrollments...")
    start = time.time()
    cursor.execute("BEGIN TRANSACTION;")
    enrollment_ids = []
    for s_id in student_ids:
        c_id = random.choice(course_ids)
        # Fetch course fee
        cursor.execute("SELECT total_fee FROM courses WHERE id = ?;", (c_id,))
        base_fee = cursor.fetchone()[0]
        discount = float(random.choice([0, 500, 1000, 1500]))
        net_fee = base_fee - discount
        cursor.execute(
            "INSERT INTO enrollments (student_id, course_id, discount, net_fee, status) VALUES (?, ?, ?, ?, ?);",
            (s_id, c_id, discount, net_fee, "Active")
        )
        enrollment_ids.append(cursor.lastrowid)
    conn.commit()
    print(f"Generated 5000 enrollments in {time.time() - start:.3f}s")
    
    print("Generating 20000 Payments...")
    start = time.time()
    cursor.execute("BEGIN TRANSACTION;")
    for i in range(1, 20001):
        e_id = random.choice(enrollment_ids)
        amount = float(random.randint(100, 1000))
        method = random.choice(["Cash", "Card", "UPI", "Bank Transfer"])
        receipt = f"REC-STRESS-{i:05d}"
        cursor.execute(
            "INSERT INTO fee_payments (enrollment_id, amount_paid, payment_method, receipt_number, remarks) VALUES (?, ?, ?, ?, ?);",
            (e_id, amount, method, receipt, f"Stress payment installment {i}")
        )
    conn.commit()
    print(f"Generated 20000 payments in {time.time() - start:.3f}s")
    
    print("Generating 500 Leads...")
    start = time.time()
    cursor.execute("BEGIN TRANSACTION;")
    for i in range(1, 501):
        c_interested = random.choice(course_ids)
        cursor.execute(
            "INSERT INTO leads (first_name, last_name, phone, email, source, course_interested_id, status, remarks) VALUES (?, ?, ?, ?, ?, ?, ?, ?);",
            (f"LeadFirst{i}", f"LeadLast{i}", f"9998887{i:03d}", f"lead{i}@example.com", random.choice(["Website", "Walk-in", "Reference"]), c_interested, "New", f"Lead remarks {i}")
        )
    conn.commit()
    print(f"Generated 500 leads in {time.time() - start:.3f}s")
    
    cursor.close()
    
def validate_data_integrity():
    print("\n=== RUNNING DATA INTEGRITY CHECKS ===")
    conn = get_connection()
    cursor = conn.cursor()
    
    # 1. Verify row counts
    cursor.execute("SELECT COUNT(*) FROM students;")
    students_count = cursor.fetchone()[0]
    cursor.execute("SELECT COUNT(*) FROM courses;")
    courses_count = cursor.fetchone()[0]
    cursor.execute("SELECT COUNT(*) FROM enrollments;")
    enrollments_count = cursor.fetchone()[0]
    cursor.execute("SELECT COUNT(*) FROM fee_payments;")
    payments_count = cursor.fetchone()[0]
    cursor.execute("SELECT COUNT(*) FROM leads;")
    leads_count = cursor.fetchone()[0]
    
    print(f"Record verification: Students={students_count}, Courses={courses_count}, Enrollments={enrollments_count}, Payments={payments_count}, Leads={leads_count}")
    
    # Assert counts
    assert students_count == 5000, f"Expected 5000 students, found {students_count}"
    assert courses_count == 100, f"Expected 100 courses, found {courses_count}"
    assert enrollments_count == 5000, f"Expected 5000 enrollments, found {enrollments_count}"
    assert payments_count == 20000, f"Expected 20000 payments, found {payments_count}"
    assert leads_count == 500, f"Expected 500 leads, found {leads_count}"
    print("[PASS] Row counts validated.")
    
    # 2. Check for duplicate student phone numbers
    cursor.execute("SELECT phone, COUNT(*) FROM students GROUP BY phone HAVING COUNT(*) > 1;")
    duplicates = cursor.fetchall()
    assert len(duplicates) == 0, f"Found duplicate student phone numbers: {duplicates}"
    print("[PASS] No duplicate student records.")
    
    # 3. Check for orphan enrollments
    cursor.execute("""
        SELECT e.id FROM enrollments e
        LEFT JOIN students s ON e.student_id = s.id
        LEFT JOIN courses c ON e.course_id = c.id
        WHERE s.id IS NULL OR c.id IS NULL;
    """)
    orphans = cursor.fetchall()
    assert len(orphans) == 0, f"Found orphan enrollments: {orphans}"
    print("[PASS] No orphan enrollments.")
    
    # 4. Check for fee payment mismatches
    cursor.execute("""
        SELECT p.id FROM fee_payments p
        LEFT JOIN enrollments e ON p.enrollment_id = e.id
        WHERE e.id IS NULL;
    """)
    orphan_payments = cursor.fetchall()
    assert len(orphan_payments) == 0, f"Found payments without enrollments: {orphan_payments}"
    print("[PASS] No payment mismatches (all payments bound to valid enrollments).")
    
    cursor.close()
    
def run_latency_and_stress_tests(excel_out, backup_dir, reports_dir):
    print("\n=== RUNNING LATENCY & PERFORMANCE MEASUREMENTS ===")
    
    # 1. Measure Startup/DB Connection Latency
    start = time.time()
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute("SELECT 1;")
    cursor.fetchone()
    cursor.close()
    startup_duration = time.time() - start
    print(f"Database Initialization/Ping latency: {startup_duration * 1000:.2f} ms")
    
    # 2. Measure Search Latency
    search_queries = [f"John{random.randint(1, 5000)}" for _ in range(50)]
    start = time.time()
    for q in search_queries:
        search_students(q)
    search_duration = (time.time() - start) / 50
    print(f"Average Student Search latency (50 samples): {search_duration * 1000:.2f} ms")
    
    # 3. Measure Excel Export Duration
    start = time.time()
    success, err = export_all_data_to_excel(excel_out)
    export_duration = time.time() - start
    assert success, f"Excel Export failed: {err}"
    print(f"Excel Export duration (5000 students, 100 courses, 20000 payments): {export_duration:.3f} s")
    
    # 4. Measure Backup Execution Duration
    settings = load_settings()
    settings["backup_directory"] = backup_dir
    settings["reports_directory"] = reports_dir
    save_settings(settings)
    
    start = time.time()
    success, zip_path, err = perform_backup()
    backup_duration = time.time() - start
    assert success, f"Backup execution failed: {err}"
    print(f"Backup compilation duration (ZIP file output): {backup_duration:.3f} s")
    
    # 5. Measure RAM Usage of current process
    process = psutil.Process(os.getpid())
    ram_usage_mb = process.memory_info().rss / (1024 * 1024)
    print(f"Current Process RAM footprint (Resident Working Set): {ram_usage_mb:.2f} MB")
    
    # 6. Verify Backup Integrity (Decompress and verify rows)
    print("\n=== VERIFYING BACKUP CORRUPTION AND RESTORE INTEGRITY ===")
    restore_dir = os.path.join(os.path.dirname(backup_dir), "restored_verify")
    if os.path.exists(restore_dir):
        shutil.rmtree(restore_dir)
        
    # Use our newly added restore_backup function containing Zip Slip protection!
    success, err = restore_backup(zip_path, restore_dir)
    assert success, f"Secure backup restoration failed: {err}"
    print("[PASS] Secure restoration completed successfully.")
    
    # Verify restored SQLite DB contents
    restored_db_path = os.path.join(restore_dir, "academyos.db")
    assert os.path.exists(restored_db_path), "Restored database file not found!"
    
    r_conn = sqlite3.connect(restored_db_path)
    r_cursor = r_conn.cursor()
    r_cursor.execute("SELECT COUNT(*) FROM students;")
    r_students = r_cursor.fetchone()[0]
    r_cursor.execute("SELECT COUNT(*) FROM courses;")
    r_courses = r_cursor.fetchone()[0]
    r_cursor.execute("SELECT COUNT(*) FROM enrollments;")
    r_enrollments = r_cursor.fetchone()[0]
    r_cursor.execute("SELECT COUNT(*) FROM fee_payments;")
    r_payments = r_cursor.fetchone()[0]
    r_cursor.execute("SELECT COUNT(*) FROM leads;")
    r_leads = r_cursor.fetchone()[0]
    r_cursor.close()
    r_conn.close()
    
    print(f"Restored Record counts: Students={r_students}, Courses={r_courses}, Enrollments={r_enrollments}, Payments={r_payments}, Leads={r_leads}")
    assert r_students == 5000, "Student counts mismatch in restored database!"
    assert r_courses == 100, "Course counts mismatch in restored database!"
    assert r_enrollments == 5000, "Enrollments counts mismatch in restored database!"
    assert r_payments == 20000, "Payments counts mismatch in restored database!"
    assert r_leads == 500, "Leads counts mismatch in restored database!"
    print("[PASS] Restore contents match original source counts exactly. Zero database corruption.")
    
    # Clean up restored directory
    if os.path.exists(restore_dir):
        shutil.rmtree(restore_dir)

    return {
        "startup_ms": startup_duration * 1000,
        "search_ms": search_duration * 1000,
        "export_sec": export_duration,
        "backup_sec": backup_duration,
        "ram_mb": ram_usage_mb
    }

def main():
    print("=== STARTING STRESS AND INTEGRITY VALIDATION PROCESS ===")
    
    # Setup paths inside temp directory
    temp_dir = os.path.join(os.path.abspath(os.path.dirname(__file__)), "stress_temp")
    os.makedirs(temp_dir, exist_ok=True)
    
    test_db = os.path.join(temp_dir, "stress_test.db")
    excel_out = os.path.join(temp_dir, "stress_export.xlsx")
    backup_dir = os.path.join(temp_dir, "backups")
    reports_dir = os.path.join(temp_dir, "reports")
    
    os.makedirs(backup_dir, exist_ok=True)
    os.makedirs(reports_dir, exist_ok=True)
    
    if os.path.exists(test_db):
        os.remove(test_db)
        
    try:
        generate_stress_data(test_db)
        validate_data_integrity()
        metrics = run_latency_and_stress_tests(excel_out, backup_dir, reports_dir)
        
        print("\n=== PERFORMANCE RESULTS SUMMARY ===")
        print(f"  Startup Latency:    {metrics['startup_ms']:.2f} ms")
        print(f"  Search Latency:     {metrics['search_ms']:.2f} ms")
        print(f"  Export Duration:    {metrics['export_sec']:.3f} s")
        print(f"  Backup Duration:    {metrics['backup_sec']:.3f} s")
        print(f"  RAM Usage:          {metrics['ram_mb']:.2f} MB")
        print("=====================================================")
        print("ALL VALIDATIONS PASSED. STRESS TEST SUCCESSFUL.")
    finally:
        # Close connection and clean up temp folder
        close_thread_connection()
        if os.path.exists(temp_dir):
            shutil.rmtree(temp_dir)

if __name__ == "__main__":
    main()
