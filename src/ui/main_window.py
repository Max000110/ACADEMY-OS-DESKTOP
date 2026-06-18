from PySide6.QtWidgets import (
    QMainWindow, QWidget, QHBoxLayout, QVBoxLayout, QListWidget,
    QStackedWidget, QStatusBar, QLabel, QPushButton, QFileDialog, QMessageBox, QMenuBar
)
from PySide6.QtGui import QIcon
from PySide6.QtCore import QSize, Qt
import logging
import os

# Import tabs
from src.ui.dashboard import DashboardTab
from src.ui.student_tab import StudentTab
from src.ui.lead_tab import LeadTab
from src.ui.fee_tab import FeeTab
from src.ui.import_tab import ImportTab
from src.ui.settings_tab import SettingsTab

# Import engines
from src.engines.excel_export import export_all_data_to_excel
from src.engines.license import check_license_status
from src.utils.config import load_settings

class MainWindow(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("AcademyOS Desktop Client")
        self.setMinimumSize(1024, 700)
        self.init_ui()
        
    def init_ui(self):
        # Central widget layout
        central_widget = QWidget()
        self.setCentralWidget(central_widget)
        main_layout = QHBoxLayout(central_widget)
        main_layout.setContentsMargins(0, 0, 0, 0)
        main_layout.setSpacing(0)
        
        # 1. Navigation Sidebar
        self.sidebar = QListWidget()
        self.sidebar.setObjectName("SidebarList")
        self.sidebar.setFixedWidth(200)
        self.sidebar.addItems([
            "Dashboard",
            "Student Profiles",
            "Enquiry Leads",
            "Outstanding Dues",
            "Data Pipeline",
            "System Settings"
        ])
        self.sidebar.setCurrentRow(0)
        self.sidebar.currentRowChanged.connect(self.switch_tab)
        main_layout.addWidget(self.sidebar)
        
        # 2. Main Stacked Widget
        self.content_stack = QStackedWidget()
        main_layout.addWidget(self.content_stack)
        
        # Initialize tabs and add them to stack
        self.dashboard_tab = DashboardTab(self)
        self.student_tab = StudentTab(self)
        self.lead_tab = LeadTab(self)
        self.fee_tab = FeeTab(self)
        self.import_tab = ImportTab(self)
        self.settings_tab = SettingsTab(self)
        
        self.content_stack.addWidget(self.dashboard_tab)
        self.content_stack.addWidget(self.student_tab)
        self.content_stack.addWidget(self.lead_tab)
        self.content_stack.addWidget(self.fee_tab)
        self.content_stack.addWidget(self.import_tab)
        self.content_stack.addWidget(self.settings_tab)
        
        # 3. Quick Action Export Button at the top Menu Bar
        self.create_menu_bar()
        
        # 4. Status Bar Configuration
        self.status = QStatusBar()
        self.setStatusBar(self.status)
        
        self.lbl_status_db = QLabel("SQLite DB: Connected |")
        self.lbl_status_mode = QLabel("Mode: Offline First |")
        self.lbl_status_license = QLabel("Subscription: Valid")
        
        self.status.addPermanentWidget(self.lbl_status_db)
        self.status.addPermanentWidget(self.lbl_status_mode)
        self.status.addPermanentWidget(self.lbl_status_license)
        
        self.update_status_bar()
        
    def create_menu_bar(self):
        menubar = self.menuBar()
        file_menu = menubar.addMenu("&File")
        
        action_export = file_menu.addAction("Export Full Database to Excel")
        action_export.triggered.connect(self.export_excel)
        
        file_menu.addSeparator()
        
        action_exit = file_menu.addAction("Exit")
        action_exit.triggered.connect(self.close)
        
    def switch_tab(self, index: int):
        self.content_stack.setCurrentIndex(index)
        # Auto-refresh active tab data
        active_tab = self.content_stack.currentWidget()
        if hasattr(active_tab, "refresh_data"):
            active_tab.refresh_data()
        elif hasattr(active_tab, "refresh_students"):
            active_tab.refresh_students()
        elif hasattr(active_tab, "refresh_leads"):
            active_tab.refresh_leads()
        elif hasattr(active_tab, "refresh_fees"):
            active_tab.refresh_fees()
        elif hasattr(active_tab, "refresh_staging"):
            active_tab.refresh_staging()
        elif hasattr(active_tab, "refresh_health_status"):
            active_tab.refresh_health_status()
            
    def refresh_all_tabs(self):
        """Invoke refresh triggers across all modules."""
        self.dashboard_tab.refresh_data()
        self.student_tab.refresh_students()
        self.lead_tab.refresh_leads()
        self.fee_tab.refresh_fees()
        self.import_tab.refresh_staging()
        self.settings_tab.refresh_health_status()
        self.update_status_bar()
        
    def update_status_bar(self):
        lic = check_license_status()
        if lic["activated"]:
            self.lbl_status_license.setText(f"Subscription: Active ({lic['days_remaining']} days left)")
            self.lbl_status_license.setStyleSheet("color: green;")
        else:
            self.lbl_status_license.setText(f"Subscription: UNLICENSED ({lic['error']})")
            self.lbl_status_license.setStyleSheet("color: red; font-weight: bold;")
            
    def export_excel(self):
        # Save File dialog
        default_name = f"AcademyOS_Report_{os.getpid()}.xlsx"
        settings = load_settings()
        reports_dir = settings["reports_directory"]
        
        file_path, _ = QFileDialog.getSaveFileName(
            self, "Save Excel Summary Report",
            os.path.join(reports_dir, default_name),
            "Excel Workbooks (*.xlsx)"
        )
        if not file_path:
            return
            
        success, err = export_all_data_to_excel(file_path)
        if success:
            QMessageBox.information(
                self, "Export Successful",
                f"Database successfully compiled and exported to styled Excel workbook!\nSaved to:\n{file_path}"
            )
        else:
            QMessageBox.critical(self, "Export Failed", f"Excel generation failed: {err}")
