from PySide6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QFormLayout, QLineEdit,
    QPushButton, QLabel, QMessageBox, QGroupBox, QComboBox, QDialog
)
from PySide6.QtCore import Qt
import logging
import os

from src.utils.config import load_settings, save_settings
from src.engines.backup import perform_backup
from src.engines.license import check_license_status, check_hardware_compatibility
from src.ui.dialogs import ActivationDialog, CourseFormDialog

class SettingsTab(QWidget):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.init_ui()
        self.load_configuration()
        self.refresh_health_status()
        
    def init_ui(self):
        layout = QVBoxLayout(self)
        layout.setContentsMargins(16, 16, 16, 16)
        
        # --- HEALTH STATE INDICATOR ---
        self.lbl_health = QLabel("<h3>System Health: Checking...</h3>")
        self.lbl_health.setStyleSheet("background-color: #E2E8F0; padding: 8px; border-radius: 4px; font-weight: bold;")
        layout.addWidget(self.lbl_health)
        
        # --- INSTITUTION PROFILE GROUP ---
        profile_group = QGroupBox("Institution Profile Settings")
        profile_layout = QFormLayout(profile_group)
        
        self.txt_name = QLineEdit()
        self.txt_phone = QLineEdit()
        self.txt_email = QLineEdit()
        self.txt_address = QLineEdit()
        
        profile_layout.addRow("Institution Name *:", self.txt_name)
        profile_layout.addRow("Contact Phone No:", self.txt_phone)
        profile_layout.addRow("Institution Email Address:", self.txt_email)
        profile_layout.addRow("Physical Address:", self.txt_address)
        
        btn_save_config = QPushButton("Save Institutional Profile")
        btn_save_config.clicked.connect(self.save_configuration)
        profile_layout.addRow("", btn_save_config)
        
        layout.addWidget(profile_group)
        
        # --- QUICK TOOLS & BACKUP GROUP ---
        tools_group = QGroupBox("Maintenance & Database Operations")
        tools_layout = QHBoxLayout(tools_group)
        
        btn_backup = QPushButton("Trigger Manual System Backup Now")
        btn_backup.clicked.connect(self.run_backup)
        tools_layout.addWidget(btn_backup)
        
        btn_add_course = QPushButton("Register New Course")
        btn_add_course.setObjectName("SecondaryButton")
        btn_add_course.clicked.connect(self.register_course)
        tools_layout.addWidget(btn_add_course)
        
        layout.addWidget(tools_group)
        
        # --- LICENSING SYSTEM STATUS ---
        license_group = QGroupBox("Software Subscription Licensing")
        license_layout = QFormLayout(license_group)
        
        self.lbl_license_state = QLabel("Licensing State: Unchecked")
        self.lbl_license_state.setStyleSheet("font-weight: bold; font-size: 13px;")
        license_layout.addRow(self.lbl_license_state)
        
        self.btn_activate = QPushButton("Enter Activation License Key")
        self.btn_activate.clicked.connect(self.activate_license)
        license_layout.addRow(self.btn_activate)
        
        layout.addWidget(license_group)
        
        # --- SYSTEM USER MANUAL HELP PANEL ---
        help_group = QGroupBox("Operations Quick Reference Manual")
        help_layout = QVBoxLayout(help_group)
        
        guide_text = QLabel(
            "<b>1. Daily Admission:</b> Use the 'Student Profile' tab to register students and enroll them in active courses.<br/>"
            "<b>2. Fee Installments:</b> Use 'Outstanding Dues' tab or the student detail panel to collect payment installments. Click 'Yes' to print PDF receipt invoices.<br/>"
            "<b>3. Daily Backups:</b> Automatic database backups are compiled into your backup folder on startup. You can trigger manual archives above.<br/>"
            "<b>4. Staging Data Import:</b> Upload excel worksheets in the 'Data Pipeline' tab, inspect field validation highlighted error labels, and commit."
        )
        guide_text.setWordWrap(True)
        guide_text.setStyleSheet("color: #475569; font-size: 12px; line-height: 16px;")
        help_layout.addWidget(guide_text)
        
        layout.addWidget(help_group)
        layout.addStretch()
        
    def load_configuration(self):
        settings = load_settings()
        self.txt_name.setText(settings["institution_name"])
        self.txt_phone.setText(settings["institution_phone"])
        self.txt_email.setText(settings["institution_email"])
        self.txt_address.setText(settings["institution_address"])
        
    def save_configuration(self):
        name = self.txt_name.text().strip()
        if not name:
            QMessageBox.warning(self, "Required", "Institution name cannot be blank.")
            return
            
        settings = load_settings()
        settings["institution_name"] = name
        settings["institution_phone"] = self.txt_phone.text().strip()
        settings["institution_email"] = self.txt_email.text().strip()
        settings["institution_address"] = self.txt_address.text().strip()
        
        if save_settings(settings):
            QMessageBox.information(self, "Saved", "Profile configurations successfully written to settings.json.")
        else:
            QMessageBox.critical(self, "Error", "Failed to write settings file.")
            
    def run_backup(self):
        success, path, err = perform_backup()
        if success:
            QMessageBox.information(
                self, "Backup Complete",
                f"Full system backup archive completed successfully!\nFile Location:\n{path}"
            )
        else:
            QMessageBox.critical(self, "Backup Failed", f"Could not create database backup: {err}")
            
    def register_course(self):
        dlg = CourseFormDialog(self)
        if dlg.exec() == QDialog.Accepted:
            QMessageBox.information(self, "Course Added", "Course successfully saved to active courses registry.")
            self.window().refresh_all_tabs()
            
    def activate_license(self):
        dlg = ActivationDialog(self)
        if dlg.exec() == QDialog.Accepted:
            self.refresh_health_status()
            self.window().refresh_all_tabs()
            
    def refresh_health_status(self):
        # 1. Check Licensing
        lic = check_license_status()
        if lic["activated"]:
            self.lbl_license_state.setText(f"Active License - Expiring Date: {lic['expiry_date']} ({lic['days_remaining']} days remaining)")
            self.lbl_license_state.setStyleSheet("color: green; font-weight: bold;")
        else:
            self.lbl_license_state.setText(f"UNLICENSED CLIENT - Error details: {lic['error']}")
            self.lbl_license_state.setStyleSheet("color: red; font-weight: bold;")
            
        # 2. Check Hardware & RAM Metrics
        comp, details, warnings = check_hardware_compatibility()
        
        if warnings:
            self.lbl_health.setText(f"System Health: WARNING (RAM resources low)")
            self.lbl_health.setStyleSheet("background-color: #FEF3C7; color: #D97706; padding: 8px; border-radius: 4px; font-weight: bold;")
        elif not lic["activated"]:
            self.lbl_health.setText("System Health: ERROR (Activation required)")
            self.lbl_health.setStyleSheet("background-color: #FEE2E2; color: #DC2626; padding: 8px; border-radius: 4px; font-weight: bold;")
        else:
            self.lbl_health.setText("System Health: WORKING NORMAL")
            self.lbl_health.setStyleSheet("background-color: #D1FAE5; color: #059669; padding: 8px; border-radius: 4px; font-weight: bold;")
