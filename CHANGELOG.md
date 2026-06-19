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

## [1.0.1] - 2026-06-18

### Fixed
- **UI Window console**: Removed debug console window popping up on startup on Windows system (`console=False` in build spec).
- **PDF Generation**: Fixed Student ID mapping bug in receipt invoice PDF rendering module.
- **XLSX Import**: Fixed runtime `NameError` on `datetime` module during Excel staging imports.

## [1.0.2] - 2026-06-18

### Added
- **Portable OCR Installer Configuration**: Configured `build_installer.iss` to target dynamic user profiles (`{%USERPROFILE}\.academyos`) and bundle portable Tesseract OCR binary directory.
- **Safeguard Database Preservation**: Commented out settings template and database files in the uninstall file targets to prevent accidental wiping of customer records.

## [1.0.3] - 2026-06-19

### Added
- **Licensing Server Architecture**: FastAPI licensing API server and management dashboard (v1.1.0) with support for online/offline activation, heartbeats, and device concurrency bindings.
- **Security Hardening**: Implemented brute force IP protection, JWT slide session rotation, XSS/CSP middleware filters, and anti-CSRF protections on settings and dashboard routers.
- **GHA Build Automation**: Continuous integration pipeline in GitHub Actions compiling Windows executables and setup installers, bundling OCR assets, generating checksums, and pushing releases.
- **Deprecated WMIC compatibility**: Patched `get_device_fingerprint()` to execute PowerShell fallbacks on modern Windows kernels (like Windows Server 2025 or Windows 11) where `wmic` has been removed.
