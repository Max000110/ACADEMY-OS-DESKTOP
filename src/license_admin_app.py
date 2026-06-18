import os
import sys
import sqlite3
import datetime
import logging
from PySide6.QtWidgets import (
    QApplication, QMainWindow, QWidget, QVBoxLayout, QHBoxLayout,
    QTableWidget, QTableWidgetItem, QFormLayout, QLineEdit, QComboBox,
    QPushButton, QLabel, QTextEdit, QTabWidget, QMessageBox, QGroupBox,
    QHeaderView, QAbstractItemView
)
from PySide6.QtCore import Qt, QSize
from PySide6.QtGui import QFont

# Setup path and import cryptographic logic
sys.path.append(os.path.abspath(os.path.dirname(os.path.dirname(__file__))))
from src.utils.crypto import generate_signature

ADMIN_DB_PATH = os.path.expanduser("~/.academyos/admin_licensing.db")

class LicenseAdminApp(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("AcademyOS Desktop — License & Customer Administrator")
        self.setMinimumSize(1100, 750)
        self.init_database()
        self.init_ui()
        self.refresh_all_views()
        
    def init_database(self):
        os.makedirs(os.path.dirname(ADMIN_DB_PATH), exist_ok=True)
        conn = sqlite3.connect(ADMIN_DB_PATH)
        cursor = conn.cursor()
        
        # 1. Customer Licenses Table
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS customer_licenses (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                customer_name TEXT NOT NULL,
                institute_name TEXT NOT NULL,
                mobile TEXT NOT NULL,
                email TEXT,
                device_fingerprint TEXT,
                license_key TEXT,
                duration_months INTEGER NOT NULL,
                expiry_date TEXT NOT NULL, -- YYYY-MM-DD
                status TEXT NOT NULL CHECK(status IN ('Active', 'Expired', 'Revoked', 'Disabled', 'Pending')) DEFAULT 'Pending',
                notes TEXT,
                created_at TEXT DEFAULT (datetime('now', 'localtime')),
                updated_at TEXT DEFAULT (datetime('now', 'localtime'))
            );
        """)
        
        # 2. License History Audit Table
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS license_history (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                customer_id INTEGER,
                action TEXT NOT NULL, -- 'GENERATE', 'RENEW', 'EXTEND', 'REVOKE', 'DISABLE'
                old_expiry TEXT,
                new_expiry TEXT,
                details TEXT,
                timestamp TEXT DEFAULT (datetime('now', 'localtime')),
                FOREIGN KEY(customer_id) REFERENCES customer_licenses(id) ON DELETE CASCADE
            );
        """)
        conn.commit()
        conn.close()
        
    def init_ui(self):
        # Global stylesheet
        self.setStyleSheet("""
            QMainWindow {
                background-color: #F8FAFC;
            }
            QGroupBox {
                font-weight: bold;
                border: 1px solid #E2E8F0;
                border-radius: 6px;
                margin-top: 12px;
                padding-top: 12px;
                background-color: #FFFFFF;
            }
            QGroupBox::title {
                subcontrol-origin: margin;
                left: 8px;
                padding: 0 3px 0 3px;
                color: #1E293B;
            }
            QTableWidget {
                border: 1px solid #E2E8F0;
                border-radius: 4px;
                gridline-color: #F1F5F9;
                background-color: #FFFFFF;
                alternate-background-color: #F8FAFC;
            }
            QHeaderView::section {
                background-color: #0F172A;
                color: #FFFFFF;
                padding: 6px;
                border: none;
                font-weight: bold;
            }
            QPushButton {
                background-color: #0F172A;
                color: #FFFFFF;
                border: none;
                border-radius: 4px;
                padding: 8px 16px;
                font-weight: bold;
            }
            QPushButton:hover {
                background-color: #1E293B;
            }
            QPushButton#SecondaryButton {
                background-color: #64748B;
            }
            QPushButton#SecondaryButton:hover {
                background-color: #475569;
            }
            QPushButton#DestructiveButton {
                background-color: #DC2626;
            }
            QPushButton#DestructiveButton:hover {
                background-color: #B91C1C;
            }
            QLineEdit, QComboBox, QTextEdit {
                border: 1px solid #CBD5E1;
                border-radius: 4px;
                padding: 6px;
                background-color: #FFFFFF;
            }
            QLineEdit:focus, QComboBox:focus, QTextEdit:focus {
                border: 1px solid #3B82F6;
            }
        """)
        
        central_widget = QWidget()
        self.setCentralWidget(central_widget)
        main_layout = QVBoxLayout(central_widget)
        
        # Header banner
        header = QLabel("<h2>AcademyOS License Administration Dashboard</h2>")
        header.setStyleSheet("color: #0F172A; padding: 4px;")
        main_layout.addWidget(header)
        
        # Tab Widget
        self.tabs = QTabWidget()
        main_layout.addWidget(self.tabs)
        
        # Setup Tabs
        self.tab_generator = QWidget()
        self.tab_active = QWidget()
        self.tab_expiring = QWidget()
        self.tab_expired = QWidget()
        self.tab_revoked = QWidget()
        self.tab_search = QWidget()
        self.tab_queries = QWidget()
        
        self.tabs.addTab(self.tab_generator, "Generate & Update License")
        self.tabs.addTab(self.tab_active, "Active Licenses")
        self.tabs.addTab(self.tab_expiring, "Expiring Soon")
        self.tabs.addTab(self.tab_expired, "Expired Licenses")
        self.tabs.addTab(self.tab_revoked, "Revoked Licenses")
        self.tabs.addTab(self.tab_search, "Search & History")
        self.tabs.addTab(self.tab_queries, "Customer Management")
        
        self.setup_generator_tab()
        self.setup_active_tab()
        self.setup_expiring_tab()
        self.setup_expired_tab()
        self.setup_revoked_tab()
        self.setup_search_tab()
        self.setup_queries_tab()
        
    def setup_generator_tab(self):
        layout = QHBoxLayout(self.tab_generator)
        
        # Form Column
        form_group = QGroupBox("License Details Form")
        form_layout = QFormLayout(form_group)
        
        self.txt_name = QLineEdit()
        self.txt_institute = QLineEdit()
        self.txt_mobile = QLineEdit()
        self.txt_email = QLineEdit()
        
        self.cb_duration = QComboBox()
        self.cb_duration.addItems(["1 Month", "3 Months", "4 Months", "6 Months", "12 Months"])
        self.cb_duration.currentIndexChanged.connect(self.calculate_auto_expiry)
        
        self.txt_expiry = QLineEdit()
        self.txt_expiry.setPlaceholderText("YYYY-MM-DD")
        self.calculate_auto_expiry()
        
        self.txt_fp = QLineEdit()
        self.txt_fp.setPlaceholderText("64-character SHA-256 fingerprint from client")
        
        self.txt_notes = QTextEdit()
        self.txt_notes.setMaximumHeight(100)
        
        form_layout.addRow("Customer Name *:", self.txt_name)
        form_layout.addRow("Institute Name *:", self.txt_institute)
        form_layout.addRow("Mobile Number *:", self.txt_mobile)
        form_layout.addRow("Email Address:", self.txt_email)
        form_layout.addRow("License Duration:", self.cb_duration)
        form_layout.addRow("Expiry Date (YYYY-MM-DD):", self.txt_expiry)
        form_layout.addRow("Device Fingerprint *:", self.txt_fp)
        form_layout.addRow("Notes / Remarks:", self.txt_notes)
        
        btn_generate = QPushButton("Generate Activation Key")
        btn_generate.clicked.connect(self.generate_license)
        form_layout.addRow("", btn_generate)
        
        layout.addWidget(form_group, 2)
        
        # Generated Output Column
        output_group = QGroupBox("Operations Console & Keys Output")
        output_layout = QVBoxLayout(output_group)
        
        output_layout.addWidget(QLabel("<b>Generated License Key:</b>"))
        self.txt_out_key = QTextEdit()
        self.txt_out_key.setReadOnly(True)
        output_layout.addWidget(self.txt_out_key)
        
        btn_copy = QPushButton("Copy Key to Clipboard")
        btn_copy.setObjectName("SecondaryButton")
        btn_copy.clicked.connect(self.copy_key_to_clipboard)
        output_layout.addWidget(btn_copy)
        
        output_layout.addWidget(QLabel("<b>License Key Operations</b>"))
        
        op_layout = QHBoxLayout()
        self.btn_renew = QPushButton("Renew Selected")
        self.btn_renew.setObjectName("SecondaryButton")
        self.btn_renew.clicked.connect(self.renew_license_action)
        op_layout.addWidget(self.btn_renew)
        
        self.btn_extend = QPushButton("Extend Selected")
        self.btn_extend.setObjectName("SecondaryButton")
        self.btn_extend.clicked.connect(self.extend_license_action)
        op_layout.addWidget(self.btn_extend)
        
        self.btn_revoke = QPushButton("Revoke Selected")
        self.btn_revoke.setObjectName("DestructiveButton")
        self.btn_revoke.clicked.connect(self.revoke_license_action)
        op_layout.addWidget(self.btn_revoke)
        
        output_layout.addLayout(op_layout)
        layout.addWidget(output_group, 1)

    def calculate_auto_expiry(self):
        duration_str = self.cb_duration.currentText()
        months = int(duration_str.split()[0])
        # Map months to days
        days = {1: 30, 3: 90, 4: 120, 6: 180, 12: 365}[months]
        expiry = datetime.date.today() + datetime.timedelta(days=days)
        self.txt_expiry.setText(expiry.strftime("%Y-%m-%d"))
        
    def generate_license(self):
        name = self.txt_name.text().strip()
        inst = self.txt_institute.text().strip()
        mobile = self.txt_mobile.text().strip()
        email = self.txt_email.text().strip()
        expiry_str = self.txt_expiry.text().strip()
        fp = self.txt_fp.text().strip()
        notes = self.txt_notes.toPlainText().strip()
        
        if not name or not inst or not mobile or not fp:
            QMessageBox.warning(self, "Validation Error", "Please fill in Customer Name, Institute Name, Mobile, and Device Fingerprint.")
            return
            
        try:
            datetime.datetime.strptime(expiry_str, "%Y-%m-%d")
        except ValueError:
            QMessageBox.warning(self, "Validation Error", "Expiry Date must be in YYYY-MM-DD format.")
            return
            
        # Cryptographic activation key generation
        license_base = f"AOS-KEY-{expiry_str}"
        try:
            sig = generate_signature(license_base, expiry_str, fp)
            activation_key = f"AOS-KEY-{expiry_str}-{sig}"
        except Exception as e:
            QMessageBox.critical(self, "Cryptographic Error", f"Failed to compute HMAC signature. AOS_SIGNING_SALT env variable may be unset or invalid: {e}")
            return
            
        # Store in database
        duration_str = self.cb_duration.currentText()
        months = int(duration_str.split()[0])
        
        conn = sqlite3.connect(ADMIN_DB_PATH)
        cursor = conn.cursor()
        
        # Check if client with this fingerprint already exists
        cursor.execute("SELECT id FROM customer_licenses WHERE device_fingerprint = ?;", (fp,))
        exists = cursor.fetchone()
        
        if exists:
            c_id = exists[0]
            cursor.execute("""
                UPDATE customer_licenses 
                SET customer_name = ?, institute_name = ?, mobile = ?, email = ?, license_key = ?, duration_months = ?, expiry_date = ?, status = 'Active', notes = ?, updated_at = datetime('now', 'localtime')
                WHERE id = ?;
            """, (name, inst, mobile, email, activation_key, months, expiry_str, notes, c_id))
            action = "GENERATE_OVERWRITE"
        else:
            cursor.execute("""
                INSERT INTO customer_licenses (customer_name, institute_name, mobile, email, device_fingerprint, license_key, duration_months, expiry_date, status, notes)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, 'Active', ?);
            """, (name, inst, mobile, email, fp, activation_key, months, expiry_str, notes))
            c_id = cursor.lastrowid
            action = "GENERATE"
            
        # Log audit history
        cursor.execute("""
            INSERT INTO license_history (customer_id, action, old_expiry, new_expiry, details)
            VALUES (?, ?, NULL, ?, ?);
        """, (c_id, action, expiry_str, f"Generated key with duration {duration_str}"))
        
        conn.commit()
        conn.close()
        
        self.txt_out_key.setText(activation_key)
        QMessageBox.information(self, "Key Generated", "Activation license generated and logged successfully.")
        self.refresh_all_views()
        
    def copy_key_to_clipboard(self):
        key = self.txt_out_key.toPlainText().strip()
        if key:
            QApplication.clipboard().setText(key)
            QMessageBox.information(self, "Clipboard", "Activation license key copied to clipboard.")
            
    def renew_license_action(self):
        # Select active customer from search or list and load it into form
        selected_id = self.get_selected_license_id()
        if not selected_id:
            return
            
        # Calculate new expiry based on currently selected duration
        duration_str = self.cb_duration.currentText()
        months = int(duration_str.split()[0])
        days = {1: 30, 3: 90, 4: 120, 6: 180, 12: 365}[months]
        
        conn = sqlite3.connect(ADMIN_DB_PATH)
        cursor = conn.cursor()
        cursor.execute("SELECT customer_name, device_fingerprint, expiry_date FROM customer_licenses WHERE id = ?;", (selected_id,))
        row = cursor.fetchone()
        if not row:
            conn.close()
            return
            
        name, fp, old_expiry_str = row
        
        # New expiry: check if old license is still valid. If yes, add to old expiry. If not, add to today.
        try:
            old_expiry = datetime.datetime.strptime(old_expiry_str, "%Y-%m-%d").date()
            base_date = max(datetime.date.today(), old_expiry)
        except ValueError:
            base_date = datetime.date.today()
            
        new_expiry = base_date + datetime.timedelta(days=days)
        new_expiry_str = new_expiry.strftime("%Y-%m-%d")
        
        # Cryptographic key
        license_base = f"AOS-KEY-{new_expiry_str}"
        sig = generate_signature(license_base, new_expiry_str, fp)
        activation_key = f"AOS-KEY-{new_expiry_str}-{sig}"
        
        cursor.execute("""
            UPDATE customer_licenses
            SET license_key = ?, duration_months = ?, expiry_date = ?, status = 'Active', updated_at = datetime('now', 'localtime')
            WHERE id = ?;
        """, (activation_key, months, new_expiry_str, selected_id))
        
        cursor.execute("""
            INSERT INTO license_history (customer_id, action, old_expiry, new_expiry, details)
            VALUES (?, 'RENEW', ?, ?, ?);
        """, (selected_id, old_expiry_str, new_expiry_str, f"Renewed license for {duration_str}"))
        
        conn.commit()
        conn.close()
        
        self.txt_out_key.setText(activation_key)
        QMessageBox.information(self, "License Renewed", f"Successfully renewed license for {name} until {new_expiry_str}.")
        self.refresh_all_views()
        
    def extend_license_action(self):
        selected_id = self.get_selected_license_id()
        if not selected_id:
            return
            
        # Extend by adding 30 days
        conn = sqlite3.connect(ADMIN_DB_PATH)
        cursor = conn.cursor()
        cursor.execute("SELECT customer_name, device_fingerprint, expiry_date FROM customer_licenses WHERE id = ?;", (selected_id,))
        row = cursor.fetchone()
        if not row:
            conn.close()
            return
            
        name, fp, old_expiry_str = row
        try:
            old_expiry = datetime.datetime.strptime(old_expiry_str, "%Y-%m-%d").date()
        except ValueError:
            old_expiry = datetime.date.today()
            
        new_expiry = old_expiry + datetime.timedelta(days=30)
        new_expiry_str = new_expiry.strftime("%Y-%m-%d")
        
        # Crypto key
        license_base = f"AOS-KEY-{new_expiry_str}"
        sig = generate_signature(license_base, new_expiry_str, fp)
        activation_key = f"AOS-KEY-{new_expiry_str}-{sig}"
        
        cursor.execute("""
            UPDATE customer_licenses
            SET license_key = ?, expiry_date = ?, status = 'Active', updated_at = datetime('now', 'localtime')
            WHERE id = ?;
        """, (activation_key, new_expiry_str, selected_id))
        
        cursor.execute("""
            INSERT INTO license_history (customer_id, action, old_expiry, new_expiry, details)
            VALUES (?, 'EXTEND', ?, ?, 'Extended license duration by 30 days');
        """, (selected_id, old_expiry_str, new_expiry_str))
        
        conn.commit()
        conn.close()
        
        self.txt_out_key.setText(activation_key)
        QMessageBox.information(self, "License Extended", f"Extended license for {name} by 30 days (new expiry: {new_expiry_str}).")
        self.refresh_all_views()
        
    def revoke_license_action(self):
        selected_id = self.get_selected_license_id()
        if not selected_id:
            return
            
        confirm = QMessageBox.question(self, "Confirm Revocation", "Are you sure you want to revoke/disable the selected license?", QMessageBox.Yes | QMessageBox.No)
        if confirm != QMessageBox.Yes:
            return
            
        conn = sqlite3.connect(ADMIN_DB_PATH)
        cursor = conn.cursor()
        cursor.execute("SELECT customer_name, expiry_date FROM customer_licenses WHERE id = ?;", (selected_id,))
        row = cursor.fetchone()
        if not row:
            conn.close()
            return
            
        name, expiry_str = row
        
        cursor.execute("""
            UPDATE customer_licenses
            SET status = 'Revoked', updated_at = datetime('now', 'localtime')
            WHERE id = ?;
        """, (selected_id,))
        
        cursor.execute("""
            INSERT INTO license_history (customer_id, action, old_expiry, new_expiry, details)
            VALUES (?, 'REVOKE', ?, NULL, 'Revoked license manually');
        """, (selected_id, expiry_str))
        
        conn.commit()
        conn.close()
        
        self.txt_out_key.clear()
        QMessageBox.information(self, "License Revoked", f"License for {name} has been revoked.")
        self.refresh_all_views()
        
    def get_selected_license_id(self) -> int:
        active_tab = self.tabs.currentIndex()
        table = None
        if active_tab == 1:
            table = self.tbl_active
        elif active_tab == 2:
            table = self.tbl_expiring
        elif active_tab == 3:
            table = self.tbl_expired
        elif active_tab == 4:
            table = self.tbl_revoked
        elif active_tab == 5:
            table = self.tbl_search
            
        if not table:
            QMessageBox.information(self, "Select Row", "Please select a customer row from any database lists tab first.")
            return 0
            
        row = table.currentRow()
        if row < 0:
            QMessageBox.information(self, "Select Row", "Please click on a customer row inside the table to select it.")
            return 0
            
        return int(table.item(row, 0).text())
        
    def setup_active_tab(self):
        layout = QVBoxLayout(self.tab_active)
        self.tbl_active = QTableWidget()
        self.setup_table_headers(self.tbl_active)
        layout.addWidget(self.tbl_active)
        
    def setup_expiring_tab(self):
        layout = QVBoxLayout(self.tab_expiring)
        self.tbl_expiring = QTableWidget()
        self.setup_table_headers(self.tbl_expiring)
        layout.addWidget(self.tbl_expiring)
        
    def setup_expired_tab(self):
        layout = QVBoxLayout(self.tab_expired)
        self.tbl_expired = QTableWidget()
        self.setup_table_headers(self.tbl_expired)
        layout.addWidget(self.tbl_expired)
        
    def setup_revoked_tab(self):
        layout = QVBoxLayout(self.tab_revoked)
        self.tbl_revoked = QTableWidget()
        self.setup_table_headers(self.tbl_revoked)
        layout.addWidget(self.tbl_revoked)
        
    def setup_search_tab(self):
        layout = QVBoxLayout(self.tab_search)
        
        search_layout = QHBoxLayout()
        self.txt_search = QLineEdit()
        self.txt_search.setPlaceholderText("Search customers by name, institute, email, or fingerprint...")
        self.txt_search.textChanged.connect(self.search_licenses_action)
        search_layout.addWidget(self.txt_search)
        
        btn_search = QPushButton("Run Query")
        btn_search.clicked.connect(self.search_licenses_action)
        search_layout.addWidget(btn_search)
        layout.addLayout(search_layout)
        
        self.tbl_search = QTableWidget()
        self.setup_table_headers(self.tbl_search)
        layout.addWidget(self.tbl_search)
        
        # History panel
        history_group = QGroupBox("Action Audit Logs History")
        h_layout = QVBoxLayout(history_group)
        self.tbl_history = QTableWidget()
        self.tbl_history.setColumnCount(4)
        self.tbl_history.setHorizontalHeaderLabels(["Timestamp", "Action", "Old Expiry", "Details"])
        self.tbl_history.horizontalHeader().setSectionResizeMode(QHeaderView.Stretch)
        self.tbl_history.setSelectionBehavior(QAbstractItemView.SelectRows)
        h_layout.addWidget(self.tbl_history)
        layout.addWidget(history_group)
        
        self.tbl_search.itemClicked.connect(self.load_license_history)

    def setup_queries_tab(self):
        layout = QVBoxLayout(self.tab_queries)
        
        grid = QVBoxLayout()
        
        self.lbl_active_count = QLabel("<b>Active Customers:</b> 0")
        self.lbl_month_expiry = QLabel("<b>Expiring This Month:</b> 0")
        self.lbl_week_expiry = QLabel("<b>Expiring In Next 7 Days:</b> 0")
        self.lbl_renewed_recent = QLabel("<b>Renewed Recently (last 14 days):</b> 0")
        self.lbl_never_activated = QLabel("<b>Registered (Pending Activation):</b> 0")
        self.lbl_revoked_count = QLabel("<b>Total Licenses Revoked:</b> 0")
        
        for lbl in (self.lbl_active_count, self.lbl_month_expiry, self.lbl_week_expiry, 
                    self.lbl_renewed_recent, self.lbl_never_activated, self.lbl_revoked_count):
            lbl.setStyleSheet("font-size: 14px; padding: 6px; background-color: #FFFFFF; border-radius: 4px; border: 1px solid #E2E8F0;")
            grid.addWidget(lbl)
            
        layout.addLayout(grid)
        layout.addStretch()

    def setup_table_headers(self, table):
        table.setColumnCount(8)
        table.setHorizontalHeaderLabels([
            "ID", "Customer Name", "Institute Name", "Mobile",
            "Expiry Date", "Days Left", "Fingerprint", "Status"
        ])
        table.horizontalHeader().setSectionResizeMode(QHeaderView.Interactive)
        table.horizontalHeader().setSectionResizeMode(1, QHeaderView.Stretch)
        table.horizontalHeader().setSectionResizeMode(2, QHeaderView.Stretch)
        table.setSelectionBehavior(QAbstractItemView.SelectRows)
        table.setEditTriggers(QAbstractItemView.NoEditTriggers)

    def refresh_all_views(self):
        # 1. Update views
        self.load_licenses_list(self.tbl_active, "Active")
        self.load_licenses_list(self.tbl_expiring, "Expiring")
        self.load_licenses_list(self.tbl_expired, "Expired")
        self.load_licenses_list(self.tbl_revoked, "Revoked")
        
        # 2. Update administrative customer management answers
        self.update_queries_panel()

    def load_licenses_list(self, table, status_filter):
        table.setRowCount(0)
        conn = sqlite3.connect(ADMIN_DB_PATH)
        conn.row_factory = sqlite3.Row
        cursor = conn.cursor()
        
        today = datetime.date.today().strftime("%Y-%m-%d")
        
        if status_filter == "Active":
            cursor.execute("SELECT * FROM customer_licenses WHERE status = 'Active' AND expiry_date >= ? ORDER BY expiry_date ASC;", (today,))
        elif status_filter == "Expiring":
            # Expires within next 30 days
            expiry_limit = (datetime.date.today() + datetime.timedelta(days=30)).strftime("%Y-%m-%d")
            cursor.execute("SELECT * FROM customer_licenses WHERE status = 'Active' AND expiry_date >= ? AND expiry_date <= ? ORDER BY expiry_date ASC;", (today, expiry_limit))
        elif status_filter == "Expired":
            cursor.execute("SELECT * FROM customer_licenses WHERE expiry_date < ? OR status = 'Expired' ORDER BY expiry_date DESC;", (today,))
        elif status_filter == "Revoked":
            cursor.execute("SELECT * FROM customer_licenses WHERE status IN ('Revoked', 'Disabled') ORDER BY updated_at DESC;")
            
        rows = cursor.fetchall()
        self.populate_table(table, rows)
        conn.close()

    def populate_table(self, table, rows):
        table.setRowCount(len(rows))
        for row_idx, row in enumerate(rows):
            # Calculate days left
            try:
                exp = datetime.datetime.strptime(row["expiry_date"], "%Y-%m-%d").date()
                days_left = (exp - datetime.date.today()).days
            except ValueError:
                days_left = 0
                
            table.setItem(row_idx, 0, QTableWidgetItem(str(row["id"])))
            table.setItem(row_idx, 1, QTableWidgetItem(row["customer_name"]))
            table.setItem(row_idx, 2, QTableWidgetItem(row["institute_name"]))
            table.setItem(row_idx, 3, QTableWidgetItem(row["mobile"]))
            table.setItem(row_idx, 4, QTableWidgetItem(row["expiry_date"]))
            table.setItem(row_idx, 5, QTableWidgetItem(f"{days_left} days" if days_left >= 0 else "Expired"))
            table.setItem(row_idx, 6, QTableWidgetItem(row["device_fingerprint"] or "N/A"))
            table.setItem(row_idx, 7, QTableWidgetItem(row["status"]))

    def search_licenses_action(self):
        query = self.txt_search.text().strip()
        if not query:
            self.tbl_search.setRowCount(0)
            return
            
        conn = sqlite3.connect(ADMIN_DB_PATH)
        conn.row_factory = sqlite3.Row
        cursor = conn.cursor()
        
        like_q = f"%{query}%"
        cursor.execute("""
            SELECT * FROM customer_licenses
            WHERE customer_name LIKE ? OR institute_name LIKE ? OR mobile LIKE ? OR email LIKE ? OR device_fingerprint LIKE ?
            ORDER BY customer_name ASC;
        """, (like_q, like_q, like_q, like_q, like_q))
        
        rows = cursor.fetchall()
        self.populate_table(self.tbl_search, rows)
        conn.close()

    def load_license_history(self, item):
        row = self.tbl_search.currentRow()
        c_id = int(self.tbl_search.item(row, 0).text())
        
        self.tbl_history.setRowCount(0)
        conn = sqlite3.connect(ADMIN_DB_PATH)
        conn.row_factory = sqlite3.Row
        cursor = conn.cursor()
        cursor.execute("SELECT * FROM license_history WHERE customer_id = ? ORDER BY timestamp DESC;", (c_id,))
        rows = cursor.fetchall()
        
        self.tbl_history.setRowCount(len(rows))
        for idx, r in enumerate(rows):
            self.tbl_history.setItem(idx, 0, QTableWidgetItem(r["timestamp"]))
            self.tbl_history.setItem(idx, 1, QTableWidgetItem(r["action"]))
            self.tbl_history.setItem(idx, 2, QTableWidgetItem(r["old_expiry"] or "N/A"))
            self.tbl_history.setItem(idx, 3, QTableWidgetItem(r["details"] or ""))
            
        conn.close()

    def update_queries_panel(self):
        conn = sqlite3.connect(ADMIN_DB_PATH)
        cursor = conn.cursor()
        
        today = datetime.date.today()
        today_str = today.strftime("%Y-%m-%d")
        
        # 1. Active Customers count
        cursor.execute("SELECT COUNT(*) FROM customer_licenses WHERE status = 'Active' AND expiry_date >= ?;", (today_str,))
        active = cursor.fetchone()[0]
        
        # 2. Expiring this month
        next_month = today.month + 1 if today.month < 12 else 1
        year = today.year if today.month < 12 else today.year + 1
        end_of_month = (datetime.date(year, next_month, 1) - datetime.timedelta(days=1)).strftime("%Y-%m-%d")
        cursor.execute("SELECT COUNT(*) FROM customer_licenses WHERE status = 'Active' AND expiry_date >= ? AND expiry_date <= ?;", (today_str, end_of_month))
        exp_month = cursor.fetchone()[0]
        
        # 3. Expiring in next 7 days
        next_week_str = (today + datetime.timedelta(days=7)).strftime("%Y-%m-%d")
        cursor.execute("SELECT COUNT(*) FROM customer_licenses WHERE status = 'Active' AND expiry_date >= ? AND expiry_date <= ?;", (today_str, next_week_str))
        exp_week = cursor.fetchone()[0]
        
        # 4. Renewed recently (last 14 days)
        recent_renew = (today - datetime.timedelta(days=14)).strftime("%Y-%m-%d %H:%M:%S")
        cursor.execute("SELECT COUNT(DISTINCT customer_id) FROM license_history WHERE action = 'RENEW' AND timestamp >= ?;", (recent_renew,))
        renewed = cursor.fetchone()[0]
        
        # 5. Registered / Pending Activation
        cursor.execute("SELECT COUNT(*) FROM customer_licenses WHERE status = 'Pending';")
        pending = cursor.fetchone()[0]
        
        # 6. Revoked
        cursor.execute("SELECT COUNT(*) FROM customer_licenses WHERE status = 'Revoked';")
        revoked = cursor.fetchone()[0]
        
        conn.close()
        
        self.lbl_active_count.setText(f"<b>1. Active Customers:</b> {active}")
        self.lbl_month_expiry.setText(f"<b>2. Expiring This Month:</b> {exp_month}")
        self.lbl_week_expiry.setText(f"<b>3. Expiring In Next 7 Days:</b> {exp_week}")
        self.lbl_renewed_recent.setText(f"<b>4. Renewed Recently (Last 14 Days):</b> {renewed}")
        self.lbl_never_activated.setText(f"<b>5. Registered (Pending Activation):</b> {pending}")
        self.lbl_revoked_count.setText(f"<b>6. Total Licenses Revoked:</b> {revoked}")

def main():
    app = QApplication(sys.argv)
    window = LicenseAdminApp()
    window.show()
    sys.exit(app.exec())

if __name__ == "__main__":
    main()
