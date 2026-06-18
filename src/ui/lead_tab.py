from PySide6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLineEdit, QPushButton,
    QTableWidget, QTableWidgetItem, QHeaderView, QMessageBox,
    QDialog, QFormLayout, QComboBox, QDateEdit
)
from PySide6.QtCore import Qt, QDate
import logging

from src.database.queries import search_leads, delete_lead
from src.ui.dialogs import LeadFormDialog
from src.engines.lead import promote_lead_to_student

class LeadTab(QWidget):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.init_ui()
        self.refresh_leads()
        
    def init_ui(self):
        layout = QVBoxLayout(self)
        layout.setContentsMargins(16, 16, 16, 16)
        
        # 1. Search & Actions Header Bar
        header_layout = QHBoxLayout()
        
        self.txt_search = QLineEdit()
        self.txt_search.setPlaceholderText("Search enquiries by name, phone or remarks...")
        self.txt_search.textChanged.connect(self.refresh_leads)
        header_layout.addWidget(self.txt_search, stretch=3)
        
        self.btn_add = QPushButton("Add Lead / Enquiry")
        self.btn_add.clicked.connect(self.add_lead)
        header_layout.addWidget(self.btn_add)
        
        self.btn_edit = QPushButton("Edit Info")
        self.btn_edit.setObjectName("SecondaryButton")
        self.btn_edit.clicked.connect(self.edit_lead)
        header_layout.addWidget(self.btn_edit)
        
        self.btn_delete = QPushButton("Delete")
        self.btn_delete.setObjectName("DestructiveButton")
        self.btn_delete.clicked.connect(self.delete_lead)
        header_layout.addWidget(self.btn_delete)
        
        self.btn_promote = QPushButton("Enroll Lead as Student")
        self.btn_promote.setStyleSheet("background-color: #10B981; color: white;") # Green highlight
        self.btn_promote.clicked.connect(self.promote_lead)
        header_layout.addWidget(self.btn_promote)
        
        layout.addLayout(header_layout)
        
        # 2. Leads Grid Table
        self.table_leads = QTableWidget()
        self.table_leads.setColumnCount(8)
        self.table_leads.setHorizontalHeaderLabels([
            "ID", "Student Name", "Phone Number", "Email Address",
            "Lead Source", "Course Interested", "Status", "Follow-up Date"
        ])
        self.table_leads.horizontalHeader().setSectionResizeMode(QHeaderView.ResizeMode.Interactive)
        self.table_leads.horizontalHeader().setSectionResizeMode(1, QHeaderView.ResizeMode.Stretch)
        self.table_leads.setSelectionBehavior(QTableWidget.SelectRows)
        self.table_leads.setSelectionMode(QTableWidget.SingleSelection)
        self.table_leads.setEditTriggers(QTableWidget.NoEditTriggers)
        self.table_leads.setAlternatingRowColors(True)
        
        layout.addWidget(self.table_leads)
        
    def refresh_leads(self):
        try:
            query = self.txt_search.text()
            leads = search_leads(query)
            
            self.table_leads.setRowCount(0)
            for row_idx, lead in enumerate(leads):
                self.table_leads.insertRow(row_idx)
                
                self.table_leads.setItem(row_idx, 0, QTableWidgetItem(str(lead["id"])))
                self.table_leads.setItem(row_idx, 1, QTableWidgetItem(f"{lead['first_name']} {lead['last_name']}"))
                self.table_leads.setItem(row_idx, 2, QTableWidgetItem(lead["phone"]))
                self.table_leads.setItem(row_idx, 3, QTableWidgetItem(lead["email"] or "N/A"))
                self.table_leads.setItem(row_idx, 4, QTableWidgetItem(lead["source"]))
                self.table_leads.setItem(row_idx, 5, QTableWidgetItem(lead["course_name"] or "None"))
                
                # Format status cell with styling
                status_item = QTableWidgetItem(lead["status"])
                status_item.setTextAlignment(Qt.AlignCenter)
                if lead["status"] == "Enrolled":
                    status_item.setForeground(Qt.darkGreen)
                elif lead["status"] == "Lost":
                    status_item.setForeground(Qt.darkRed)
                self.table_leads.setItem(row_idx, 6, status_item)
                
                self.table_leads.setItem(row_idx, 7, QTableWidgetItem(lead["follow_up_date"] or "N/A"))
                
        except Exception as e:
            logging.error(f"Failed to refresh leads: {e}")
            
    def get_selected_lead_id(self) -> int:
        selected_rows = self.table_leads.selectionModel().selectedRows()
        if not selected_rows:
            return None
        row_idx = selected_rows[0].row()
        return int(self.table_leads.item(row_idx, 0).text())
        
    def add_lead(self):
        dlg = LeadFormDialog(self)
        if dlg.exec() == QDialog.Accepted:
            self.refresh_leads()
            # Update parent window dashboard if needed
            self.window().refresh_all_tabs()
            
    def edit_lead(self):
        lead_id = self.get_selected_lead_id()
        if not lead_id:
            QMessageBox.information(self, "Select Row", "Please select a lead to edit.")
            return
            
        dlg = LeadFormDialog(self, lead_id=lead_id)
        if dlg.exec() == QDialog.Accepted:
            self.refresh_leads()
            self.window().refresh_all_tabs()
            
    def delete_lead(self):
        lead_id = self.get_selected_lead_id()
        if not lead_id:
            QMessageBox.information(self, "Select Row", "Please select a lead to delete.")
            return
            
        reply = QMessageBox.question(
            self, "Confirm Delete",
            "Are you sure you want to delete this enquiry record?",
            QMessageBox.Yes | QMessageBox.No
        )
        if reply == QMessageBox.Yes:
            if delete_lead(lead_id):
                self.refresh_leads()
                self.window().refresh_all_tabs()
                
    def promote_lead(self):
        lead_id = self.get_selected_lead_id()
        if not lead_id:
            QMessageBox.information(self, "Select Row", "Please select a lead to enroll.")
            return
            
        # Get lead status
        selected_rows = self.table_leads.selectionModel().selectedRows()
        row_idx = selected_rows[0].row()
        status = self.table_leads.item(row_idx, 6).text()
        if status == "Enrolled":
            QMessageBox.warning(self, "Enrolled Lead", "This lead is already enrolled as a student.")
            return
            
        # Prompt details for student profile creation
        promote_dlg = PromoteLeadDialog(self)
        if promote_dlg.exec() == QDialog.Accepted:
            dob = promote_dlg.date_dob.date().toString("yyyy-MM-dd")
            gender = promote_dlg.combo_gender.currentText()
            address = promote_dlg.txt_address.text().strip()
            discount = promote_dlg.txt_discount.text().strip()
            
            try:
                disc_val = float(discount) if discount else 0.0
                if disc_val < 0:
                    raise ValueError()
            except ValueError:
                QMessageBox.warning(self, "Discount Error", "Discount must be a valid positive number.")
                return
                
            try:
                promote_lead_to_student(lead_id, dob, gender, address, disc_val)
                QMessageBox.information(self, "Enrolled", "Lead successfully enrolled as a student!")
                self.refresh_leads()
                self.window().refresh_all_tabs()
            except Exception as e:
                QMessageBox.critical(self, "Enrollment Failed", f"Could not enroll lead: {e}")

class PromoteLeadDialog(QDialog):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowTitle("Enrollment Profile Setup")
        self.setMinimumWidth(350)
        self.init_ui()
        
    def init_ui(self):
        layout = QVBoxLayout(self)
        form_layout = QFormLayout()
        
        self.date_dob = QDateEdit()
        self.date_dob.setCalendarPopup(True)
        self.date_dob.setDate(QDate(2000, 1, 1))
        
        self.combo_gender = QComboBox()
        self.combo_gender.addItems(["Male", "Female", "Other"])
        
        self.txt_address = QLineEdit()
        self.txt_discount = QLineEdit()
        self.txt_discount.setText("0.00")
        
        form_layout.addRow("Date of Birth *:", self.date_dob)
        form_layout.addRow("Gender:", self.combo_gender)
        form_layout.addRow("Home Address:", self.txt_address)
        form_layout.addRow("Course Discount ($):", self.txt_discount)
        
        layout.addLayout(form_layout)
        
        btn_layout = QHBoxLayout()
        btn_ok = QPushButton("Confirm Enrollment")
        btn_ok.clicked.connect(self.accept)
        btn_cancel = QPushButton("Cancel")
        btn_cancel.setObjectName("SecondaryButton")
        btn_cancel.clicked.connect(self.reject)
        
        btn_layout.addWidget(btn_ok)
        btn_layout.addWidget(btn_cancel)
        layout.addLayout(btn_layout)
