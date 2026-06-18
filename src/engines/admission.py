import re
import datetime
import logging
from src.database.queries import add_student, update_student, get_student_by_id

EMAIL_REGEX = r'^[\w\.-]+@[\w\.-]+\.\w+$'

class AdmissionValidationError(Exception):
    pass

def validate_student_data(first_name: str, last_name: str, email: str, phone: str, dob: str, gender: str, status: str):
    """Validate student fields. Raises AdmissionValidationError if invalid."""
    if not first_name.strip():
        raise AdmissionValidationError("First name cannot be empty.")
    if not last_name.strip():
        raise AdmissionValidationError("Last name cannot be empty.")
        
    # Phone number validation (e.g. 10 digits minimum, numeric)
    phone_clean = re.sub(r'[\s\-\(\)\+]', '', phone)
    if not phone_clean.isdigit() or len(phone_clean) < 10:
        raise AdmissionValidationError("Phone number must contain at least 10 digits.")
        
    # Email validation (optional but must be valid format if provided)
    if email and not re.match(EMAIL_REGEX, email):
        raise AdmissionValidationError("Invalid email address format.")
        
    # Date of birth validation (YYYY-MM-DD)
    try:
        dob_date = datetime.datetime.strptime(dob, "%Y-%m-%d").date()
        if dob_date >= datetime.date.today():
            raise AdmissionValidationError("Date of birth must be in the past.")
    except ValueError:
        raise AdmissionValidationError("Date of birth must be in YYYY-MM-DD format.")
        
    # Gender validation
    if gender not in ('Male', 'Female', 'Other'):
        raise AdmissionValidationError("Gender must be one of: Male, Female, Other.")
        
    # Status validation
    if status not in ('Active', 'Inactive', 'Suspended', 'Graduated'):
        raise AdmissionValidationError("Invalid student status value.")

def register_new_student(first_name: str, last_name: str, email: str, phone: str, dob: str, gender: str, address: str, admission_date: str = None) -> int:
    """
    Validate and register a new student.
    Returns the new student ID.
    """
    first_name = first_name.strip()
    last_name = last_name.strip()
    email = email.strip() if email else None
    phone = phone.strip()
    address = address.strip() if address else None
    
    validate_student_data(first_name, last_name, email, phone, dob, gender, 'Active')
    
    # We can perform additional business checks like duplicate active phones
    # Select from database checks if phone already registered (optional, let's keep it clean)
    
    student_id = add_student(
        first_name=first_name,
        last_name=last_name,
        email=email,
        phone=phone,
        dob=dob,
        gender=gender,
        address=address,
        admission_date=admission_date,
        status='Active'
    )
    return student_id

def modify_existing_student(student_id: int, first_name: str, last_name: str, email: str, phone: str, dob: str, gender: str, address: str, status: str) -> bool:
    """
    Validate and update an existing student profile.
    """
    # Verify student exists
    student = get_student_by_id(student_id)
    if not student:
        raise AdmissionValidationError(f"Student with ID {student_id} not found.")
        
    first_name = first_name.strip()
    last_name = last_name.strip()
    email = email.strip() if email else None
    phone = phone.strip()
    address = address.strip() if address else None
    
    validate_student_data(first_name, last_name, email, phone, dob, gender, status)
    
    success = update_student(
        student_id=student_id,
        first_name=first_name,
        last_name=last_name,
        email=email,
        phone=phone,
        dob=dob,
        gender=gender,
        address=address,
        status=status
    )
    return success
