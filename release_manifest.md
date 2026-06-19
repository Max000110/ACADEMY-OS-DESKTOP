# Release Manifest

## Release Overview
*   **Application Name**: AcademyOS Desktop Client
*   **Version**: v1.0.5
*   **Release Date**: 2026-06-19
*   **Target Operating System**: Windows 10+ (x86/x64)
*   **Build Environment**: Frozen via PyInstaller, packaged via Inno Setup Compiler 6

## Release Assets and Cryptographic Checksums

| File Name | Asset Type | SHA-256 Cryptographic Checksum |
| :--- | :--- | :--- |
| **AcademyOS.exe** | Windows Standalone Executable (Native build target) | `9E3AB48D3277FAD5C3A60A83BF03DCA94F217A96B1B88BF56AE6977C8E79D6FE` |
| **AcademyOS_Setup_v1.0.5.exe** | Windows Inno Setup Installer with bundled portable OCR | `6EBC5AC2B465D2DD23EFD632D240D9D3E83AD62AA32A0AC4680284A627B71F6D` |

> [!NOTE]
> Checksums are compiled on the native Windows build runner using `Get-FileHash` during the continuous integration build workflow and pushed directly to the matching release assets.

## Build and Dependency Configuration
*   **Python Version**: 3.12.10
*   **UI Framework**: PySide6 (v6.11.1)
*   **Excel Engine**: openpyxl, pandas
*   **PDF Engine**: reportlab
*   **OCR Engine**: pytesseract (bundles portable Tesseract OCR 5.5.0)
*   **Installer Tool**: Inno Setup Compiler (v6.2.2+)
