from PySide6.QtWidgets import (
    QDialog, QVBoxLayout, QHBoxLayout, QFormLayout, QLineEdit,
    QComboBox, QTextEdit, QDateEdit, QPushButton, QLabel, QMessageBox
)
from PySide6.QtCore import QDate, Qt
import logging

from src.database.queries import get_courses, get_student_enrollments
from src.engines.admission import register_new_student, modify_existing_student, get_student_by_id
from src.engines.lead import create_lead, modify_lead
from src.engines.fee import get_enrollment_financials
from src.database.queries import add_fee_payment, add_course

class StudentFormDialog(QDialog):
    def __init__(self, parent=None, student_id=None):
        super().__init__(parent)
        self.student_id = student_id
        self.setWindowTitle("Add New Student" if not student_id else "Edit Student Profile")
        self.setMinimumWidth(400)
        self.init_ui()
        if student_id:
            self.load_student_data()
            
    def init_ui(self):
        layout = QVBoxLayout(self)
        form_layout = QFormLayout()
        
        self.txt_first_name = QLineEdit()
        self.txt_last_name = QLineEdit()
        self.txt_phone = QLineEdit()
        self.txt_email = QLineEdit()
        
        self.date_dob = QDateEdit()
        self.date_dob.setCalendarPopup(True)
        self.date_dob.setDate(QDate(2000, 1, 1))
        
        self.combo_gender = QComboBox()
        self.combo_gender.addItems(["Male", "Female", "Other"])
        
        self.txt_address = QTextEdit()
        self.txt_address.setMaximumHeight(80)
        
        self.combo_status = QComboBox()
        self.combo_status.addItems(["Active", "Inactive", "Suspended", "Graduated"])
        
        form_layout.addRow("First Name *:", self.txt_first_name)
        form_layout.addRow("Last Name *:", self.txt_last_name)
        form_layout.addRow("Phone Number *:", self.txt_phone)
        form_layout.addRow("Email Address:", self.txt_email)
        form_layout.addRow("Date of Birth *:", self.date_dob)
        form_layout.addRow("Gender:", self.combo_gender)
        form_layout.addRow("Address:", self.txt_address)
        
        if self.student_id:
            form_layout.addRow("Status:", self.combo_status)
            
        layout.addLayout(form_layout)
        
        # Buttons
        btn_layout = QHBoxLayout()
        self.btn_save = QPushButton("Save Student")
        self.btn_save.clicked.connect(self.save_data)
        self.btn_cancel = QPushButton("Cancel")
        self.btn_cancel.setObjectName("SecondaryButton")
        self.btn_cancel.clicked.connect(self.reject)
        
        btn_layout.addWidget(self.btn_save)
        btn_layout.addWidget(self.btn_cancel)
        layout.addLayout(btn_layout)
        
    def load_student_data(self):
        try:
            student = get_student_by_id(self.student_id)
            if student:
                self.txt_first_name.setText(student["first_name"])
                self.txt_last_name.setText(student["last_name"])
                self.txt_phone.setText(student["phone"])
                self.txt_email.setText(student["email"] or "")
                
                qdate = QDate.fromString(student["dob"], "yyyy-MM-dd")
                if qdate.isValid():
                    self.date_dob.setDate(qdate)
                    
                self.combo_gender.setCurrentText(student["gender"])
                self.txt_address.setPlainText(student["address"] or "")
                self.combo_status.setCurrentText(student["status"])
        except Exception as e:
            logging.error(f"Failed to load student data: {e}")
            QMessageBox.critical(self, "Error", f"Failed to load student: {e}")
            
    def save_data(self):
        first = self.txt_first_name.text()
        last = self.txt_last_name.text()
        phone = self.txt_phone.text()
        email = self.txt_email.text()
        dob = self.date_dob.date().toString("yyyy-MM-dd")
        gender = self.combo_gender.currentText()
        address = self.txt_address.toPlainText()
        status = self.combo_status.currentText() if self.student_id else "Active"
        
        try:
            if not self.student_id:
                register_new_student(first, last, email, phone, dob, gender, address)
            else:
                modify_existing_student(self.student_id, first, last, email, phone, dob, gender, address, status)
            self.accept()
        except Exception as e:
            QMessageBox.warning(self, "Validation Error", str(e))

class LeadFormDialog(QDialog):
    def __init__(self, parent=None, lead_id=None, raw_data=None):
        super().__init__(parent)
        self.lead_id = lead_id
        self.raw_data = raw_data
        self.setWindowTitle("Add New Enquiry/Lead" if not lead_id else "Edit Lead Info")
        self.setMinimumWidth(400)
        self.init_ui()
        self.load_courses()
        if lead_id:
            self.load_lead_data()
            
    def init_ui(self):
        layout = QVBoxLayout(self)
        form_layout = QFormLayout()
        
        self.txt_first_name = QLineEdit()
        self.txt_last_name = QLineEdit()
        self.txt_phone = QLineEdit()
        self.txt_email = QLineEdit()
        
        self.combo_source = QComboBox()
        self.combo_source.addItems(["Walk-in", "Website", "Reference", "Advertisement", "Social Media"])
        self.combo_source.setEditable(True)
        
        self.combo_course = QComboBox()
        
        self.date_follow_up = QDateEdit()
        self.date_follow_up.setCalendarPopup(True)
        self.date_follow_up.setDate(QDate.currentDate().addDays(3))
        
        self.txt_remarks = QTextEdit()
        self.txt_remarks.setMaximumHeight(80)
        
        self.combo_status = QComboBox()
        self.combo_status.addItems(["New", "Contacted", "Interested", "Enrolled", "Lost"])
        
        form_layout.addRow("First Name *:", self.txt_first_name)
        form_layout.addRow("Last Name *:", self.txt_last_name)
        form_layout.addRow("Phone Number *:", self.txt_phone)
        form_layout.addRow("Email Address:", self.txt_email)
        form_layout.addRow("Source *:", self.combo_source)
        form_layout.addRow("Course Interested:", self.combo_course)
        form_layout.addRow("Follow-up Date:", self.date_follow_up)
        form_layout.addRow("Remarks / Notes:", self.txt_remarks)
        
        if self.lead_id:
            form_layout.addRow("Lead Status:", self.combo_status)
            
        layout.addLayout(form_layout)
        
        # Action Buttons
        btn_layout = QHBoxLayout()
        self.btn_save = QPushButton("Save Lead")
        self.btn_save.clicked.connect(self.save_data)
        self.btn_cancel = QPushButton("Cancel")
        self.btn_cancel.setObjectName("SecondaryButton")
        self.btn_cancel.clicked.connect(self.reject)
        
        btn_layout.addWidget(self.btn_save)
        btn_layout.addWidget(self.btn_cancel)
        layout.addLayout(btn_layout)
        
    def load_courses(self):
        try:
            self.courses_list = get_courses()
            self.combo_course.addItem("None", None)
            for c in self.courses_list:
                self.combo_course.addItem(c["name"], c["id"])
        except Exception as e:
            logging.error(f"Failed to fetch courses list: {e}")
            
    def load_lead_data(self):
        # Fetching details for edit
        from src.database.connection import get_connection
        conn = get_connection()
        cursor = conn.cursor()
        cursor.execute("SELECT * FROM leads WHERE id = ?;", (self.lead_id,))
        lead = cursor.fetchone()
        cursor.close()
        
        if lead:
            self.txt_first_name.setText(lead["first_name"])
            self.txt_last_name.setText(lead["last_name"])
            self.txt_phone.setText(lead["phone"])
            self.txt_email.setText(lead["email"] or "")
            self.combo_source.setEditText(lead["source"])
            
            # Find and set interested course index
            idx = self.combo_course.findData(lead["course_interested_id"])
            if idx >= 0:
                self.combo_course.setCurrentIndex(idx)
                
            qdate = QDate.fromString(lead["follow_up_date"], "yyyy-MM-dd")
            if qdate.isValid():
                self.date_follow_up.setDate(qdate)
                
            self.txt_remarks.setPlainText(lead["remarks"] or "")
            self.combo_status.setCurrentText(lead["status"])
            
    def save_data(self):
        first = self.txt_first_name.text()
        last = self.txt_last_name.text()
        phone = self.txt_phone.text()
        email = self.txt_email.text()
        source = self.combo_source.currentText()
        course_id = self.combo_course.currentData()
        follow_up = self.date_follow_up.date().toString("yyyy-MM-dd")
        remarks = self.txt_remarks.toPlainText()
        status = self.combo_status.currentText() if self.lead_id else "New"
        
        try:
            if not self.lead_id:
                create_lead(first, last, phone, email, source, course_id, follow_up, remarks)
            else:
                modify_lead(self.lead_id, first, last, phone, email, source, course_id, status, follow_up, remarks)
            self.accept()
        except Exception as e:
            QMessageBox.warning(self, "Validation Error", str(e))

class CourseFormDialog(QDialog):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowTitle("Add New Course")
        self.setMinimumWidth(350)
        self.init_ui()
        
    def init_ui(self):
        layout = QVBoxLayout(self)
        form_layout = QFormLayout()
        
        self.txt_name = QLineEdit()
        self.txt_code = QLineEdit()
        self.txt_duration = QLineEdit()
        self.txt_duration.setPlaceholderText("e.g. 3")
        self.txt_fee = QLineEdit()
        self.txt_fee.setPlaceholderText("e.g. 15000")
        
        self.txt_desc = QTextEdit()
        self.txt_desc.setMaximumHeight(80)
        
        form_layout.addRow("Course Name *:", self.txt_name)
        form_layout.addRow("Course Code *:", self.txt_code)
        form_layout.addRow("Duration (Months) *:", self.txt_duration)
        form_layout.addRow("Total Fees ($) *:", self.txt_fee)
        form_layout.addRow("Description:", self.txt_desc)
        
        layout.addLayout(form_layout)
        
        btn_layout = QHBoxLayout()
        btn_save = QPushButton("Add Course")
        btn_save.clicked.connect(self.save_data)
        btn_cancel = QPushButton("Cancel")
        btn_cancel.setObjectName("SecondaryButton")
        btn_cancel.clicked.connect(self.reject)
        
        btn_layout.addWidget(btn_save)
        btn_layout.addWidget(btn_cancel)
        layout.addLayout(btn_layout)
        
    def save_data(self):
        name = self.txt_name.text().strip()
        code = self.txt_code.text().strip().upper()
        duration = self.txt_duration.text().strip()
        fee = self.txt_fee.text().strip()
        desc = self.txt_desc.toPlainText().strip()
        
        if not name or not code or not duration or not fee:
            QMessageBox.warning(self, "Validation Error", "All fields marked * are required.")
            return
            
        try:
            duration_months = int(duration)
            total_fee = float(fee)
            if duration_months <= 0 or total_fee < 0:
                raise ValueError()
        except ValueError:
            QMessageBox.warning(self, "Validation Error", "Duration must be > 0 and Fees must be a valid positive number.")
            return
            
        try:
            add_course(name, code, desc, duration_months, total_fee)
            self.accept()
        except Exception as e:
            QMessageBox.critical(self, "Error", f"Failed to save course: {e}")

class PaymentCollectionDialog(QDialog):
    def __init__(self, parent=None, student_id=None):
        super().__init__(parent)
        self.student_id = student_id
        self.setWindowTitle("Collect Fee Payment")
        self.setMinimumWidth(380)
        self.init_ui()
        self.load_enrollments()
        
    def init_ui(self):
        layout = QVBoxLayout(self)
        form_layout = QFormLayout()
        
        self.combo_enrollment = QComboBox()
        self.combo_enrollment.currentIndexChanged.connect(self.enrollment_changed)
        
        self.lbl_outstanding = QLabel("$0.00")
        self.lbl_outstanding.setStyleSheet("font-weight: bold; color: red; font-size: 14px;")
        
        self.txt_amount = QLineEdit()
        self.txt_receipt = QLineEdit()
        # Auto generate receipt number
        import random
        self.txt_receipt.setText(f"AOS-REC-{QDate.currentDate().toString('yyyyMM')}-{random.randint(1000, 9999)}")
        
        self.combo_method = QComboBox()
        self.combo_method.addItems(["Cash", "UPI", "Card", "Bank Transfer"])
        
        self.txt_remarks = QLineEdit()
        
        form_layout.addRow("Select Course *:", self.combo_enrollment)
        form_layout.addRow("Pending Dues:", self.lbl_outstanding)
        form_layout.addRow("Amount Paid ($) *:", self.txt_amount)
        form_layout.addRow("Receipt Number *:", self.txt_receipt)
        form_layout.addRow("Payment Method:", self.combo_method)
        form_layout.addRow("Remarks:", self.txt_remarks)
        
        layout.addLayout(form_layout)
        
        btn_layout = QHBoxLayout()
        self.btn_submit = QPushButton("Collect Payment")
        self.btn_submit.clicked.connect(self.submit_payment)
        self.btn_cancel = QPushButton("Cancel")
        self.btn_cancel.setObjectName("SecondaryButton")
        self.btn_cancel.clicked.connect(self.reject)
        
        btn_layout.addWidget(self.btn_submit)
        btn_layout.addWidget(self.btn_cancel)
        layout.addLayout(btn_layout)
        
    def load_enrollments(self):
        try:
            enrollments = get_student_enrollments(self.student_id)
            if not enrollments:
                QMessageBox.warning(self, "No Enrollments", "This student has no active enrollments to pay for.")
                self.reject()
                return
                
            for e in enrollments:
                self.combo_enrollment.addItem(f"{e['course_name']} ({e['course_code']})", e["id"])
        except Exception as e:
            logging.error(f"Failed to fetch enrollments for payment: {e}")
            
    def enrollment_changed(self):
        enrollment_id = self.combo_enrollment.currentData()
        if enrollment_id:
            fin = get_enrollment_financials(enrollment_id)
            if fin:
                self.lbl_outstanding.setText(f"${fin['due_amount']:.2f}")
                self.txt_amount.setPlaceholderText(f"Max ${fin['due_amount']:.2f}")
                
    def submit_payment(self):
        enrollment_id = self.combo_enrollment.currentData()
        amount_str = self.txt_amount.text().strip()
        receipt = self.txt_receipt.text().strip()
        method = self.combo_method.currentText()
        remarks = self.txt_remarks.text().strip()
        
        if not amount_str or not receipt:
            QMessageBox.warning(self, "Validation Error", "Amount and receipt fields are required.")
            return
            
        try:
            amount = float(amount_str)
            if amount <= 0:
                raise ValueError()
        except ValueError:
            QMessageBox.warning(self, "Validation Error", "Please input a positive numeric amount.")
            return
            
        # Verify amount doesn't exceed outstanding dues
        fin = get_enrollment_financials(enrollment_id)
        if amount > fin['due_amount'] + 0.01: # allow small precision delta
            QMessageBox.warning(self, "Excess Amount", f"Paid amount ${amount:.2f} cannot exceed pending dues (${fin['due_amount']:.2f}).")
            return
            
        try:
            payment_id = add_fee_payment(enrollment_id, amount, method, receipt, remarks)
            self.accept()
            # In UI we will capture payment_id for optional receipt PDF rendering
            self.payment_id = payment_id
        except Exception as e:
            QMessageBox.critical(self, "Error", f"Failed to record payment: {e}")

class ActivationDialog(QDialog):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowTitle("AcademyOS Desktop Activation")
        self.setMinimumWidth(400)
        self.setWindowFlags(self.windowFlags() & ~Qt.WindowContextHelpButtonHint)
        self.init_ui()
        
    def init_ui(self):
        layout = QVBoxLayout(self)
        
        # Header Info
        header = QLabel("<h3>Software Activation Required</h3>")
        layout.addWidget(header)
        
        desc = QLabel(
            "AcademyOS requires an activation key to run. "
            "Please copy the hardware fingerprint below and contact your administrator to generate an activation license key."
        )
        desc.setWordWrap(True)
        layout.addWidget(desc)
        
        # Display Fingerprint
        from src.engines.license import get_device_fingerprint
        self.fingerprint = get_device_fingerprint()
        
        fp_layout = QHBoxLayout()
        fp_layout.addWidget(QLabel("<b>Device Fingerprint:</b>"))
        self.txt_fp = QLineEdit(self.fingerprint)
        self.txt_fp.setReadOnly(True)
        fp_layout.addWidget(self.txt_fp)
        
        btn_copy = QPushButton("Copy")
        btn_copy.setObjectName("SecondaryButton")
        btn_copy.clicked.connect(self.copy_fingerprint)
        fp_layout.addWidget(btn_copy)
        
        layout.addLayout(fp_layout)
        
        # Key Entry
        layout.addWidget(QLabel("<b>Enter Activation License Key:</b>"))
        self.txt_key = QLineEdit()
        self.txt_key.setPlaceholderText("AOS-KEY-YYYY-MM-DD-SIGNATURE")
        layout.addWidget(self.txt_key)
        
        layout.addSpacing(10)
        
        # Submit
        btn_layout = QHBoxLayout()
        btn_activate = QPushButton("Activate Software")
        btn_activate.clicked.connect(self.activate)
        btn_exit = QPushButton("Exit")
        btn_exit.setObjectName("DestructiveButton")
        btn_exit.clicked.connect(self.reject)
        
        btn_layout.addWidget(btn_activate)
        btn_layout.addWidget(btn_exit)
        layout.addLayout(btn_layout)
        
    def copy_fingerprint(self):
        from PySide6.QtGui import QClipboard
        from PySide6.QtWidgets import QApplication
        QApplication.clipboard().setText(self.fingerprint)
        QMessageBox.information(self, "Copied", "Hardware fingerprint copied to clipboard.")
        
    def activate(self):
        key = self.txt_key.text().strip()
        if not key:
            QMessageBox.warning(self, "Blank Key", "Please input an activation key.")
            return
            
        from src.engines.license import activate_license
        if activate_license(key):
            QMessageBox.information(self, "Success", "AcademyOS activated successfully! The application will now load.")
            self.accept()
        else:
            QMessageBox.critical(self, "Activation Failed", "The activation key is invalid, expired, or generated for another device.")
