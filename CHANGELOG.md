# Changelog

All notable changes to **AcademyOS Desktop** will be documented in this file.

## [1.0.0] - 2026-06-18

### Added
- **Offline-First Client Architecture**: Full local management for computer classes, tuition centers, and academies using PySide6.
- **SQLite Storage Backend**: Zero-dependency transactional SQLite local database.
- **Lead / Enquiry Pipeline**: Dynamic lead logging, follow-up scheduling, and direct single-click student promotion.
- **Fees & Payment installment system**:Meters base course pricing, applies customer discounts, and calculates due balances dynamically.
- **Data Import Pipeline**: Staged validation layer for CSV, XLSX, and TXT bulk files with detailed error previewing before commit.
- **Excel Export Utility**: Custom styled workbooks using corporate palettes, auto column fitting, and conditional formatting.
- **PDF Receipt Invoice Generator**: Institutional invoice template output with transaction summary data.
- **Transactional Backup Engine**: Hot backup copier using native SQLite Backup API.
- **Cryptographic Activation License**: Offline client activation using SHA-256 system fingerprinting and HMAC-SHA256 license signatures.
- **License Administrator Panel**: Standalone manager tool `src/license_admin_app.py` to generate, renew, extend, search, and revoke activations.

### Hardened
- **SQL Injection Prevention**: Positional parameter binding `?` applied to all queries (including pagination limit strings).
- **Command Injection Prevention**: Hardened system calls by passing structured list arguments to subprocess executors and disabling `shell=True`.
- **Zip Slip Mitigation**: Added directory prefix boundary checks inside the extraction restore sequence to block path traversal exploits.
- **Spreadsheet Formula Injection Escape**: Prepend cell entries starting with `=`, `+`, `-`, or `@` with a single quote (`'`).
- **Clock Rollback Safeguard**: Checks system clock dates against configuration-logged execution datetimes to block clock-shifting trial bypasses.
- **Console Log Protection**: Fixed console logging levels to `logging.INFO` to prevent private key/debug leak logs.
