import logging
from src.database.connection import get_connection

def get_enrollment_financials(enrollment_id: int) -> dict:
    """
    Get detailed financial metrics for an enrollment.
    Returns a dictionary of fees, discounts, amount paid, and outstanding dues.
    """
    conn = get_connection()
    cursor = conn.cursor()
    
    # 1. Fetch enrollment details
    cursor.execute(
        """
        SELECT e.*, c.name as course_name, c.total_fee as course_base_fee, s.first_name, s.last_name, s.phone
        FROM enrollments e
        JOIN courses c ON e.course_id = c.id
        JOIN students s ON e.student_id = s.id
        WHERE e.id = ?;
        """,
        (enrollment_id,)
    )
    row = cursor.fetchone()
    if not row:
        cursor.close()
        return {}
        
    enrollment = dict(row)
    
    # 2. Fetch sum of payments
    cursor.execute("SELECT SUM(amount_paid) FROM fee_payments WHERE enrollment_id = ?;", (enrollment_id,))
    total_paid = cursor.fetchone()[0] or 0.0
    
    cursor.close()
    
    net_fee = enrollment["net_fee"]
    discount = enrollment["discount"]
    due_amount = max(0.0, net_fee - total_paid)
    
    return {
        "enrollment_id": enrollment_id,
        "student_id": enrollment["student_id"],
        "student_name": f"{enrollment['first_name']} {enrollment['last_name']}",
        "student_phone": enrollment["phone"],
        "course_name": enrollment["course_name"],
        "course_base_fee": enrollment["course_base_fee"],
        "discount": discount,
        "net_fee": net_fee,
        "total_paid": total_paid,
        "due_amount": due_amount,
        "status": enrollment["status"]
    }

def get_outstanding_fees_list() -> list:
    """
    Fetch a list of all enrollments with an outstanding balance (dues > 0).
    Sorted by highest dues first.
    """
    conn = get_connection()
    cursor = conn.cursor()
    
    cursor.execute(
        """
        SELECT 
            e.id as enrollment_id, 
            e.net_fee,
            e.status as enrollment_status,
            s.id as student_id,
            s.first_name, 
            s.last_name, 
            s.phone,
            c.name as course_name,
            COALESCE((SELECT SUM(amount_paid) FROM fee_payments WHERE enrollment_id = e.id), 0.0) as total_paid
        FROM enrollments e
        JOIN students s ON e.student_id = s.id
        JOIN courses c ON e.course_id = c.id
        WHERE e.status = 'Active'
        ORDER BY s.last_name ASC, s.first_name ASC;
        """
    )
    rows = cursor.fetchall()
    cursor.close()
    
    outstanding = []
    for r in rows:
        item = dict(r)
        due = max(0.0, item["net_fee"] - item["total_paid"])
        if due > 0:
            item["total_paid"] = item["total_paid"]
            item["due_amount"] = due
            item["student_name"] = f"{item['first_name']} {item['last_name']}"
            outstanding.append(item)
            
    # Sort by due amount descending
    outstanding.sort(key=lambda x: x["due_amount"], reverse=True)
    return outstanding
