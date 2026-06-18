# AcademyOS UI Styles & Design System (PySide6 QSS)

THEME_COLOR_PRIMARY = "#1F497D"    # Deep Navy
THEME_COLOR_SECONDARY = "#3182CE"  # Slate Blue
THEME_COLOR_BACKGROUND = "#F8FAFC" # Light Slate
THEME_COLOR_CARD = "#FFFFFF"       # Muted Card White
THEME_COLOR_TEXT = "#1E293B"       # Dark Slate Text
THEME_COLOR_MUTED = "#64748B"      # Cool Gray Muted Text
THEME_COLOR_BORDER = "#E2E8F0"     # Thin Border Gray
THEME_COLOR_SUCCESS = "#10B981"    # Green Success Accent
THEME_COLOR_WARNING = "#F59E0B"    # Amber Warning Accent
THEME_COLOR_ERROR = "#EF4444"      # Red Error Accent

GLOBAL_STYLE_SHEET = """
QMainWindow {
    background-color: #F1F5F9;
}

QWidget {
    font-family: 'Segoe UI', Arial, sans-serif;
    font-size: 13px;
    color: #1E293B;
}

/* Sidebar Navigation Styling */
QListWidget#SidebarList {
    background-color: #1E293B;
    border: none;
    outline: none;
}

QListWidget#SidebarList::item {
    padding: 14px 18px;
    color: #94A3B8;
    font-weight: bold;
    border-left: 4px solid transparent;
}

QListWidget#SidebarList::item:hover {
    background-color: #334155;
    color: #F1F5F9;
}

QListWidget#SidebarList::item:selected {
    background-color: #0F172A;
    color: #FFFFFF;
    border-left: 4px solid #3182CE;
}

/* Tab Containers */
QTabWidget::pane {
    border: 1px solid #E2E8F0;
    background-color: #FFFFFF;
    border-radius: 6px;
    top: -1px;
}

/* Dashboard Summary Cards */
QFrame#MetricCard {
    background-color: #FFFFFF;
    border: 1px solid #E2E8F0;
    border-radius: 8px;
    padding: 16px;
}

QLabel#MetricValue {
    font-size: 24px;
    font-weight: bold;
    color: #1F497D;
}

QLabel#MetricTitle {
    font-size: 12px;
    color: #64748B;
    text-transform: uppercase;
    font-weight: bold;
}

/* Buttons */
QPushButton {
    background-color: #1F497D;
    color: #FFFFFF;
    border: none;
    border-radius: 4px;
    padding: 8px 16px;
    font-weight: bold;
}

QPushButton:hover {
    background-color: #1A3E68;
}

QPushButton:pressed {
    background-color: #122C4B;
}

QPushButton:disabled {
    background-color: #CBD5E1;
    color: #64748B;
}

QPushButton#SecondaryButton {
    background-color: #FFFFFF;
    color: #1F497D;
    border: 1px solid #1F497D;
}

QPushButton#SecondaryButton:hover {
    background-color: #F1F5F9;
}

QPushButton#DestructiveButton {
    background-color: #EF4444;
}

QPushButton#DestructiveButton:hover {
    background-color: #DC2626;
}

/* Inputs and Forms */
QLineEdit, QComboBox, QTextEdit, QDateEdit {
    background-color: #FFFFFF;
    border: 1px solid #CBD5E1;
    border-radius: 4px;
    padding: 6px 10px;
    selection-background-color: #3182CE;
}

QLineEdit:focus, QComboBox:focus, QTextEdit:focus, QDateEdit:focus {
    border: 1px solid #3182CE;
    background-color: #F8FAFC;
}

/* Table Views */
QTableWidget {
    background-color: #FFFFFF;
    border: 1px solid #E2E8F0;
    gridline-color: #F1F5F9;
    border-radius: 6px;
}

QHeaderView::section {
    background-color: #F8FAFC;
    color: #475569;
    font-weight: bold;
    border: none;
    border-bottom: 2px solid #E2E8F0;
    padding: 8px;
}

QTableWidget::item {
    padding: 6px;
    border-bottom: 1px solid #F1F5F9;
}

QTableWidget::item:selected {
    background-color: #E2E8F0;
    color: #000000;
}

/* ScrollBars */
QScrollBar:vertical {
    border: none;
    background: #F1F5F9;
    width: 10px;
    margin: 0px;
}

QScrollBar::handle:vertical {
    background: #CBD5E1;
    border-radius: 5px;
    min-height: 20px;
}

QScrollBar::handle:vertical:hover {
    background: #94A3B8;
}

/* Group Boxes */
QGroupBox {
    font-weight: bold;
    border: 1px solid #E2E8F0;
    border-radius: 6px;
    margin-top: 12px;
    padding-top: 16px;
}

QGroupBox::title {
    subcontrol-origin: margin;
    subcontrol-position: top left;
    left: 10px;
    padding: 0px 5px;
}
"""
