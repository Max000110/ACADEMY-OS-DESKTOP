# Release Manifest

## Release Overview
*   **Application Name**: AcademyOS Desktop Client
*   **Version**: v1.0.4
*   **Release Date**: 2026-06-19
*   **Target Operating System**: Windows 10+ (x86/x64)
*   **Build Environment**: Frozen via PyInstaller, packaged via Inno Setup Compiler 6

## Release Assets and Cryptographic Checksums

| File Name | Asset Type | SHA-256 Cryptographic Checksum |
| :--- | :--- | :--- |
| **AcademyOS.exe** | Windows Standalone Executable (Native build target) | `2E133D7EA1DB387663D399C453EFC880A28DC0F266397B326DBC235BC67A8832` |
| **AcademyOS_Setup_v1.0.4.exe** | Windows Inno Setup Installer with bundled portable OCR | `31344B16C44D1B8590FF64A2BD2E593EE93E4D0879802729BA21237A1678708F` |

> [!NOTE]
> Checksums are compiled on the native Windows build runner using `Get-FileHash` during the continuous integration build workflow and pushed directly to the matching release assets.

## Build and Dependency Configuration
*   **Python Version**: 3.12.10
*   **UI Framework**: PySide6 (v6.11.1)
*   **Excel Engine**: openpyxl, pandas
*   **PDF Engine**: reportlab
*   **OCR Engine**: pytesseract (bundles portable Tesseract OCR 5.5.0)
*   **Installer Tool**: Inno Setup Compiler (v6.2.2+)
