import json
import sqlite3
import logging
from src.database.connection import get_connection

# --- AUDIT LOGS ---
def log_action(action: str, details: dict = None) -> bool:
    """Insert a record into the audit logs table for tracing user activities."""
    try:
        conn = get_connection()
        cursor = conn.cursor()
        details_str = json.dumps(details) if details else None
        
        # Determine local hostname/IP if possible
        import socket
        try:
            hostname = socket.gethostname()
        except Exception:
            hostname = "local"
            
        cursor.execute(
            """
            INSERT INTO audit_logs (user_action, details, ip_address)
            VALUES (?, ?, ?);
            """,
            (action, details_str, hostname)
        )
        conn.commit()
        cursor.close()
        return True
    except Exception as e:
        logging.error(f"Audit log insertion failed: {e}")
        return False

# --- COURSES ---
def add_course(name: str, code: str, description: str, duration_months: int, total_fee: float) -> int:
    """Add a new course record. Returns the new course ID."""
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute(
        """
        INSERT INTO courses (name, code, description, duration_months, total_fee)
        VALUES (?, ?, ?, ?, ?);
        """,
        (name, code, description, duration_months, total_fee)
    )
    course_id = cursor.lastrowid
    conn.commit()
    cursor.close()
    
    log_action("ADD_COURSE", {"course_id": course_id, "name": name, "code": code})
    return course_id

def update_course(course_id: int, name: str, code: str, description: str, duration_months: int, total_fee: float) -> bool:
    """Update course details."""
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute(
        """
        UPDATE courses 
        SET name = ?, code = ?, description = ?, duration_months = ?, total_fee = ?, updated_at = datetime('now', 'localtime')
        WHERE id = ?;
        """,
        (name, code, description, duration_months, total_fee, course_id)
    )
    success = cursor.rowcount > 0
    conn.commit()
    cursor.close()
    
    if success:
        log_action("UPDATE_COURSE", {"course_id": course_id, "name": name, "code": code})
    return success

def delete_course(course_id: int) -> bool:
    """Delete a course."""
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute("DELETE FROM courses WHERE id = ?;", (course_id,))
    success = cursor.rowcount > 0
    conn.commit()
    cursor.close()
    
    if success:
        log_action("DELETE_COURSE", {"course_id": course_id})
    return success

def get_courses() -> list:
    """Fetch all courses."""
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute("SELECT * FROM courses ORDER BY name ASC;")
    rows = cursor.fetchall()
    cursor.close()
    return [dict(r) for r in rows]

# --- STUDENTS ---
def add_student(first_name: str, last_name: str, email: str, phone: str, dob: str, gender: str, address: str, admission_date: str = None, status: str = 'Active') -> int:
    """Add a new student profile. Returns the student ID."""
    conn = get_connection()
    cursor = conn.cursor()
    
    if admission_date:
        cursor.execute(
            """
            INSERT INTO students (first_name, last_name, email, phone, dob, gender, address, admission_date, status)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?);
            """,
            (first_name, last_name, email, phone, dob, gender, address, admission_date, status)
        )
    else:
        cursor.execute(
            """
            INSERT INTO students (first_name, last_name, email, phone, dob, gender, address, status)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?);
            """,
            (first_name, last_name, email, phone, dob, gender, address, status)
        )
        
    student_id = cursor.lastrowid
    conn.commit()
    cursor.close()
    
    log_action("ADD_STUDENT", {"student_id": student_id, "first_name": first_name, "last_name": last_name, "phone": phone})
    return student_id

def update_student(student_id: int, first_name: str, last_name: str, email: str, phone: str, dob: str, gender: str, address: str, status: str) -> bool:
    """Update student profile details."""
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute(
        """
        UPDATE students
        SET first_name = ?, last_name = ?, email = ?, phone = ?, dob = ?, gender = ?, address = ?, status = ?, updated_at = datetime('now', 'localtime')
        WHERE id = ?;
        """,
        (first_name, last_name, email, phone, dob, gender, address, status, student_id)
    )
    success = cursor.rowcount > 0
    conn.commit()
    cursor.close()
    
    if success:
        log_action("UPDATE_STUDENT", {"student_id": student_id, "first_name": first_name, "last_name": last_name, "status": status})
    return success

def delete_student(student_id: int) -> bool:
    """Delete a student profile (cascades to enrollments)."""
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute("DELETE FROM students WHERE id = ?;", (student_id,))
    success = cursor.rowcount > 0
    conn.commit()
    cursor.close()
    
    if success:
        log_action("DELETE_STUDENT", {"student_id": student_id})
    return success

def search_students(query_str: str) -> list:
    """Search students matching name, email, or phone. Case-insensitive."""
    conn = get_connection()
    cursor = conn.cursor()
    
    if not query_str:
        cursor.execute("SELECT * FROM students ORDER BY last_name ASC, first_name ASC LIMIT 200;")
    else:
        like_query = f"%{query_str}%"
        cursor.execute(
            """
            SELECT * FROM students
            WHERE first_name LIKE ? OR last_name LIKE ? OR phone LIKE ? OR email LIKE ?
            ORDER BY last_name ASC, first_name ASC;
            """,
            (like_query, like_query, like_query, like_query)
        )
    rows = cursor.fetchall()
    cursor.close()
    return [dict(r) for r in rows]

def get_student_by_id(student_id: int) -> dict:
    """Fetch a single student by ID."""
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute("SELECT * FROM students WHERE id = ?;", (student_id,))
    row = cursor.fetchone()
    cursor.close()
    return dict(row) if row else None

# --- ENROLLMENTS ---
def enroll_student(student_id: int, course_id: int, discount: float, net_fee: float, enrollment_date: str = None) -> int:
    """Enroll a student in a course."""
    conn = get_connection()
    cursor = conn.cursor()
    
    if enrollment_date:
        cursor.execute(
            """
            INSERT INTO enrollments (student_id, course_id, discount, net_fee, enrollment_date)
            VALUES (?, ?, ?, ?, ?);
            """,
            (student_id, course_id, discount, net_fee, enrollment_date)
        )
    else:
        cursor.execute(
            """
            INSERT INTO enrollments (student_id, course_id, discount, net_fee)
            VALUES (?, ?, ?, ?);
            """,
            (student_id, course_id, discount, net_fee)
        )
        
    enrollment_id = cursor.lastrowid
    conn.commit()
    cursor.close()
    
    log_action("ENROLL_STUDENT", {"enrollment_id": enrollment_id, "student_id": student_id, "course_id": course_id})
    return enrollment_id

def update_enrollment_status(enrollment_id: int, status: str) -> bool:
    """Update enrollment status (Active, Completed, Dropped)."""
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute(
        """
        UPDATE enrollments
        SET status = ?, updated_at = datetime('now', 'localtime')
        WHERE id = ?;
        """,
        (status, enrollment_id)
    )
    success = cursor.rowcount > 0
    conn.commit()
    cursor.close()
    
    if success:
        log_action("UPDATE_ENROLLMENT_STATUS", {"enrollment_id": enrollment_id, "status": status})
    return success

def get_student_enrollments(student_id: int) -> list:
    """Fetch all course enrollments for a specific student."""
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute(
        """
        SELECT e.*, c.name as course_name, c.code as course_code, c.total_fee as course_base_fee
        FROM enrollments e
        JOIN courses c ON e.course_id = c.id
        WHERE e.student_id = ?;
        """,
        (student_id,)
    )
    rows = cursor.fetchall()
    cursor.close()
    return [dict(r) for r in rows]

# --- FEE PAYMENTS ---
def add_fee_payment(enrollment_id: int, amount_paid: float, payment_method: str, receipt_number: str, remarks: str, payment_date: str = None) -> int:
    """Record a fee payment. Returns the payment ID."""
    conn = get_connection()
    cursor = conn.cursor()
    
    if payment_date:
        cursor.execute(
            """
            INSERT INTO fee_payments (enrollment_id, amount_paid, payment_date, payment_method, receipt_number, remarks)
            VALUES (?, ?, ?, ?, ?, ?);
            """,
            (enrollment_id, amount_paid, payment_date, payment_method, receipt_number, remarks)
        )
    else:
        cursor.execute(
            """
            INSERT INTO fee_payments (enrollment_id, amount_paid, payment_method, receipt_number, remarks)
            VALUES (?, ?, ?, ?, ?);
            """,
            (enrollment_id, amount_paid, payment_method, receipt_number, remarks)
        )
        
    payment_id = cursor.lastrowid
    conn.commit()
    cursor.close()
    
    log_action("COLLECT_FEE", {"payment_id": payment_id, "enrollment_id": enrollment_id, "amount": amount_paid, "receipt": receipt_number})
    return payment_id

def get_payments_by_enrollment(enrollment_id: int) -> list:
    """Fetch all fee payments made for an enrollment."""
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute(
        """
        SELECT * FROM fee_payments
        WHERE enrollment_id = ?
        ORDER BY payment_date DESC, id DESC;
        """,
        (enrollment_id,)
    )
    rows = cursor.fetchall()
    cursor.close()
    return [dict(r) for r in rows]

def get_all_payments_joined(limit: int = 500) -> list:
    """Fetch payments list containing student and course names for dashboard logging."""
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute(
        """
        SELECT p.*, s.first_name, s.last_name, c.name as course_name
        FROM fee_payments p
        JOIN enrollments e ON p.enrollment_id = e.id
        JOIN students s ON e.student_id = s.id
        JOIN courses c ON e.course_id = c.id
        ORDER BY p.payment_date DESC, p.id DESC
        LIMIT ?;
        """,
        (limit,)
    )
    rows = cursor.fetchall()
    cursor.close()
    return [dict(r) for r in rows]

# --- LEADS ---
def add_lead(first_name: str, last_name: str, phone: str, email: str, source: str, course_interested_id: int = None, status: str = 'New', follow_up_date: str = None, remarks: str = None) -> int:
    """Add a new lead / enquiry. Returns lead ID."""
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute(
        """
        INSERT INTO leads (first_name, last_name, phone, email, source, course_interested_id, status, follow_up_date, remarks)
        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?);
        """,
        (first_name, last_name, phone, email, source, course_interested_id, status, follow_up_date, remarks)
    )
    lead_id = cursor.lastrowid
    conn.commit()
    cursor.close()
    
    log_action("ADD_LEAD", {"lead_id": lead_id, "first_name": first_name, "last_name": last_name, "phone": phone})
    return lead_id

def update_lead(lead_id: int, first_name: str, last_name: str, phone: str, email: str, source: str, course_interested_id: int, status: str, follow_up_date: str, remarks: str) -> bool:
    """Update lead details."""
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute(
        """
        UPDATE leads
        SET first_name = ?, last_name = ?, phone = ?, email = ?, source = ?, course_interested_id = ?, status = ?, follow_up_date = ?, remarks = ?, updated_at = datetime('now', 'localtime')
        WHERE id = ?;
        """,
        (first_name, last_name, phone, email, source, course_interested_id, status, follow_up_date, remarks, lead_id)
    )
    success = cursor.rowcount > 0
    conn.commit()
    cursor.close()
    
    if success:
        log_action("UPDATE_LEAD", {"lead_id": lead_id, "first_name": first_name, "status": status})
    return success

def search_leads(query_str: str) -> list:
    """Search leads tracking table."""
    conn = get_connection()
    cursor = conn.cursor()
    
    if not query_str:
        cursor.execute(
            """
            SELECT l.*, c.name as course_name 
            FROM leads l
            LEFT JOIN courses c ON l.course_interested_id = c.id
            ORDER BY l.created_at DESC;
            """
        )
    else:
        like_query = f"%{query_str}%"
        cursor.execute(
            """
            SELECT l.*, c.name as course_name 
            FROM leads l
            LEFT JOIN courses c ON l.course_interested_id = c.id
            WHERE l.first_name LIKE ? OR l.last_name LIKE ? OR l.phone LIKE ? OR l.remarks LIKE ?
            ORDER BY l.created_at DESC;
            """,
            (like_query, like_query, like_query, like_query)
        )
    rows = cursor.fetchall()
    cursor.close()
    return [dict(r) for r in rows]

def delete_lead(lead_id: int) -> bool:
    """Remove a lead."""
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute("DELETE FROM leads WHERE id = ?;", (lead_id,))
    success = cursor.rowcount > 0
    conn.commit()
    cursor.close()
    
    if success:
        log_action("DELETE_LEAD", {"lead_id": lead_id})
    return success

# --- STAGING IMPORTS ---
def add_staging_import(import_type: str, raw_data: dict, source_file: str) -> int:
    """Add row to staging imports for user validation staging."""
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute(
        """
        INSERT INTO staging_imports (import_type, raw_data, validation_status, source_file_name)
        VALUES (?, ?, 'Pending', ?);
        """,
        (import_type, json.dumps(raw_data), source_file)
    )
    staging_id = cursor.lastrowid
    conn.commit()
    cursor.close()
    return staging_id

def update_staging_validation(staging_id: int, status: str, errors: dict = None) -> bool:
    """Update staging records with validation messages."""
    conn = get_connection()
    cursor = conn.cursor()
    errors_str = json.dumps(errors) if errors else None
    cursor.execute(
        """
        UPDATE staging_imports
        SET validation_status = ?, validation_errors = ?
        WHERE id = ?;
        """,
        (status, errors_str, staging_id)
    )
    success = cursor.rowcount > 0
    conn.commit()
    cursor.close()
    return success

def get_staging_by_status(status: str = 'Pending') -> list:
    """Fetch staging import rows for UI verification."""
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute("SELECT * FROM staging_imports WHERE validation_status = ? ORDER BY id ASC;", (status,))
    rows = cursor.fetchall()
    cursor.close()
    return [dict(r) for r in rows]

def clear_staging_imports() -> bool:
    """Clear all records from staging imports table."""
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute("DELETE FROM staging_imports;")
    conn.commit()
    cursor.close()
    return True

# --- SYSTEM STATS & REPORTS ---
def get_dashboard_stats() -> dict:
    """Retrieve key metrics for dashboard display (offline friendly)."""
    conn = get_connection()
    cursor = conn.cursor()
    
    stats = {}
    
    # 1. Total Active Students
    cursor.execute("SELECT COUNT(*) FROM students WHERE status = 'Active';")
    stats["active_students"] = cursor.fetchone()[0]
    
    # 2. Total Active Leads
    cursor.execute("SELECT COUNT(*) FROM leads WHERE status IN ('New', 'Contacted', 'Interested');")
    stats["active_leads"] = cursor.fetchone()[0]
    
    # 3. Total Courses
    cursor.execute("SELECT COUNT(*) FROM courses;")
    stats["total_courses"] = cursor.fetchone()[0]
    
    # 4. Financial Sums (Total Net Fees vs Total Fees Paid)
    cursor.execute("SELECT SUM(net_fee) FROM enrollments;")
    total_receivable = cursor.fetchone()[0] or 0.0
    stats["total_receivable"] = total_receivable
    
    cursor.execute("SELECT SUM(amount_paid) FROM fee_payments;")
    total_collected = cursor.fetchone()[0] or 0.0
    stats["total_collected"] = total_collected
    
    stats["pending_receivable"] = max(0.0, total_receivable - total_collected)
    
    cursor.close()
    return stats
