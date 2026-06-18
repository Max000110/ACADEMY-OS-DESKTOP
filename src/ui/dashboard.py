from PySide6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QGridLayout, QLabel,
    QTableWidget, QTableWidgetItem, QHeaderView, QFrame
)
from PySide6.QtCore import Qt
import logging
import json

from src.database.queries import get_dashboard_stats
from src.database.connection import get_connection

class DashboardTab(QWidget):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.init_ui()
        self.refresh_data()
        
    def init_ui(self):
        layout = QVBoxLayout(self)
        layout.setContentsMargins(16, 16, 16, 16)
        layout.setSpacing(20)
        
        # 1. Header Welcome
        welcome_lbl = QLabel("<h2>Dashboard Overview</h2>")
        layout.addWidget(welcome_lbl)
        
        # 2. Metric Cards Grid
        self.cards_layout = QGridLayout()
        self.cards_layout.setSpacing(16)
        
        # Card 1: Active Students
        self.card_students = self.create_metric_card("Active Students", "0")
        self.cards_layout.addWidget(self.card_students, 0, 0)
        
        # Card 2: Active Leads
        self.card_leads = self.create_metric_card("Active Enquiries/Leads", "0")
        self.cards_layout.addWidget(self.card_leads, 0, 1)
        
        # Card 3: Total Collections
        self.card_collected = self.create_metric_card("Total Collected", "$0.00")
        self.cards_layout.addWidget(self.card_collected, 0, 2)
        
        # Card 4: Pending Dues
        self.card_dues = self.create_metric_card("Outstanding Balance", "$0.00")
        self.cards_layout.addWidget(self.card_dues, 0, 3)
        
        layout.addLayout(self.cards_layout)
        
        # 3. Recent Activity Log Grid Block
        activity_title = QLabel("<h3>Recent Operations Audit Trail</h3>")
        layout.addWidget(activity_title)
        
        self.table_logs = QTableWidget()
        self.table_logs.setColumnCount(3)
        self.table_logs.setHorizontalHeaderLabels(["Timestamp", "Operation Action", "Details"])
        self.table_logs.horizontalHeader().setSectionResizeMode(0, QHeaderView.ResizeMode.ResizeToContents)
        self.table_logs.horizontalHeader().setSectionResizeMode(1, QHeaderView.ResizeMode.ResizeToContents)
        self.table_logs.horizontalHeader().setSectionResizeMode(2, QHeaderView.ResizeMode.Stretch)
        self.table_logs.setEditTriggers(QTableWidget.NoEditTriggers)
        self.table_logs.setSelectionBehavior(QTableWidget.SelectRows)
        self.table_logs.setAlternatingRowColors(True)
        
        layout.addWidget(self.table_logs)
        
    def create_metric_card(self, title: str, value: str) -> QFrame:
        card = QFrame()
        card.setObjectName("MetricCard")
        card.setFrameShape(QFrame.StyledPanel)
        
        card_layout = QVBoxLayout(card)
        card_layout.setSpacing(6)
        
        title_lbl = QLabel(title)
        title_lbl.setObjectName("MetricTitle")
        
        val_lbl = QLabel(value)
        val_lbl.setObjectName("MetricValue")
        
        card_layout.addWidget(title_lbl)
        card_layout.addWidget(val_lbl)
        
        # Keep references to label variables to update them
        card.title_lbl = title_lbl
        card.val_lbl = val_lbl
        return card
        
    def refresh_data(self):
        try:
            # 1. Update stats
            stats = get_dashboard_stats()
            self.card_students.val_lbl.setText(str(stats.get("active_students", 0)))
            self.card_leads.val_lbl.setText(str(stats.get("active_leads", 0)))
            self.card_collected.val_lbl.setText(f"${stats.get('total_collected', 0.0):,.2f}")
            self.card_dues.val_lbl.setText(f"${stats.get('pending_receivable', 0.0):,.2f}")
            
            # 2. Update Audit Logs Table
            conn = get_connection()
            cursor = conn.cursor()
            cursor.execute(
                """
                SELECT timestamp, user_action, details FROM audit_logs
                ORDER BY timestamp DESC, id DESC LIMIT 50;
                """
            )
            rows = cursor.fetchall()
            
            self.table_logs.setRowCount(0)
            for row_idx, row in enumerate(rows):
                self.table_logs.insertRow(row_idx)
                
                # Format timestamp
                self.table_logs.setItem(row_idx, 0, QTableWidgetItem(row["timestamp"]))
                self.table_logs.setItem(row_idx, 1, QTableWidgetItem(row["user_action"]))
                
                # Format details json
                detail_str = ""
                if row["details"]:
                    try:
                        details_dict = json.loads(row["details"])
                        detail_str = ", ".join(f"{k}: {v}" for k, v in details_dict.items())
                    except Exception:
                        detail_str = str(row["details"])
                self.table_logs.setItem(row_idx, 2, QTableWidgetItem(detail_str))
                
            cursor.close()
        except Exception as e:
            logging.error(f"Failed to refresh dashboard data: {e}")
