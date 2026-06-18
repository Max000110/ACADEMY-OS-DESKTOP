from PySide6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QPushButton, QTableWidget,
    QTableWidgetItem, QHeaderView, QMessageBox, QFileDialog, QComboBox, QLabel, QGroupBox
)
from PySide6.QtCore import Qt
import os
import json
import logging

from src.engines.importers import parse_csv_file, parse_xlsx_file, parse_txt_file
from src.engines.ocr_engine import run_offline_ocr, extract_entities_from_text
from src.engines.staging import stage_and_validate_records, approve_and_commit_staging
from src.database.queries import get_staging_by_status, clear_staging_imports

class ImportTab(QWidget):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.init_ui()
        self.refresh_staging()
        
    def init_ui(self):
        layout = QVBoxLayout(self)
        layout.setContentsMargins(16, 16, 16, 16)
        
        # --- UPLOAD SECTION ---
        upload_group = QGroupBox("Import Data Pipeline")
        upload_layout = QHBoxLayout(upload_group)
        
        self.combo_type = QComboBox()
        self.combo_type.addItems(["Students", "Leads"])
        upload_layout.addWidget(QLabel("<b>Staging Type:</b>"))
        upload_layout.addWidget(self.combo_type)
        
        btn_upload = QPushButton("Upload File (CSV / XLSX / TXT)")
        btn_upload.clicked.connect(self.upload_file)
        upload_layout.addWidget(btn_upload)
        
        btn_ocr = QPushButton("Scan Image/PDF Receipt (Offline OCR)")
        btn_ocr.clicked.connect(self.upload_ocr)
        btn_ocr.setObjectName("SecondaryButton")
        upload_layout.addWidget(btn_ocr)
        
        upload_layout.addStretch()
        layout.addWidget(upload_group)
        
        # --- STAGING PREVIEW SECTION ---
        staging_group = QGroupBox("Staging Buffer (Review Validation Status)")
        staging_layout = QVBoxLayout(staging_group)
        
        self.lbl_summary = QLabel("Staging is empty.")
        self.lbl_summary.setStyleSheet("font-weight: bold; color: #64748B;")
        staging_layout.addWidget(self.lbl_summary)
        
        self.table_staging = QTableWidget()
        self.table_staging.setColumnCount(4)
        self.table_staging.setHorizontalHeaderLabels(["Staging ID", "Source File", "Data Content", "Validation Error Detail"])
        self.table_staging.horizontalHeader().setSectionResizeMode(QHeaderView.ResizeMode.Interactive)
        self.table_staging.horizontalHeader().setSectionResizeMode(2, QHeaderView.ResizeMode.Stretch)
        self.table_staging.horizontalHeader().setSectionResizeMode(3, QHeaderView.ResizeMode.Stretch)
        self.table_staging.setSelectionBehavior(QTableWidget.SelectRows)
        self.table_staging.setEditTriggers(QTableWidget.NoEditTriggers)
        self.table_staging.setAlternatingRowColors(True)
        
        staging_layout.addWidget(self.table_staging)
        
        # Staging Commit Actions
        commit_layout = QHBoxLayout()
        self.btn_commit = QPushButton("Commit Valid Records to Database")
        self.btn_commit.setStyleSheet("background-color: #10B981; color: white;")
        self.btn_commit.clicked.connect(self.commit_records)
        commit_layout.addWidget(self.btn_commit)
        
        self.btn_clear = QPushButton("Clear Staging Buffer")
        self.btn_clear.setObjectName("DestructiveButton")
        self.btn_clear.clicked.connect(self.clear_buffer)
        commit_layout.addWidget(self.btn_clear)
        
        staging_layout.addLayout(commit_layout)
        layout.addWidget(staging_group)
        
    def refresh_staging(self):
        try:
            # Query valid and error records
            valid_rows = get_staging_by_status("Valid")
            error_rows = get_staging_by_status("Error")
            all_rows = valid_rows + error_rows
            
            self.lbl_summary.setText(f"Staging Buffer: {len(valid_rows)} Valid records ready, {len(error_rows)} Error records need attention.")
            self.table_staging.setRowCount(0)
            
            for row_idx, r in enumerate(all_rows):
                self.table_staging.insertRow(row_idx)
                
                self.table_staging.setItem(row_idx, 0, QTableWidgetItem(str(r["id"])))
                self.table_staging.setItem(row_idx, 1, QTableWidgetItem(r["source_file_name"]))
                
                # Format raw JSON data
                raw_data = json.loads(r["raw_data"])
                formatted_data = ", ".join(f"{k}: {v}" for k, v in raw_data.items() if v)
                self.table_staging.setItem(row_idx, 2, QTableWidgetItem(formatted_data))
                
                # Format error messages
                status_item = QTableWidgetItem()
                if r["validation_status"] == "Error":
                    err_dict = json.loads(r["validation_errors"]) if r["validation_errors"] else {}
                    err_msg = "; ".join(f"{k}: {v}" for k, v in err_dict.items())
                    status_item.setText(err_msg)
                    status_item.setForeground(Qt.red)
                else:
                    status_item.setText("Ready to Commit")
                    status_item.setForeground(Qt.darkGreen)
                self.table_staging.setItem(row_idx, 3, status_item)
                
        except Exception as e:
            logging.error(f"Failed to refresh staging tables: {e}")
            
    def upload_file(self):
        file_path, _ = QFileDialog.getOpenFileName(
            self, "Select Tabular File to Import", "",
            "Tabular Files (*.csv *.xlsx *.txt);;CSV Files (*.csv);;Excel Files (*.xlsx);;Text Files (*.txt)"
        )
        if not file_path:
            return
            
        import_type = self.combo_type.currentText()
        file_name = os.path.basename(file_path)
        
        try:
            if file_path.endswith(".csv"):
                records = parse_csv_file(file_path)
            elif file_path.endswith(".xlsx"):
                records = parse_xlsx_file(file_path)
            else:
                records = parse_txt_file(file_path)
                
            if not records:
                QMessageBox.warning(self, "Empty File", "No records could be parsed from the file.")
                return
                
            staged = stage_and_validate_records(import_type, records, file_name)
            QMessageBox.information(self, "Staged", f"Successfully staged {staged} records. Review validation errors below.")
            self.refresh_staging()
        except Exception as e:
            QMessageBox.critical(self, "Import Failed", f"Failed to parse or stage file: {e}")
            
    def upload_ocr(self):
        file_path, _ = QFileDialog.getOpenFileName(
            self, "Select Scanned Document / Receipt Image", "",
            "Images (*.png *.jpg *.jpeg *.bmp);;All Files (*)"
        )
        if not file_path:
            return
            
        import_type = self.combo_type.currentText()
        file_name = os.path.basename(file_path)
        
        # Show busy waiting state
        QMessageBox.information(self, "OCR Starting", "The offline OCR engine is starting to scan the image. Please click OK and wait a moment.")
        
        try:
            raw_text = run_offline_ocr(file_path)
            entities = extract_entities_from_text(raw_text)
            
            # Stage single record
            stage_and_validate_records(import_type, [entities], file_name)
            QMessageBox.information(self, "Scanned", "Image scanned successfully! The extracted data is loaded into staging.")
            self.refresh_staging()
        except Exception as e:
            QMessageBox.critical(self, "OCR Failed", str(e))
            
    def commit_records(self):
        import_type = self.combo_type.currentText()
        
        success, failed = approve_and_commit_staging(import_type)
        if success > 0 or failed > 0:
            QMessageBox.information(self, "Commit Result", f"Successfully committed {success} records.\nFailed to commit {failed} records.")
            self.refresh_staging()
            self.window().refresh_all_tabs()
        else:
            QMessageBox.warning(self, "No Records", "No valid staging records were found to commit.")
            
    def clear_buffer(self):
        reply = QMessageBox.question(
            self, "Clear Staging",
            "Are you sure you want to delete all staging records?",
            QMessageBox.Yes | QMessageBox.No
        )
        if reply == QMessageBox.Yes:
            clear_staging_imports()
            self.refresh_staging()
