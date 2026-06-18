# SQL DDL Statements for AcademyOS SQLite Database Schema

CREATE_COURSES_TABLE = """
CREATE TABLE IF NOT EXISTS courses (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    name TEXT NOT NULL UNIQUE,
    code TEXT NOT NULL UNIQUE,
    description TEXT,
    duration_months INTEGER NOT NULL CHECK(duration_months > 0),
    total_fee REAL NOT NULL CHECK(total_fee >= 0),
    created_at TEXT DEFAULT (datetime('now', 'localtime')),
    updated_at TEXT DEFAULT (datetime('now', 'localtime'))
);
"""

CREATE_STUDENTS_TABLE = """
CREATE TABLE IF NOT EXISTS students (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    first_name TEXT NOT NULL,
    last_name TEXT NOT NULL,
    email TEXT,
    phone TEXT NOT NULL,
    dob TEXT NOT NULL, -- YYYY-MM-DD
    gender TEXT CHECK(gender IN ('Male', 'Female', 'Other')),
    address TEXT,
    admission_date TEXT NOT NULL DEFAULT (date('now', 'localtime')),
    status TEXT NOT NULL CHECK(status IN ('Active', 'Inactive', 'Suspended', 'Graduated')) DEFAULT 'Active',
    created_at TEXT DEFAULT (datetime('now', 'localtime')),
    updated_at TEXT DEFAULT (datetime('now', 'localtime'))
);
"""

CREATE_ENROLLMENTS_TABLE = """
CREATE TABLE IF NOT EXISTS enrollments (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    student_id INTEGER NOT NULL,
    course_id INTEGER NOT NULL,
    enrollment_date TEXT NOT NULL DEFAULT (date('now', 'localtime')),
    status TEXT NOT NULL CHECK(status IN ('Active', 'Completed', 'Dropped')) DEFAULT 'Active',
    discount REAL DEFAULT 0.0 CHECK(discount >= 0.0),
    net_fee REAL NOT NULL CHECK(net_fee >= 0.0),
    created_at TEXT DEFAULT (datetime('now', 'localtime')),
    updated_at TEXT DEFAULT (datetime('now', 'localtime')),
    FOREIGN KEY(student_id) REFERENCES students(id) ON DELETE CASCADE,
    FOREIGN KEY(course_id) REFERENCES courses(id) ON UPDATE CASCADE,
    UNIQUE(student_id, course_id)
);
"""

CREATE_FEE_PAYMENTS_TABLE = """
CREATE TABLE IF NOT EXISTS fee_payments (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    enrollment_id INTEGER NOT NULL,
    amount_paid REAL NOT NULL CHECK(amount_paid > 0),
    payment_date TEXT NOT NULL DEFAULT (date('now', 'localtime')),
    payment_method TEXT NOT NULL CHECK(payment_method IN ('Cash', 'Card', 'UPI', 'Bank Transfer')),
    receipt_number TEXT NOT NULL UNIQUE,
    remarks TEXT,
    created_at TEXT DEFAULT (datetime('now', 'localtime')),
    FOREIGN KEY(enrollment_id) REFERENCES enrollments(id) ON DELETE CASCADE
);
"""

CREATE_LEADS_TABLE = """
CREATE TABLE IF NOT EXISTS leads (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    first_name TEXT NOT NULL,
    last_name TEXT NOT NULL,
    phone TEXT NOT NULL,
    email TEXT,
    source TEXT NOT NULL, -- Website, Walk-in, Reference, Advertisement
    course_interested_id INTEGER,
    status TEXT NOT NULL CHECK(status IN ('New', 'Contacted', 'Interested', 'Enrolled', 'Lost')) DEFAULT 'New',
    follow_up_date TEXT, -- YYYY-MM-DD
    remarks TEXT,
    created_at TEXT DEFAULT (datetime('now', 'localtime')),
    updated_at TEXT DEFAULT (datetime('now', 'localtime')),
    FOREIGN KEY(course_interested_id) REFERENCES courses(id) ON UPDATE CASCADE
);
"""

CREATE_STAGING_IMPORTS_TABLE = """
CREATE TABLE IF NOT EXISTS staging_imports (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    import_type TEXT NOT NULL CHECK(import_type IN ('Students', 'Leads', 'Payments')),
    raw_data TEXT NOT NULL, -- JSON formatted raw columns extracted from file
    validation_status TEXT NOT NULL CHECK(validation_status IN ('Pending', 'Valid', 'Error')) DEFAULT 'Pending',
    validation_errors TEXT, -- JSON formatted list of field error messages
    source_file_name TEXT NOT NULL,
    created_at TEXT DEFAULT (datetime('now', 'localtime'))
);
"""

CREATE_SETTINGS_TABLE = """
CREATE TABLE IF NOT EXISTS settings (
    key TEXT PRIMARY KEY,
    value TEXT NOT NULL,
    updated_at TEXT DEFAULT (datetime('now', 'localtime'))
);
"""

CREATE_ACTIVATION_TABLE = """
CREATE TABLE IF NOT EXISTS activation (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    device_fingerprint TEXT NOT NULL UNIQUE,
    license_key TEXT NOT NULL,
    activated_at TEXT NOT NULL,
    expiry_date TEXT NOT NULL,
    status TEXT NOT NULL CHECK(status IN ('Active', 'Expired', 'Revoked')) DEFAULT 'Active'
);
"""

CREATE_AUDIT_LOGS_TABLE = """
CREATE TABLE IF NOT EXISTS audit_logs (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    user_action TEXT NOT NULL, -- e.g., 'ADD_STUDENT', 'DELETE_PAYMENT'
    details TEXT,             -- JSON string describing old/new values
    ip_address TEXT,          -- Local IP or hostname
    timestamp TEXT NOT NULL DEFAULT (datetime('now', 'localtime'))
);
"""

# Indexes for performance
INDEXES = [
    "CREATE INDEX IF NOT EXISTS idx_students_phone ON students(phone);",
    "CREATE INDEX IF NOT EXISTS idx_students_status ON students(status);",
    "CREATE INDEX IF NOT EXISTS idx_enrollments_student ON enrollments(student_id);",
    "CREATE INDEX IF NOT EXISTS idx_fee_payments_enrollment ON fee_payments(enrollment_id);",
    "CREATE INDEX IF NOT EXISTS idx_fee_payments_receipt ON fee_payments(receipt_number);",
    "CREATE INDEX IF NOT EXISTS idx_leads_phone ON leads(phone);",
    "CREATE INDEX IF NOT EXISTS idx_leads_status ON leads(status);",
    "CREATE INDEX IF NOT EXISTS idx_staging_imports_status ON staging_imports(validation_status);",
    "CREATE INDEX IF NOT EXISTS idx_audit_logs_action ON audit_logs(user_action);",
    "CREATE INDEX IF NOT EXISTS idx_audit_logs_time ON audit_logs(timestamp);"
]

SCHEMA_TABLES = [
    CREATE_COURSES_TABLE,
    CREATE_STUDENTS_TABLE,
    CREATE_ENROLLMENTS_TABLE,
    CREATE_FEE_PAYMENTS_TABLE,
    CREATE_LEADS_TABLE,
    CREATE_STAGING_IMPORTS_TABLE,
    CREATE_SETTINGS_TABLE,
    CREATE_ACTIVATION_TABLE,
    CREATE_AUDIT_LOGS_TABLE
]
