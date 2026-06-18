from PySide6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLineEdit, QPushButton,
    QTableWidget, QTableWidgetItem, QHeaderView, QMessageBox,
    QDialog, QFormLayout, QComboBox, QLabel, QGroupBox, QSplitter
)
from PySide6.QtCore import Qt, QDate
import logging

from src.database.queries import search_students, delete_student, get_student_enrollments, get_courses, enroll_student
from src.ui.dialogs import StudentFormDialog, PaymentCollectionDialog
from src.engines.report_generator import generate_receipt_pdf
from src.utils.config import load_settings

class StudentTab(QWidget):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.init_ui()
        self.refresh_students()
        
    def init_ui(self):
        main_layout = QHBoxLayout(self)
        main_layout.setContentsMargins(16, 16, 16, 16)
        
        # Use QSplitter to allow resizing the master and detail section
        splitter = QSplitter(Qt.Vertical)
        
        # --- MASTER CONTAINER (Top) ---
        master_widget = QWidget()
        master_layout = QVBoxLayout(master_widget)
        master_layout.setContentsMargins(0, 0, 0, 0)
        
        # Search & CRUD buttons
        action_layout = QHBoxLayout()
        self.txt_search = QLineEdit()
        self.txt_search.setPlaceholderText("Search students by name, email or phone...")
        self.txt_search.textChanged.connect(self.refresh_students)
        action_layout.addWidget(self.txt_search, stretch=3)
        
        self.btn_add = QPushButton("Register Student")
        self.btn_add.clicked.connect(self.add_student)
        action_layout.addWidget(self.btn_add)
        
        self.btn_edit = QPushButton("Edit Profile")
        self.btn_edit.setObjectName("SecondaryButton")
        self.btn_edit.clicked.connect(self.edit_student)
        action_layout.addWidget(self.btn_edit)
        
        self.btn_delete = QPushButton("Delete")
        self.btn_delete.setObjectName("DestructiveButton")
        self.btn_delete.clicked.connect(self.delete_student)
        action_layout.addWidget(self.btn_delete)
        
        master_layout.addLayout(action_layout)
        
        # Student Grid
        self.table_students = QTableWidget()
        self.table_students.setColumnCount(6)
        self.table_students.setHorizontalHeaderLabels(["ID", "Student Name", "Phone Number", "Email Address", "Admission Date", "Status"])
        self.table_students.horizontalHeader().setSectionResizeMode(QHeaderView.ResizeMode.Interactive)
        self.table_students.horizontalHeader().setSectionResizeMode(1, QHeaderView.ResizeMode.Stretch)
        self.table_students.setSelectionBehavior(QTableWidget.SelectRows)
        self.table_students.setSelectionMode(QTableWidget.SingleSelection)
        self.table_students.setEditTriggers(QTableWidget.NoEditTriggers)
        self.table_students.setAlternatingRowColors(True)
        self.table_students.itemSelectionChanged.connect(self.student_selection_changed)
        
        master_layout.addWidget(self.table_students)
        splitter.addWidget(master_widget)
        
        # --- DETAIL CONTAINER (Bottom) ---
        self.detail_group = QGroupBox("Selected Student Details & Enrollments")
        detail_layout = QVBoxLayout(self.detail_group)
        
        detail_actions = QHBoxLayout()
        self.lbl_selected_student = QLabel("No student selected.")
        self.lbl_selected_student.setStyleSheet("font-weight: bold; font-size: 14px; color: #1F497D;")
        detail_actions.addWidget(self.lbl_selected_student)
        
        detail_actions.addStretch()
        
        self.btn_enroll = QPushButton("Enroll in Course")
        self.btn_enroll.clicked.connect(self.enroll_in_course)
        self.btn_enroll.setEnabled(False)
        detail_actions.addWidget(self.btn_enroll)
        
        self.btn_pay = QPushButton("Collect Payment")
        self.btn_pay.setStyleSheet("background-color: #10B981; color: white;")
        self.btn_pay.clicked.connect(self.collect_payment)
        self.btn_pay.setEnabled(False)
        detail_actions.addWidget(self.btn_pay)
        
        detail_layout.addLayout(detail_actions)
        
        # Enrollments Table
        self.table_enrollments = QTableWidget()
        self.table_enrollments.setColumnCount(5)
        self.table_enrollments.setHorizontalHeaderLabels(["Enrollment Date", "Course Name", "Course Code", "Discount Granted", "Net Course Fee"])
        self.table_enrollments.horizontalHeader().setSectionResizeMode(QHeaderView.ResizeMode.Stretch)
        self.table_enrollments.setEditTriggers(QTableWidget.NoEditTriggers)
        self.table_enrollments.setAlternatingRowColors(True)
        detail_layout.addWidget(self.table_enrollments)
        
        splitter.addWidget(self.detail_group)
        
        # Add splitter to layout
        main_layout.addWidget(splitter)
        
    def refresh_students(self):
        try:
            query = self.txt_search.text()
            students = search_students(query)
            
            self.table_students.setRowCount(0)
            for row_idx, s in enumerate(students):
                self.table_students.insertRow(row_idx)
                
                self.table_students.setItem(row_idx, 0, QTableWidgetItem(str(s["id"])))
                self.table_students.setItem(row_idx, 1, QTableWidgetItem(f"{s['first_name']} {s['last_name']}"))
                self.table_students.setItem(row_idx, 2, QTableWidgetItem(s["phone"]))
                self.table_students.setItem(row_idx, 3, QTableWidgetItem(s["email"] or "N/A"))
                self.table_students.setItem(row_idx, 4, QTableWidgetItem(s["admission_date"]))
                
                status_item = QTableWidgetItem(s["status"])
                status_item.setTextAlignment(Qt.AlignCenter)
                if s["status"] == "Active":
                    status_item.setForeground(Qt.darkGreen)
                self.table_students.setItem(row_idx, 5, status_item)
                
            self.clear_detail_view()
        except Exception as e:
            logging.error(f"Failed to refresh students directory: {e}")
            
    def get_selected_student_id(self) -> int:
        selected_rows = self.table_students.selectionModel().selectedRows()
        if not selected_rows:
            return None
        row_idx = selected_rows[0].row()
        return int(self.table_students.item(row_idx, 0).text())
        
    def get_selected_student_name(self) -> str:
        selected_rows = self.table_students.selectionModel().selectedRows()
        if not selected_rows:
            return ""
        row_idx = selected_rows[0].row()
        return self.table_students.item(row_idx, 1).text()
        
    def student_selection_changed(self):
        student_id = self.get_selected_student_id()
        if not student_id:
            self.clear_detail_view()
            return
            
        student_name = self.get_selected_student_name()
        self.lbl_selected_student.setText(f"Details for: {student_name}")
        self.btn_enroll.setEnabled(True)
        self.btn_pay.setEnabled(True)
        
        # Load enrollments
        try:
            enrollments = get_student_enrollments(student_id)
            self.table_enrollments.setRowCount(0)
            for row_idx, e in enumerate(enrollments):
                self.table_enrollments.insertRow(row_idx)
                self.table_enrollments.setItem(row_idx, 0, QTableWidgetItem(e["enrollment_date"]))
                self.table_enrollments.setItem(row_idx, 1, QTableWidgetItem(e["course_name"]))
                self.table_enrollments.setItem(row_idx, 2, QTableWidgetItem(e["course_code"]))
                self.table_enrollments.setItem(row_idx, 3, QTableWidgetItem(f"${e['discount']:.2f}"))
                self.table_enrollments.setItem(row_idx, 4, QTableWidgetItem(f"${e['net_fee']:.2f}"))
        except Exception as e:
            logging.error(f"Failed to load enrollments for student {student_id}: {e}")
            
    def clear_detail_view(self):
        self.lbl_selected_student.setText("No student selected.")
        self.table_enrollments.setRowCount(0)
        self.btn_enroll.setEnabled(False)
        self.btn_pay.setEnabled(False)
        
    def add_student(self):
        dlg = StudentFormDialog(self)
        if dlg.exec() == QDialog.Accepted:
            self.refresh_students()
            self.window().refresh_all_tabs()
            
    def edit_student(self):
        student_id = self.get_selected_student_id()
        if not student_id:
            QMessageBox.information(self, "Select Row", "Please select a student to edit.")
            return
            
        dlg = StudentFormDialog(self, student_id=student_id)
        if dlg.exec() == QDialog.Accepted:
            self.refresh_students()
            self.window().refresh_all_tabs()
            
    def delete_student(self):
        student_id = self.get_selected_student_id()
        if not student_id:
            QMessageBox.information(self, "Select Row", "Please select a student to delete.")
            return
            
        reply = QMessageBox.question(
            self, "Confirm Delete",
            "Are you sure you want to delete this student profile?\nThis will permanently delete all associated course enrollments and payments.",
            QMessageBox.Yes | QMessageBox.No
        )
        if reply == QMessageBox.Yes:
            if delete_student(student_id):
                self.refresh_students()
                self.window().refresh_all_tabs()
                
    def enroll_in_course(self):
        student_id = self.get_selected_student_id()
        if not student_id:
            return
            
        dlg = EnrollCourseDialog(self)
        if dlg.exec() == QDialog.Accepted:
            course_id = dlg.combo_course.currentData()
            discount = dlg.txt_discount.text().strip()
            
            try:
                disc_val = float(discount) if discount else 0.0
                if disc_val < 0:
                    raise ValueError()
            except ValueError:
                QMessageBox.warning(self, "Discount Error", "Discount must be a valid positive number.")
                return
                
            try:
                # Find course fee
                courses = get_courses()
                course = next(c for c in courses if c["id"] == course_id)
                base_fee = course["total_fee"]
                net_fee = max(0.0, base_fee - disc_val)
                
                enroll_student(student_id, course_id, disc_val, net_fee)
                QMessageBox.information(self, "Enrolled", "Successfully enrolled student in course!")
                self.student_selection_changed() # Refresh detail panel
                self.window().refresh_all_tabs()
            except Exception as e:
                QMessageBox.critical(self, "Error", f"Failed to enroll student: {e}")
                
    def collect_payment(self):
        student_id = self.get_selected_student_id()
        if not student_id:
            return
            
        dlg = PaymentCollectionDialog(self, student_id)
        if dlg.exec() == QDialog.Accepted:
            # Refresh details panel
            self.student_selection_changed()
            self.window().refresh_all_tabs()
            
            # Offer to print receipt PDF
            reply = QMessageBox.question(
                self, "Generate Receipt",
                "Payment recorded successfully! Would you like to generate and print a PDF receipt?",
                QMessageBox.Yes | QMessageBox.No
            )
            if reply == QMessageBox.Yes:
                payment_id = getattr(dlg, "payment_id", None)
                if payment_id:
                    self.print_receipt(payment_id)
                    
    def print_receipt(self, payment_id: int):
        try:
            settings = load_settings()
            reports_dir = settings["reports_directory"]
            os.makedirs(reports_dir, exist_ok=True)
            
            pdf_path = os.path.join(reports_dir, f"Receipt_{payment_id}_{QDate.currentDate().toString('yyyyMMdd')}.pdf")
            success, err = generate_receipt_pdf(payment_id, pdf_path)
            
            if success:
                QMessageBox.information(self, "PDF Saved", f"PDF receipt saved successfully to:\n{pdf_path}")
                # Open PDF using default system viewer
                import platform
                import subprocess
                if platform.system() == 'Windows':
                    os.startfile(pdf_path)
                elif platform.system() == 'Darwin':
                    subprocess.Popen(['open', pdf_path])
                else:
                    subprocess.Popen(['xdg-open', pdf_path])
            else:
                QMessageBox.critical(self, "PDF Error", f"Failed to generate receipt: {err}")
        except Exception as e:
            logging.error(f"Print receipt failed: {e}")
            QMessageBox.critical(self, "Error", f"Failed to generate PDF: {e}")

class EnrollCourseDialog(QDialog):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowTitle("Enroll Student in Course")
        self.setMinimumWidth(320)
        self.init_ui()
        self.load_courses()
        
    def init_ui(self):
        layout = QVBoxLayout(self)
        form_layout = QFormLayout()
        
        self.combo_course = QComboBox()
        self.txt_discount = QLineEdit()
        self.txt_discount.setText("0.00")
        
        form_layout.addRow("Select Course *:", self.combo_course)
        form_layout.addRow("Discount Granted ($):", self.txt_discount)
        
        layout.addLayout(form_layout)
        
        btn_layout = QHBoxLayout()
        btn_ok = QPushButton("Enroll")
        btn_ok.clicked.connect(self.accept)
        btn_cancel = QPushButton("Cancel")
        btn_cancel.setObjectName("SecondaryButton")
        btn_cancel.clicked.connect(self.reject)
        
        btn_layout.addWidget(btn_ok)
        btn_layout.addWidget(btn_cancel)
        layout.addLayout(btn_layout)
        
    def load_courses(self):
        try:
            courses = get_courses()
            for c in courses:
                self.combo_course.addItem(f"{c['name']} (${c['total_fee']:.2f})", c["id"])
        except Exception as e:
            logging.error(f"Failed to load courses for enrollment: {e}")
