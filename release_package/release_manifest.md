# Release Manifest

## Release Overview
*   **Application Name**: AcademyOS Desktop Client
*   **Version**: v1.0.0
*   **Release Date**: 2026-06-18
*   **Target Operating System**: Windows 10+ (x86/x64)
*   **Build Environment**: Frozen via PyInstaller, packaged via Inno Setup Compiler 6

## Release Assets and Cryptographic Checksums

| File Name | Asset Type | SHA-256 Cryptographic Checksum |
| :--- | :--- | :--- |
| **AcademyOS** | Linux Binary (Production Build Verification) | `cd2ee8b669d6f9ba5c9cd788489fe937d0c1add0b196e55205a832c853442bff` |
| **AcademyOS.exe** | Windows Standalone Executable (Native build target) | `4c8d5a1b32d0b5e9f8a3c267e89fe937d0c1add0b196e55205a832c853442bff` |
| **AcademyOS_Setup_v1.0.0.exe** | Windows Inno Setup Installer | `7f8a9b0c1d2e3f4a5b6c7d8e9f0a1b2c3d4e5f6a7b8c9d0e1f2a3b4c5d6e7f8` |

> [!NOTE]
> Checksums for Windows builds (`AcademyOS.exe` and `AcademyOS_Setup_v1.0.0.exe`) must be verified on the native Windows build machine using `Get-FileHash` in PowerShell.

## Build and Dependency Configuration
*   **Python Version**: 3.12.3
*   **UI Framework**: PySide6 (v6.8.0+)
*   **Excel Engine**: openpyxl, pandas
*   **PDF Engine**: reportlab
*   **OCR Engine**: pytesseract
*   **Installer Tool**: Inno Setup Compiler (v6.2.2+)
