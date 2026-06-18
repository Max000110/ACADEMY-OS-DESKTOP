import os
import sys
import uuid
import json
import hashlib
import subprocess
import datetime
import logging
from src.utils.config import APP_DIR
from src.utils.crypto import verify_license_payload, generate_signature

LICENSE_PATH = os.path.join(APP_DIR, "license.json")

def get_device_fingerprint() -> str:
    """
    Retrieve unique hardware descriptors (Motherboard, CPU, MAC) and hash them 
    into a unique 64-character device fingerprint.
    """
    identifiers = []
    
    # 1. Platform specific system UUIDs
    try:
        if sys.platform.startswith("win"):
            # Motherboard UUID via WMIC (without shell=True for command injection safety)
            raw_uuid = subprocess.check_output(["wmic", "bios", "get", "uuid"], shell=False).decode('utf-8')
            identifiers.append(raw_uuid.strip().split("\n")[-1].strip())
            
            # Motherboard Serial
            raw_board = subprocess.check_output(["wmic", "baseboard", "get", "serialnumber"], shell=False).decode('utf-8')
            identifiers.append(raw_board.strip().split("\n")[-1].strip())
        elif sys.platform.startswith("linux"):
            # Machine ID or Motherboard serial
            for path in ["/etc/machine-id", "/var/lib/dbus/machine-id", "/sys/class/dmi/id/product_uuid", "/sys/class/dmi/id/board_serial"]:
                if os.path.exists(path):
                    with open(path, "r") as f:
                        identifiers.append(f.read().strip())
                    break
    except Exception as e:
        logging.warning(f"Failed to fetch system UUID: {e}")
        
    # 2. Network Interface MAC Address as reliable fallback/addition
    try:
        mac = ':'.join(['{:02x}'.format((uuid.getnode() >> ele) & 0xff)
                        for ele in range(0, 8*6, 8)][::-1])
        identifiers.append(mac)
    except Exception as e:
        logging.warning(f"Failed to fetch MAC address: {e}")
        
    # 3. CPU details
    try:
        identifiers.append(sys.implementation.name)
        identifiers.append(os.cpu_count() or 1)
    except Exception:
        pass
        
    # Hash combined list
    raw_str = "|".join(str(i) for i in identifiers)
    return hashlib.sha256(raw_str.encode('utf-8')).hexdigest()

def check_clock_tampering() -> bool:
    """Check if system clock has been rolled back compared to settings.json."""
    try:
        from src.utils.config import load_settings, save_settings
        settings = load_settings()
        last_run_str = settings.get("last_run_date", "")
        today_str = datetime.date.today().strftime("%Y-%m-%d")
        
        if last_run_str:
            try:
                last_run = datetime.datetime.strptime(last_run_str, "%Y-%m-%d").date()
                if datetime.date.today() < last_run:
                    logging.error(f"Clock rollback detected! System date: {today_str}, Last run: {last_run_str}")
                    return True
            except ValueError:
                pass
                
        # Update last_run_date
        settings["last_run_date"] = today_str
        save_settings(settings)
        return False
    except Exception as e:
        logging.error(f"Clock tampering check failed: {e}")
        return False

def check_license_status() -> dict:
    """
    Check the current activation status.
    Returns a dict with keys:
        - "activated": bool
        - "expiry_date": str or None
        - "days_remaining": int
        - "error": str or None
    """
    if check_clock_tampering():
        return {"activated": False, "expiry_date": None, "days_remaining": 0, "error": "Clock Tampering"}

    if not os.path.exists(LICENSE_PATH):
        return {"activated": False, "expiry_date": None, "days_remaining": 0, "error": "Not Activated"}
        
    try:
        with open(LICENSE_PATH, 'r', encoding='utf-8') as f:
            data = json.load(f)
            
        license_key = data.get("license_key", "")
        expiry_str = data.get("expiry_date", "")
        fingerprint = data.get("fingerprint", "")
        signature = data.get("signature", "")
        
        # Verify cryptographic signature
        if not verify_license_payload(license_key, expiry_str, fingerprint, signature):
            return {"activated": False, "expiry_date": None, "days_remaining": 0, "error": "License Tampered"}
            
        # Verify hardware match
        current_fingerprint = get_device_fingerprint()
        if fingerprint != current_fingerprint:
            return {"activated": False, "expiry_date": None, "days_remaining": 0, "error": "Hardware Mismatch"}
            
        # Check expiry
        expiry_date = datetime.datetime.strptime(expiry_str, "%Y-%m-%d").date()
        today = datetime.date.today()
        
        if today > expiry_date:
            return {"activated": False, "expiry_date": expiry_str, "days_remaining": 0, "error": "Expired"}
            
        days_remaining = (expiry_date - today).days
        return {
            "activated": True,
            "expiry_date": expiry_str,
            "days_remaining": days_remaining,
            "error": None
        }
    except Exception as e:
        logging.error(f"License check failed: {e}")
        return {"activated": False, "expiry_date": None, "days_remaining": 0, "error": "Internal Error"}

def activate_license(activation_key: str) -> bool:
    """
    Activate the application offline using a signed activation key.
    A valid key format is: AOS-KEY-<YYYY-MM-DD>-<SIGNATURE>
    where <SIGNATURE> is the HMAC hash of "AOS-KEY-<YYYY-MM-DD>" and current device fingerprint.
    """
    try:
        parts = activation_key.strip().split("-")
        if len(parts) != 6 or parts[0] != "AOS" or parts[1] != "KEY":
            logging.error(f"Invalid activation key format: {activation_key}")
            return False
            
        # Extract components
        expiry_str = f"{parts[2]}-{parts[3]}-{parts[4]}"  # YYYY-MM-DD
        signature = parts[5]   # HMAC signature
        
        # Check if date is in future
        try:
            expiry_date = datetime.datetime.strptime(expiry_str, "%Y-%m-%d").date()
            if expiry_date < datetime.date.today():
                logging.error("Activation key is already expired.")
                return False
        except ValueError:
            logging.error(f"Invalid expiry date in key: {expiry_str}")
            return False
            
        # Verify activation signature
        fingerprint = get_device_fingerprint()
        license_base = f"AOS-KEY-{expiry_str}"
        
        if not verify_license_payload(license_base, expiry_str, fingerprint, signature):
            logging.error("Licensing signature mismatch.")
            return False
            
        # Write active license file to user app directory
        license_data = {
            "license_key": license_base,
            "expiry_date": expiry_str,
            "fingerprint": fingerprint,
            "signature": generate_signature(license_base, expiry_str, fingerprint)
        }
        
        os.makedirs(APP_DIR, exist_ok=True)
        with open(LICENSE_PATH, 'w', encoding='utf-8') as f:
            json.dump(license_data, f, indent=4)
            
        logging.info(f"License activated successfully until {expiry_str}")
        return True
    except Exception as e:
        logging.error(f"Failed to activate license: {e}")
        return False

def check_hardware_compatibility() -> tuple:
    """
    Verify host hardware resources.
    Returns (compatible: bool, details: str, warnings: list)
    """
    import platform
    warnings = []
    
    # 1. OS check
    is_windows = sys.platform.startswith("win")
    # Log system name
    system_name = platform.system()
    
    # 2. Check RAM
    try:
        # psutil would be nice, but fallback to free/system calls to avoid extra dependency
        if sys.platform.startswith("win"):
            # WMIC computer system get totalphysicalmemory (without shell=True)
            raw_mem = subprocess.check_output(["wmic", "computersystem", "get", "totalphysicalmemory"], shell=False).decode('utf-8')
            mem_bytes = int(raw_mem.strip().split("\n")[-1].strip())
            total_ram_gb = mem_bytes / (1024 ** 3)
        elif sys.platform.startswith("linux"):
            with open("/proc/meminfo", "r") as f:
                for line in f:
                    if "MemTotal" in line:
                        mem_kb = int(line.split()[1])
                        total_ram_gb = mem_kb / (1024 * 1024)
                        break
        else:
            total_ram_gb = 4.0  # Default assumption if unable to query
    except Exception:
        total_ram_gb = 4.0  # Fallback
        
    details = f"OS: {system_name}, RAM: {total_ram_gb:.1f} GB, CPU Cores: {os.cpu_count() or 1}"
    
    if total_ram_gb < 3.5:
        warnings.append("System RAM is below recommended 4GB. Performance may be degraded.")
        
    return True, details, warnings
