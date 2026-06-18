import os
import logging
from datetime import datetime

from reportlab.lib.pagesizes import letter
from reportlab.lib import colors
from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle, KeepTogether
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib.units import inch

from src.database.connection import get_connection
from src.utils.config import load_settings

def generate_receipt_pdf(payment_id: int, output_path: str) -> tuple:
    """
    Generate a professional PDF receipt for a fee payment.
    
    Returns (success: bool, error_message: str or None)
    """
    try:
        # Create directories
        os.makedirs(os.path.dirname(output_path), exist_ok=True)
        
        # 1. Fetch payment details from database
        conn = get_connection()
        cursor = conn.cursor()
        cursor.execute(
            """
            SELECT 
                p.id as payment_id, p.amount_paid, p.payment_date, p.payment_method, p.receipt_number, p.remarks,
                s.id as student_id, s.first_name, s.last_name, s.phone, s.email,
                c.name as course_name, e.net_fee
            FROM fee_payments p
            JOIN enrollments e ON p.enrollment_id = e.id
            JOIN students s ON e.student_id = s.id
            JOIN courses c ON e.course_id = c.id
            WHERE p.id = ?;
            """,
            (payment_id,)
        )
        row = cursor.fetchone()
        
        if not row:
            cursor.close()
            return False, f"Payment with ID {payment_id} not found."
            
        pay = dict(row)
        
        # 2. Fetch sum of payments made BEFORE or INCLUDING this payment
        cursor.execute(
            """
            SELECT SUM(amount_paid) FROM fee_payments
            WHERE enrollment_id = (SELECT enrollment_id FROM fee_payments WHERE id = ?)
              AND payment_date <= ?;
            """,
            (payment_id, pay["payment_date"])
        )
        cumulative_paid = cursor.fetchone()[0] or 0.0
        cursor.close()
        
        due_amount = max(0.0, pay["net_fee"] - cumulative_paid)
        
        # Load settings for school details
        settings = load_settings()
        school_name = settings.get("institution_name", "AcademyOS Training Center")
        school_phone = settings.get("institution_phone", "")
        school_email = settings.get("institution_email", "")
        school_address = settings.get("institution_address", "")
        
        # 3. Design PDF Doc Structure
        doc = SimpleDocTemplate(
            output_path,
            pagesize=letter,
            rightMargin=0.5 * inch,
            leftMargin=0.5 * inch,
            topMargin=0.5 * inch,
            bottomMargin=0.5 * inch
        )
        
        story = []
        styles = getSampleStyleSheet()
        
        # Create custom styles
        title_style = ParagraphStyle(
            'SchoolTitle',
            parent=styles['Heading1'],
            fontName='Helvetica-Bold',
            fontSize=22,
            textColor=colors.HexColor('#1F497D'),
            spaceAfter=6
        )
        
        subtitle_style = ParagraphStyle(
            'SchoolInfo',
            parent=styles['Normal'],
            fontName='Helvetica',
            fontSize=9,
            textColor=colors.HexColor('#555555'),
            leading=12
        )
        
        receipt_header_style = ParagraphStyle(
            'ReceiptHeader',
            parent=styles['Heading2'],
            fontName='Helvetica-Bold',
            fontSize=16,
            textColor=colors.HexColor('#1F497D'),
            alignment=2, # Right align
            spaceAfter=15
        )
        
        normal_bold = ParagraphStyle(
            'NormalBold',
            parent=styles['Normal'],
            fontName='Helvetica-Bold',
            fontSize=10,
            leading=14
        )
        
        normal_regular = ParagraphStyle(
            'NormalRegular',
            parent=styles['Normal'],
            fontName='Helvetica',
            fontSize=10,
            leading=14
        )
        
        # 4. Header Section Table (Left: Institution Info, Right: Receipt Details)
        school_info = f"<b>{school_name}</b><br/>"
        if school_address: school_info += f"{school_address}<br/>"
        if school_phone: school_info += f"Phone: {school_phone}  "
        if school_email: school_info += f"Email: {school_email}"
        
        receipt_meta = f"<b>FEES RECEIPT</b><br/><font color='#555555' size=9>"
        receipt_meta += f"Receipt No: {pay['receipt_number']}<br/>"
        receipt_meta += f"Date: {pay['payment_date']}<br/>"
        receipt_meta += f"Payment Method: {pay['payment_method']}</font>"
        
        header_table = Table(
            [[Paragraph(school_info, subtitle_style), Paragraph(receipt_meta, ParagraphStyle('RightMeta', parent=subtitle_style, alignment=2))]],
            colWidths=[4.5 * inch, 3.0 * inch]
        )
        header_table.setStyle(TableStyle([
            ('VALIGN', (0,0), (-1,-1), 'TOP'),
            ('BOTTOMPADDING', (0,0), (-1,-1), 10),
        ]))
        story.append(header_table)
        
        # Draw a horizontal line
        line_table = Table([[""]], colWidths=[7.5 * inch])
        line_table.setStyle(TableStyle([
            ('LINEBELOW', (0,0), (-1,-1), 1.5, colors.HexColor('#1F497D')),
            ('BOTTOMPADDING', (0,0), (-1,-1), 15),
        ]))
        story.append(line_table)
        story.append(Spacer(1, 10))
        
        # 5. Student / Enrollment Summary Details Block
        details_data = [
            [
                Paragraph("<b>Student ID:</b>", normal_bold),
                Paragraph(str(pay["student_id"]), normal_regular),
                Paragraph("<b>Student Name:</b>", normal_bold),
                Paragraph(f"{pay['first_name']} {pay['last_name']}", normal_regular)
            ],
            [
                Paragraph("<b>Contact No:</b>", normal_bold),
                Paragraph(pay["phone"], normal_regular),
                Paragraph("<b>Email Address:</b>", normal_bold),
                Paragraph(pay["email"] or "N/A", normal_regular)
            ],
            [
                Paragraph("<b>Enrolled Course:</b>", normal_bold),
                Paragraph(pay["course_name"], normal_regular),
                Paragraph("<b>Date Generated:</b>", normal_bold),
                Paragraph(datetime.now().strftime("%Y-%m-%d"), normal_regular)
            ]
        ]
        
        details_table = Table(details_data, colWidths=[1.2 * inch, 2.3 * inch, 1.3 * inch, 2.7 * inch])
        details_table.setStyle(TableStyle([
            ('VALIGN', (0,0), (-1,-1), 'MIDDLE'),
            ('PADDING', (0,0), (-1,-1), 4),
            ('BACKGROUND', (0,0), (-1,-1), colors.HexColor('#F8F9FA')),
            ('BOX', (0,0), (-1,-1), 0.5, colors.HexColor('#E5E7EB')),
        ]))
        story.append(details_table)
        story.append(Spacer(1, 20))
        
        # 6. Ledger Table
        ledger_headers = [
            Paragraph("<b>Fee Component</b>", normal_bold),
            Paragraph("<b>Amount Receivable</b>", normal_bold),
            Paragraph("<b>Amount Paid Now</b>", normal_bold),
            Paragraph("<b>Balance Dues</b>", normal_bold)
        ]
        
        ledger_row = [
            Paragraph(f"Course Tuition Fee ({pay['course_name']})", normal_regular),
            Paragraph(f"${pay['net_fee']:.2f}", normal_regular),
            Paragraph(f"${pay['amount_paid']:.2f}", normal_bold),
            Paragraph(f"${due_amount:.2f}", normal_regular)
        ]
        
        ledger_table_data = [ledger_headers, ledger_row]
        
        # Add summary rows
        ledger_table_data.append([
            Paragraph("<b>Total Received in Transaction:</b>", normal_bold),
            "", "",
            Paragraph(f"<b>${pay['amount_paid']:.2f}</b>", normal_bold)
        ])
        
        # Generate the table
        ledger_table = Table(ledger_table_data, colWidths=[3.2 * inch, 1.4 * inch, 1.4 * inch, 1.5 * inch])
        ledger_table.setStyle(TableStyle([
            ('BACKGROUND', (0,0), (-1,0), colors.HexColor('#1F497D')),
            ('TEXTCOLOR', (0,0), (-1,0), colors.white),
            ('VALIGN', (0,0), (-1,-1), 'MIDDLE'),
            ('ALIGN', (1,0), (-1,-1), 'RIGHT'),
            ('GRID', (0,0), (-1,-2), 0.5, colors.HexColor('#D1D5DB')),
            ('PADDING', (0,0), (-1,-1), 8),
            # Format header Paragraph color manually to white
            ('LINEBELOW', (0,-1), (-1,-1), 1.5, colors.HexColor('#1F497D')),
            ('SPAN', (0,-1), (2,-1)),  # Span totals label across columns
            ('ALIGN', (0,-1), (0,-1), 'RIGHT'),
        ]))
        
        # Adjust Paragraph colors in header table cells
        header_white_style = ParagraphStyle('WhiteBold', parent=normal_bold, textColor=colors.white)
        ledger_headers_styled = [
            Paragraph("<b>Description</b>", header_white_style),
            Paragraph("<b>Receivable</b>", ParagraphStyle('RWhiteBold', parent=header_white_style, alignment=2)),
            Paragraph("<b>Paid Now</b>", ParagraphStyle('RWhiteBold', parent=header_white_style, alignment=2)),
            Paragraph("<b>Balance Dues</b>", ParagraphStyle('RWhiteBold', parent=header_white_style, alignment=2))
        ]
        ledger_table_data[0] = ledger_headers_styled
        
        story.append(ledger_table)
        story.append(Spacer(1, 15))
        
        # 7. Remarks & Signatures Section
        remarks_text = f"<b>Remarks:</b> {pay['remarks'] or 'N/A'}"
        story.append(Paragraph(remarks_text, normal_regular))
        story.append(Spacer(1, 40))
        
        # Signature block
        sign_data = [
            [
                Paragraph("__________________________<br/>Student Signature", normal_regular),
                Paragraph("__________________________<br/>Authorized Officer", ParagraphStyle('RNormal', parent=normal_regular, alignment=2))
            ]
        ]
        sign_table = Table(sign_data, colWidths=[3.7 * inch, 3.8 * inch])
        sign_table.setStyle(TableStyle([
            ('VALIGN', (0,0), (-1,-1), 'TOP'),
            ('TOPPADDING', (0,0), (-1,-1), 10),
        ]))
        
        story.append(KeepTogether([sign_table]))
        
        # Build Document
        doc.build(story)
        logging.info(f"PDF receipt generated at: {output_path}")
        return True, None
        
    except Exception as e:
        logging.error(f"Failed to generate receipt PDF: {e}")
        return False, str(e)
