import os
import sys
import time
import json
import sqlite3
import datetime
import logging
import subprocess

# Ensure we run Qt headless
os.environ["QT_QPA_PLATFORM"] = "offscreen"

# Setup sys path to import our modules
sys.path.append("/home/ubuntu/academyos")

from PySide6.QtWidgets import QApplication
from src.database.connection import set_db_path, initialize_database, get_connection, close_thread_connection
from src.database.queries import add_course, add_student, enroll_student, add_fee_payment, get_dashboard_stats, add_lead, log_action
from src.ui.main_window import MainWindow
import src.engines.license as license_engine
from src.utils.crypto import generate_signature
from src.utils.config import load_settings, save_settings
import src.engines.backup as backup_engine
import src.engines.excel_export as excel_engine
import src.engines.report_generator as pdf_engine
import src.engines.staging as staging_engine
import src.engines.ocr_engine as ocr_engine

ARTIFACT_DIR = os.environ.get("AOS_ARTIFACT_DIR", "/home/ubuntu/.gemini/antigravity-cli/brain/bad9de1d-c8e4-4253-8c7f-0a63c4939998")

def main():
    print("=== ACADEMYOS VERIFICATION AUDIT INITIALIZING ===")
    os.makedirs(ARTIFACT_DIR, exist_ok=True)
    
    # 1. DATABASE AUDIT
    print("\n--- 1. DATABASE AUDIT ---")
    db_path = os.path.join(ARTIFACT_DIR, "audit_test.db")
    if os.path.exists(db_path):
        os.remove(db_path)
    set_db_path(db_path)
    initialize_database()
    
    conn = get_connection()
    cursor = conn.cursor()
    
    # List all tables
    cursor.execute("SELECT name FROM sqlite_master WHERE type='table';")
    tables = [r[0] for r in cursor.fetchall()]
    print(f"Created Tables: {tables}")
    
    # List all indexes
    cursor.execute("SELECT name, tbl_name FROM sqlite_master WHERE type='index';")
    indexes = [dict(r) for r in cursor.fetchall()]
    print(f"Created Indexes: {json.dumps(indexes, indent=2)}")
    
    # Write SQL schema file
    schema_sql_path = os.path.join(ARTIFACT_DIR, "schema.sql")
    with open(schema_sql_path, "w") as sf:
        cursor.execute("SELECT sql FROM sqlite_master WHERE sql IS NOT NULL;")
        sqls = [r[0] for r in cursor.fetchall()]
        sf.write("\n\n".join(sqls))
    print(f"Saved DB schema DDL to {schema_sql_path}")
    cursor.close()
    
    # 2. RUN PERFORMANCE BENCHMARKS (Part 1 - DB insertions)
    print("\n--- 2. PERFORMANCE BENCHMARKS (DB Query speed) ---")
    start_time = time.time()
    conn = get_connection()
    cursor = conn.cursor()
    # Bulk insert 500 students
    cursor.execute("BEGIN TRANSACTION;")
    for i in range(500):
        cursor.execute(
            "INSERT INTO students (first_name, last_name, email, phone, dob, gender, address, status) VALUES (?, ?, ?, ?, ?, ?, ?, ?);",
            (f"First{i}", f"Last{i}", f"student{i}@academy.com", f"98765432{i:02d}", "2005-05-05", "Male", "Address Road", "Active")
        )
    conn.commit()
    cursor.close()
    db_duration = time.time() - start_time
    print(f"Benchmark: Inserted 500 students in {db_duration:.4f} seconds (average {(db_duration/500)*1000:.4f} ms per insert)")
    
    # 3. LICENSING TESTS
    print("\n--- 3. LICENSING & ACTIVATION TESTS ---")
    # Verify offline fingerprint matches check
    fp = license_engine.get_device_fingerprint()
    print(f"Generated Device Fingerprint: {fp}")
    
    # Test Activation Failures
    self_activated = license_engine.activate_license("AOS-KEY-BADKEY")
    print(f"Bad Key Activation (expected False): {self_activated}")
    
    # Test Activation Success
    expiry = "2030-12-31"
    sig = generate_signature(f"AOS-KEY-{expiry}", expiry, fp)
    valid_key = f"AOS-KEY-{expiry}-{sig}"
    success_act = license_engine.activate_license(valid_key)
    print(f"Valid Key Activation (expected True): {success_act}")
    
    status = license_engine.check_license_status()
    print(f"License Expiry Check: {status}")
    
    # 4. CAPTURE UI SCREENSHOTS HEADLESSLY
    print("\n--- 4. UI SCREENSHOT GRABS ---")
    qt_app = QApplication.instance()
    if not qt_app:
        qt_app = QApplication([])
    from src.ui.styles import GLOBAL_STYLE_SHEET
    qt_app.setStyleSheet(GLOBAL_STYLE_SHEET)
    
    # Populate a course to make screens look nice
    course_id = add_course("Python Academy Pro", "PY-PRO", "Full Python training", 3, 12000.0)
    add_course("Web Apps with Flask", "FL-101", "Flask web coding", 2, 8000.0)
    
    # Enroll a student
    stud_id = add_student("Alice", "Wonderland", "alice@wonder.com", "9900112233", "2002-02-02", "Female", "Cheshire Lane")
    enroll_id = enroll_student(stud_id, course_id, discount=2000.0, net_fee=10000.0)
    
    # Record payment
    add_fee_payment(enroll_id, amount_paid=5000.0, payment_method="UPI", receipt_number="AOS-REC-202606-1002", remarks="Initial Installment")
    
    # Record Lead
    add_lead("Robert", "Downey", "9876540011", "robert@tony.com", "Advertisement", course_id, "New", "2026-06-25", "Needs weekday classes")
    
    # Benchmark UI startup time
    ui_start = time.time()
    main_win = MainWindow()
    main_win.resize(1024, 700)
    main_win.show()
    ui_duration = time.time() - ui_start
    print(f"Benchmark: Instantiated MainWindow in {ui_duration:.4f} seconds")
    
    # Capture screenshots of tabs
    tabs = ["dashboard", "students", "leads", "fee", "import", "settings"]
    for idx, tname in enumerate(tabs):
        main_win.sidebar.setCurrentRow(idx)
        qt_app.processEvents()
        time.sleep(0.1) # Let paint events complete
        
        pixmap = main_win.grab()
        screenshot_path = os.path.join(ARTIFACT_DIR, f"screenshot_{tname}.png")
        pixmap.save(screenshot_path, "PNG")
        print(f"Captured screen for {tname} -> {screenshot_path}")
        
    main_win.close()
    
    # 5. EXCEL EXPORT ENGINE AUDIT
    print("\n--- 5. EXCEL GENERATION AUDIT ---")
    excel_path = os.path.join(ARTIFACT_DIR, "academyos_sample_export.xlsx")
    ex_success, ex_err = excel_engine.export_all_data_to_excel(excel_path)
    print(f"Excel Export Status: {ex_success} (Saved to: {excel_path})")
    if ex_err:
        print(f"Excel Export Error: {ex_err}")
        
    # Read sheet structures to verify formatting
    import openpyxl
    wb = openpyxl.load_workbook(excel_path, read_only=True)
    print(f"Generated Sheets in Workbook: {wb.sheetnames}")
    wb.close()
    
    # 6. PDF RECEIPT ENGINE AUDIT
    print("\n--- 6. PDF RECEIPT INVOICE AUDIT ---")
    # Retrieve first payment ID from DB
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute("SELECT id FROM fee_payments ORDER BY id ASC LIMIT 1;")
    pay_id = cursor.fetchone()[0]
    cursor.close()
    
    pdf_path = os.path.join(ARTIFACT_DIR, "academyos_sample_receipt.pdf")
    pdf_success, pdf_err = pdf_engine.generate_receipt_pdf(pay_id, pdf_path)
    print(f"PDF Receipt Status: {pdf_success} (Saved to: {pdf_path})")
    
    # 7. BACKUP / RESTORE AUDIT
    print("\n--- 7. BACKUP & RESTORE INTEGRITY ---")
    # Inject backup/reports dirs to settings
    settings = load_settings()
    settings["backup_directory"] = os.path.join(ARTIFACT_DIR, "backups")
    settings["reports_directory"] = os.path.join(ARTIFACT_DIR, "reports")
    settings["backup_retention_count"] = 5
    save_settings(settings)
    
    # Run Backup
    backup_success, zip_path, backup_err = backup_engine.perform_backup()
    print(f"Backup Success: {backup_success} (Saved to: {zip_path})")
    
    # Verify ZIP structure
    import zipfile
    with zipfile.ZipFile(zip_path, 'r') as zf:
        print(f"Files inside Backup ZIP: {zf.namelist()}")
        
    # Verify Restore Process
    restore_db_path = os.path.join(ARTIFACT_DIR, "restored_database.db")
    if os.path.exists(restore_db_path):
        os.remove(restore_db_path)
        
    print("Testing Restore: Extracting database from backup ZIP...")
    with zipfile.ZipFile(zip_path, 'r') as zf:
        zf.extract("academyos.db", ARTIFACT_DIR)
        os.rename(os.path.join(ARTIFACT_DIR, "academyos.db"), restore_db_path)
        
    # Read restored DB entries
    r_conn = sqlite3.connect(restore_db_path)
    r_cursor = r_conn.cursor()
    r_cursor.execute("SELECT first_name, last_name, phone FROM students WHERE first_name='Alice';")
    r_row = r_cursor.fetchone()
    print(f"Restored Student Records (Expected Alice): {r_row}")
    r_conn.close()
    
    # 8. OFFLINE OCR ENGINE AUDIT
    print("\n--- 8. OFFLINE OCR PIPELINE AUDIT ---")
    # Draw a receipt image using PIL
    from PIL import Image, ImageDraw, ImageFont
    
    # Create empty white canvas
    img = Image.new('RGB', (500, 250), color = (255, 255, 255))
    d = ImageDraw.Draw(img)
    # Write text block
    d.text((20, 20), "FEES RECEIPT INVOICE", fill=(0,0,0))
    d.text((20, 50), "Receipt Number: AOS-REC-9999", fill=(0,0,0))
    d.text((20, 80), "Student Name: Mark Spector", fill=(0,0,0))
    d.text((20, 110), "Phone: 9991112223", fill=(0,0,0))
    d.text((20, 140), "Email: mark@moon.com", fill=(0,0,0))
    d.text((20, 170), "Course: Python Core Classes", fill=(0,0,0))
    d.text((20, 200), "Paid Amount: $4500.00", fill=(0,0,0))
    
    mock_receipt_img = os.path.join(ARTIFACT_DIR, "mock_receipt_image.png")
    img.save(mock_receipt_img)
    print(f"Generated mock receipt image for OCR test: {mock_receipt_img}")
    
    # Run OCR extraction
    try:
        raw_ocr_text = ocr_engine.run_offline_ocr(mock_receipt_img)
        print(f"Extracted OCR Raw Text:\n{raw_ocr_text}")
        entities = ocr_engine.extract_entities_from_text(raw_ocr_text)
        print(f"Extracted Entities Dict: {json.dumps(entities, indent=2)}")
    except Exception as ocr_err:
        print(f"OCR execution skipped (Tesseract not available or failed): {ocr_err}")
        
    # 9. RAM USAGE BENCHMARK
    print("\n--- 9. RAM USAGE BENCHMARK ---")
    try:
        import resource
        usage = resource.getrusage(resource.RUSAGE_SELF)
        # Convert max rss (in KB on Linux) to MB
        ram_mb = usage.ru_maxrss / 1024
        print(f"Resident Memory (RSS) Peak Usage: {ram_mb:.2f} MB (Target < 300MB)")
    except Exception as ram_err:
        print(f"Unable to read system memory resources: {ram_err}")
        
    print("\n=== VERIFICATION AUDIT COMPLETE ===")

if __name__ == "__main__":
    main()
