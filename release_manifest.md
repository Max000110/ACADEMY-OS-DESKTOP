# Release Manifest

## Release Overview
*   **Application Name**: AcademyOS Desktop Client
*   **Version**: v1.0.3
*   **Release Date**: 2026-06-19
*   **Target Operating System**: Windows 10+ (x86/x64)
*   **Build Environment**: Frozen via PyInstaller, packaged via Inno Setup Compiler 6

## Release Assets and Cryptographic Checksums

| File Name | Asset Type | SHA-256 Cryptographic Checksum |
| :--- | :--- | :--- |
| **AcademyOS.exe** | Windows Standalone Executable (Native build target) | `CE8C0E682B43F5685BA775956B89AC5A70F7E6E0A2F81C30B59D0E00BAE42DDF` |
| **AcademyOS_Setup_v1.0.3.exe** | Windows Inno Setup Installer with bundled portable OCR | `0007F306A9CFB8F525E9485A6E9FCB612A30A6321B3CEF4C8E3F3722B051747E` |

> [!NOTE]
> Checksums are compiled on the native Windows build runner using `Get-FileHash` during the continuous integration build workflow and pushed directly to the matching release assets.

## Build and Dependency Configuration
*   **Python Version**: 3.12.10
*   **UI Framework**: PySide6 (v6.11.1)
*   **Excel Engine**: openpyxl, pandas
*   **PDF Engine**: reportlab
*   **OCR Engine**: pytesseract (bundles portable Tesseract OCR 5.5.0)
*   **Installer Tool**: Inno Setup Compiler (v6.2.2+)
