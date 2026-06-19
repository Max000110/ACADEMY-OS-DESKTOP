import re
import os
import logging
from PIL import Image, ImageEnhance, ImageFilter

# Define PyTesseract helper
try:
    import pytesseract
except ImportError:
    pytesseract = None

class OCREngineError(Exception):
    pass

def process_image_for_ocr(image_path: str) -> Image.Image:
    """Preprocess image to enhance OCR text extraction accuracy."""
    try:
        img = Image.open(image_path)
        # Convert to grayscale
        img = img.convert('L')
        # Scale up slightly to improve reading of small text
        w, h = img.size
        img = img.resize((w * 2, h * 2), Image.Resampling.LANCZOS)
        # Increase contrast
        enhancer = ImageEnhance.Contrast(img)
        img = enhancer.enhance(2.0)
        # Apply slight thresholding binarization
        img = img.point(lambda x: 0 if x < 128 else 255, '1')
        return img
    except Exception as e:
        logging.error(f"Image preprocessing failed: {e}")
        raise OCREngineError(f"Failed to process image: {e}")

def run_offline_ocr(image_path: str) -> str:
    """Run Tesseract OCR on a local image path. Fails gracefully if Tesseract is missing."""
    if not pytesseract:
        raise OCREngineError("pytesseract library is not installed in Python environment.")
        
    try:
        processed_img = process_image_for_ocr(image_path)
        
        # Check if tesseract binary path is set, or if it can be called directly
        # In a real Windows environment, users can install Tesseract to Program Files
        # We check common installation paths on Windows as fallbacks
        if os.name == 'nt':
            # Check portable installation path relative to frozen executable first
            import sys
            app_dir = os.path.dirname(sys.executable)
            portable_path = os.path.join(app_dir, "tesseract", "tesseract.exe")
            portable_tessdata = os.path.join(app_dir, "tesseract", "tessdata")
            
            common_paths = []
            if os.path.exists(portable_path):
                common_paths.append(portable_path)
                # Configure tessdata prefix if using portable bundler (must point to parent of 'tessdata' folder)
                if os.path.exists(portable_tessdata):
                    os.environ["TESSDATA_PREFIX"] = os.path.join(app_dir, "tesseract")
            
            common_paths.extend([
                r"C:\Program Files\Tesseract-OCR\tesseract.exe",
                r"C:\Program Files (x86)\Tesseract-OCR\tesseract.exe"
            ])
            for path in common_paths:
                if os.path.exists(path):
                    pytesseract.pytesseract.tesseract_cmd = path
                    break
                    
        # Extract string
        text = pytesseract.image_to_string(processed_img)
        logging.info("Offline OCR finished successfully.")
        return text
    except FileNotFoundError:
        logging.warning("Tesseract OCR executable not found on the host system path.")
        raise OCREngineError("Tesseract OCR system software is not installed. Please install Tesseract on your system to process images.")
    except Exception as e:
        logging.error(f"OCR execution failure: {e}")
        raise OCREngineError(f"OCR processing failed: {e}")

def extract_entities_from_text(raw_text: str) -> dict:
    """
    Parse OCR raw text output using regex patterns.
    Extracts student fields, receipt numbers, and fee values.
    """
    extracted = {
        "first_name": "",
        "last_name": "",
        "phone": "",
        "email": "",
        "course": "",
        "amount": "",
        "receipt": ""
    }
    
    lines = [line.strip() for line in raw_text.split("\n") if line.strip()]
    
    # 1. Search for phone numbers (10 digits)
    phone_match = re.search(r'\b(?:\+?\d{1,3}[- ]?)?(\d{10})\b', raw_text)
    if phone_match:
        extracted["phone"] = phone_match.group(1)
        
    # 2. Search for emails
    email_match = re.search(r'[\w\.-]+@[\w\.-]+\.\w+', raw_text)
    if email_match:
        extracted["email"] = email_match.group(0)
        
    # 3. Simple Name Parser (e.g. "Name: First Last" or "Student: First Last")
    for line in lines:
        lower_line = line.lower()
        if "name:" in lower_line or "student:" in lower_line or "student name:" in lower_line:
            # Strip key and separate
            clean_line = re.sub(r'^(student|name|student name)\s*:\s*', '', line, flags=re.IGNORECASE)
            parts = clean_line.strip().split()
            if len(parts) >= 2:
                extracted["first_name"] = parts[0]
                extracted["last_name"] = " ".join(parts[1:])
            elif len(parts) == 1:
                extracted["first_name"] = parts[0]
            break
            
    # 4. Extract Receipt Details
    for line in lines:
        lower_line = line.lower()
        if "receipt:" in lower_line or "receipt no:" in lower_line or "receipt number:" in lower_line or "rec no:" in lower_line:
            clean_line = re.sub(r'^(receipt|receipt no|receipt number|rec no)\s*:\s*', '', line, flags=re.IGNORECASE)
            extracted["receipt"] = clean_line.strip()
            break
            
    # 5. Extract amount paid/fees
    amount_match = re.search(r'(?:fee|amount|paid|total|collection)\s*[:$]?\s*(\d+(?:\.\d{2})?)', raw_text, re.IGNORECASE)
    if amount_match:
        extracted["amount"] = amount_match.group(1)
        
    return extracted
