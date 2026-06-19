import csv
import logging
from datetime import datetime

class ImportParseError(Exception):
    pass

def map_column_headers(headers: list) -> dict:
    """
    Map raw sheet column headers to standardized internal key names.
    Supports variations in capitalization, spaces, and abbreviations.
    """
    mapping = {}
    standard_keys = {
        "first_name": ["first name", "firstname", "first", "fname"],
        "last_name": ["last name", "lastname", "last", "lname", "surname"],
        "phone": ["phone", "mobile", "contact", "phone number", "mob", "tel"],
        "email": ["email", "email address", "mail"],
        "dob": ["dob", "date of birth", "birthdate", "birth date"],
        "gender": ["gender", "sex"],
        "address": ["address", "residence", "location"],
        "source": ["source", "lead source", "enquiry source", "referred by"],
        "course": ["course", "course interested", "interested course", "subject"]
    }
    
    for header in headers:
        clean_header = str(header).strip().lower().replace("_", " ")
        matched = False
        for key, aliases in standard_keys.items():
            if clean_header in aliases or clean_header == key:
                mapping[header] = key
                matched = True
                break
        if not matched:
            mapping[header] = clean_header.replace(" ", "_") # Fallback key formatting
            
    return mapping

def parse_csv_file(file_path: str) -> list:
    """Parse a CSV tabular file and return list of matched records."""
    records = []
    try:
        with open(file_path, 'r', encoding='utf-8', errors='ignore') as f:
            reader = csv.reader(f)
            headers = next(reader, None)
            if not headers:
                raise ImportParseError("CSV file is empty.")
                
            header_map = map_column_headers(headers)
            
            for row in reader:
                if not any(row):  # Skip blank rows
                    continue
                record = {}
                for idx, cell in enumerate(row):
                    if idx < len(headers):
                        raw_header = headers[idx]
                        std_key = header_map[raw_header]
                        record[std_key] = cell.strip()
                records.append(record)
        return records
    except Exception as e:
        logging.error(f"Error parsing CSV file {file_path}: {e}")
        raise ImportParseError(f"Failed to parse CSV: {e}")

def parse_xlsx_file(file_path: str) -> list:
    """Parse an Excel (XLSX) worksheet using openpyxl and return list of records."""
    records = []
    try:
        import openpyxl
        wb = openpyxl.load_workbook(file_path, read_only=True, data_only=True)
        sheet = wb.active
        
        rows = list(sheet.rows)
        if not rows:
            raise ImportParseError("Excel sheet is empty.")
            
        headers = [cell.value for cell in rows[0] if cell.value is not None]
        if not headers:
            raise ImportParseError("Excel header row is blank.")
            
        header_map = map_column_headers(headers)
        
        for row_cells in rows[1:]:
            # Check if row is empty
            values = [cell.value for cell in row_cells]
            if not any(v is not None for v in values):
                continue
                
            record = {}
            for idx, cell in enumerate(row_cells):
                if idx < len(headers):
                    raw_header = headers[idx]
                    std_key = header_map[raw_header]
                    val = cell.value
                    if val is not None:
                        if isinstance(val, datetime):
                            record[std_key] = val.strftime("%Y-%m-%d")
                        else:
                            record[std_key] = str(val).strip()
                    else:
                        record[std_key] = ""
            records.append(record)
            
        wb.close()
        return records
    except Exception as e:
        logging.error(f"Error parsing Excel file {file_path}: {e}")
        raise ImportParseError(f"Failed to parse Excel: {e}")

def parse_txt_file(file_path: str) -> list:
    """Parse structured tabular TXT file (determines delimiter like tab/comma)."""
    try:
        with open(file_path, 'r', encoding='utf-8', errors='ignore') as f:
            sample = f.read(2048)
            f.seek(0)
            
        # Detect separator
        if '\t' in sample:
            delimiter = '\t'
        elif ',' in sample:
            delimiter = ','
        else:
            delimiter = '|'
            
        records = []
        with open(file_path, 'r', encoding='utf-8', errors='ignore') as f:
            reader = csv.reader(f, delimiter=delimiter)
            headers = next(reader, None)
            if not headers:
                raise ImportParseError("TXT file is empty.")
                
            header_map = map_column_headers(headers)
            
            for row in reader:
                if not any(row):
                    continue
                record = {}
                for idx, cell in enumerate(row):
                    if idx < len(headers):
                        raw_header = headers[idx]
                        std_key = header_map[raw_header]
                        record[std_key] = cell.strip()
                records.append(record)
        return records
    except Exception as e:
        logging.error(f"Error parsing text file {file_path}: {e}")
        raise ImportParseError(f"Failed to parse text: {e}")
