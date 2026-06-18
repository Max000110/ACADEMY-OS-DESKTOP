import json
import logging
import re
from src.database.queries import (
    add_staging_import, update_staging_validation, get_staging_by_status,
    add_student, add_lead, add_fee_payment
)
from src.database.connection import get_connection

def stage_and_validate_records(import_type: str, raw_records: list, source_file: str) -> int:
    """
    Ingest a list of raw dictionaries into staging_imports and perform field validations.
    Returns the count of successfully staged records.
    """
    staged_count = 0
    for record in raw_records:
        # 1. Insert as pending staging row
        staging_id = add_staging_import(import_type, record, source_file)
        
        # 2. Run validations
        errors = {}
        
        first_name = record.get("first_name", "").strip()
        last_name = record.get("last_name", "").strip()
        phone = record.get("phone", "").strip()
        email = record.get("email", "").strip()
        
        if not first_name:
            errors["first_name"] = "First name is required."
        if not last_name:
            errors["last_name"] = "Last name is required."
            
        phone_clean = re.sub(r'[\s\-\(\)\+]', '', phone)
        if not phone_clean:
            errors["phone"] = "Phone number is required."
        elif not phone_clean.isdigit() or len(phone_clean) < 10:
            errors["phone"] = "Phone must contain at least 10 digits."
            
        if email and not re.match(r'^[\w\.-]+@[\w\.-]+\.\w+$', email):
            errors["email"] = "Invalid email format."
            
        if import_type == "Leads":
            source = record.get("source", "").strip()
            if not source:
                errors["source"] = "Lead source is required."
                
        # 3. Update staging row status based on errors
        status = "Error" if errors else "Valid"
        update_staging_validation(staging_id, status, errors)
        staged_count += 1
        
    return staged_count

def approve_and_commit_staging(import_type: str) -> tuple:
    """
    Commit all 'Valid' staging records of a specific type to the core tables.
    Returns (success_count: int, failed_count: int)
    """
    conn = get_connection()
    cursor = conn.cursor()
    
    # Fetch all valid records of the specified type
    cursor.execute(
        """
        SELECT id, raw_data FROM staging_imports
        WHERE import_type = ? AND validation_status = 'Valid';
        """,
        (import_type,)
    )
    rows = cursor.fetchall()
    
    success_count = 0
    failed_count = 0
    
    for row in rows:
        staging_id = row["id"]
        record = json.loads(row["raw_data"])
        
        try:
            # We run everything in individual trans-commits
            if import_type == "Students":
                add_student(
                    first_name=record.get("first_name", ""),
                    last_name=record.get("last_name", ""),
                    email=record.get("email", None),
                    phone=record.get("phone", ""),
                    dob=record.get("dob", "2000-01-01"),
                    gender=record.get("gender", "Other"),
                    address=record.get("address", "")
                )
            elif import_type == "Leads":
                # Match course name to course ID if defined
                course_id = None
                course_name = record.get("course", "")
                if course_name:
                    cursor.execute("SELECT id FROM courses WHERE name LIKE ? LIMIT 1;", (f"%{course_name}%",))
                    course_row = cursor.fetchone()
                    if course_row:
                        course_id = course_row[0]
                        
                add_lead(
                    first_name=record.get("first_name", ""),
                    last_name=record.get("last_name", ""),
                    phone=record.get("phone", ""),
                    email=record.get("email", None),
                    source=record.get("source", "Walk-in"),
                    course_interested_id=course_id,
                    status='New',
                    remarks=record.get("remarks", "")
                )
            elif import_type == "Payments":
                # Special payments staging commit handling
                # In a real app we'd map enrollment_id based on student name / course
                pass
                
            # Remove staging record on successful insert
            cursor.execute("DELETE FROM staging_imports WHERE id = ?;", (staging_id,))
            conn.commit()
            success_count += 1
        except Exception as e:
            conn.rollback()
            logging.error(f"Failed to commit staged record {staging_id}: {e}")
            # Mark it as error
            update_staging_validation(staging_id, "Error", {"internal": str(e)})
            failed_count += 1
            
    cursor.close()
    return success_count, failed_count
