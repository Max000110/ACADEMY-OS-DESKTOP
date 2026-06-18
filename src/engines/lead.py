import re
import datetime
import logging
from src.database.queries import (
    add_lead, update_lead, search_leads, delete_lead,
    enroll_student
)
from src.engines.admission import register_new_student, AdmissionValidationError

class LeadValidationError(Exception):
    pass

def validate_lead_data(first_name: str, last_name: str, phone: str, email: str, source: str, status: str):
    """Validate lead fields. Raises LeadValidationError if invalid."""
    if not first_name.strip():
        raise LeadValidationError("First name cannot be empty.")
    if not last_name.strip():
        raise LeadValidationError("Last name cannot be empty.")
        
    phone_clean = re.sub(r'[\s\-\(\)\+]', '', phone)
    if not phone_clean.isdigit() or len(phone_clean) < 10:
        raise LeadValidationError("Phone number must contain at least 10 digits.")
        
    if email and not re.match(r'^[\w\.-]+@[\w\.-]+\.\w+$', email):
        raise LeadValidationError("Invalid email address format.")
        
    if not source.strip():
        raise LeadValidationError("Lead source cannot be empty.")
        
    if status not in ('New', 'Contacted', 'Interested', 'Enrolled', 'Lost'):
        raise LeadValidationError("Invalid lead status value.")

def create_lead(first_name: str, last_name: str, phone: str, email: str, source: str, course_id: int = None, follow_up_date: str = None, remarks: str = None) -> int:
    """Create a new lead/enquiry with validation."""
    first_name = first_name.strip()
    last_name = last_name.strip()
    email = email.strip() if email else None
    phone = phone.strip()
    source = source.strip()
    remarks = remarks.strip() if remarks else None
    
    validate_lead_data(first_name, last_name, phone, email, source, 'New')
    
    # Validate follow-up date if provided
    if follow_up_date:
        try:
            datetime.datetime.strptime(follow_up_date, "%Y-%m-%d")
        except ValueError:
            raise LeadValidationError("Follow-up date must be in YYYY-MM-DD format.")
            
    lead_id = add_lead(
        first_name=first_name,
        last_name=last_name,
        phone=phone,
        email=email,
        source=source,
        course_interested_id=course_id,
        status='New',
        follow_up_date=follow_up_date,
        remarks=remarks
    )
    return lead_id

def modify_lead(lead_id: int, first_name: str, last_name: str, phone: str, email: str, source: str, course_id: int, status: str, follow_up_date: str, remarks: str) -> bool:
    """Update lead details."""
    first_name = first_name.strip()
    last_name = last_name.strip()
    email = email.strip() if email else None
    phone = phone.strip()
    source = source.strip()
    remarks = remarks.strip() if remarks else None
    
    validate_lead_data(first_name, last_name, phone, email, source, status)
    
    if follow_up_date:
        try:
            datetime.datetime.strptime(follow_up_date, "%Y-%m-%d")
        except ValueError:
            raise LeadValidationError("Follow-up date must be in YYYY-MM-DD format.")
            
    return update_lead(
        lead_id=lead_id,
        first_name=first_name,
        last_name=last_name,
        phone=phone,
        email=email,
        source=source,
        course_interested_id=course_id,
        status=status,
        follow_up_date=follow_up_date,
        remarks=remarks
    )

def promote_lead_to_student(lead_id: int, dob: str, gender: str, address: str, course_discount: float = 0.0) -> tuple:
    """
    Promote a lead to an admitted student and enroll them in their interested course.
    
    Returns (student_id: int, enrollment_id: int)
    """
    from src.database.connection import get_connection
    conn = get_connection()
    cursor = conn.cursor()
    
    # 1. Fetch the lead
    cursor.execute("SELECT * FROM leads WHERE id = ?;", (lead_id,))
    row = cursor.fetchone()
    if not row:
        raise LeadValidationError(f"Lead with ID {lead_id} not found.")
    lead = dict(row)
    
    if lead["status"] == "Enrolled":
        raise LeadValidationError("This lead has already been enrolled.")
        
    try:
        # We perform everything in a single SQLite transaction
        # 2. Register as a student
        student_id = register_new_student(
            first_name=lead["first_name"],
            last_name=lead["last_name"],
            email=lead["email"],
            phone=lead["phone"],
            dob=dob,
            gender=gender,
            address=address
        )
        
        # 3. Enroll in interested course if defined
        enrollment_id = None
        course_id = lead["course_interested_id"]
        if course_id:
            # Fetch course fee
            cursor.execute("SELECT total_fee FROM courses WHERE id = ?;", (course_id,))
            course_row = cursor.fetchone()
            if course_row:
                base_fee = course_row[0]
                net_fee = max(0.0, base_fee - course_discount)
                enrollment_id = enroll_student(
                    student_id=student_id,
                    course_id=course_id,
                    discount=course_discount,
                    net_fee=net_fee
                )
                
        # 4. Mark lead as enrolled
        cursor.execute(
            "UPDATE leads SET status = 'Enrolled', updated_at = datetime('now', 'localtime') WHERE id = ?;",
            (lead_id,)
        )
        
        conn.commit()
        cursor.close()
        logging.info(f"Successfully promoted lead {lead_id} to student {student_id} with enrollment {enrollment_id}")
        return student_id, enrollment_id
    except Exception as e:
        conn.rollback()
        cursor.close()
        logging.error(f"Failed to promote lead {lead_id}: {e}")
        raise e
