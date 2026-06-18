from PySide6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel, QTableWidget,
    QTableWidgetItem, QHeaderView, QPushButton, QMessageBox, QDialog
)
from PySide6.QtCore import Qt
import logging

from src.engines.fee import get_outstanding_fees_list
from src.ui.dialogs import PaymentCollectionDialog

class FeeTab(QWidget):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.init_ui()
        self.refresh_fees()
        
    def init_ui(self):
        layout = QVBoxLayout(self)
        layout.setContentsMargins(16, 16, 16, 16)
        
        # 1. Title & Action Bar
        header_layout = QHBoxLayout()
        header_title = QLabel("<h2>Outstanding Dues Tracking</h2>")
        header_layout.addWidget(header_title)
        
        header_layout.addStretch()
        
        self.btn_pay = QPushButton("Collect Payment / Installment")
        self.btn_pay.setStyleSheet("background-color: #10B981; color: white;")
        self.btn_pay.clicked.connect(self.collect_payment)
        header_layout.addWidget(self.btn_pay)
        
        layout.addLayout(header_layout)
        
        # 2. Grid Table of Outstanding Dues
        self.table_fees = QTableWidget()
        self.table_fees.setColumnCount(7)
        self.table_fees.setHorizontalHeaderLabels([
            "Enrollment ID", "Student Name", "Phone Number", "Course Enrolled",
            "Net Fee ($)", "Amount Paid ($)", "Outstanding Dues ($)"
        ])
        self.table_fees.horizontalHeader().setSectionResizeMode(QHeaderView.ResizeMode.Interactive)
        self.table_fees.horizontalHeader().setSectionResizeMode(1, QHeaderView.ResizeMode.Stretch)
        self.table_fees.horizontalHeader().setSectionResizeMode(3, QHeaderView.ResizeMode.Stretch)
        self.table_fees.setSelectionBehavior(QTableWidget.SelectRows)
        self.table_fees.setSelectionMode(QTableWidget.SingleSelection)
        self.table_fees.setEditTriggers(QTableWidget.NoEditTriggers)
        self.table_fees.setAlternatingRowColors(True)
        
        layout.addWidget(self.table_fees)
        
    def refresh_fees(self):
        try:
            outstanding = get_outstanding_fees_list()
            self.table_fees.setRowCount(0)
            
            for row_idx, item in enumerate(outstanding):
                self.table_fees.insertRow(row_idx)
                
                self.table_fees.setItem(row_idx, 0, QTableWidgetItem(str(item["enrollment_id"])))
                self.table_fees.setItem(row_idx, 1, QTableWidgetItem(item["student_name"]))
                self.table_fees.setItem(row_idx, 2, QTableWidgetItem(item["phone"]))
                self.table_fees.setItem(row_idx, 3, QTableWidgetItem(item["course_name"]))
                
                c_net = QTableWidgetItem(f"${item['net_fee']:.2f}")
                c_net.setTextAlignment(Qt.AlignRight | Qt.AlignVCenter)
                self.table_fees.setItem(row_idx, 4, c_net)
                
                c_paid = QTableWidgetItem(f"${item['total_paid']:.2f}")
                c_paid.setTextAlignment(Qt.AlignRight | Qt.AlignVCenter)
                self.table_fees.setItem(row_idx, 5, c_paid)
                
                # Dues highlighted in soft red text
                c_due = QTableWidgetItem(f"${item['due_amount']:.2f}")
                c_due.setTextAlignment(Qt.AlignRight | Qt.AlignVCenter)
                c_due.setForeground(Qt.red)
                self.table_fees.setItem(row_idx, 6, c_due)
                
        except Exception as e:
            logging.error(f"Failed to refresh fees ledger: {e}")
            
    def get_selected_enrollment_id(self) -> int:
        selected_rows = self.table_fees.selectionModel().selectedRows()
        if not selected_rows:
            return None
        row_idx = selected_rows[0].row()
        return int(self.table_fees.item(row_idx, 0).text())
        
    def get_selected_student_id(self) -> int:
        # Resolve student ID from the database using selected enrollment row
        enroll_id = self.get_selected_enrollment_id()
        if not enroll_id:
            return None
            
        from src.database.connection import get_connection
        conn = get_connection()
        cursor = conn.cursor()
        cursor.execute("SELECT student_id FROM enrollments WHERE id = ?;", (enroll_id,))
        row = cursor.fetchone()
        cursor.close()
        return row[0] if row else None
        
    def collect_payment(self):
        student_id = self.get_selected_student_id()
        if not student_id:
            QMessageBox.information(self, "Select Row", "Please select a student record to record payment.")
            return
            
        dlg = PaymentCollectionDialog(self, student_id)
        if dlg.exec() == QDialog.Accepted:
            self.refresh_fees()
            self.window().refresh_all_tabs()
            
            # Ask if they want receipt printout (delegated to StudentTab's print logic via main window)
            payment_id = getattr(dlg, "payment_id", None)
            if payment_id:
                # Main Window has print_receipt shortcut
                if hasattr(self.window(), "student_tab"):
                    self.window().student_tab.print_receipt(payment_id)
