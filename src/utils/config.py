import os
import json
import logging

# Setup base directories in the user's home folder
APP_DIR = os.path.abspath(os.path.expanduser("~/.academyos"))
SETTINGS_PATH = os.path.join(APP_DIR, "settings.json")

DEFAULT_SETTINGS = {
    "database_path": os.path.join(APP_DIR, "academyos.db"),
    "backup_directory": os.path.join(APP_DIR, "backups"),
    "reports_directory": os.path.join(APP_DIR, "reports"),
    "theme": "light",
    "institution_name": "AcademyOS Training Center",
    "institution_phone": "",
    "institution_email": "",
    "institution_address": "",
    "backup_retention_count": 30,
    "backup_enabled": True
}

def init_app_directories():
    """Create initial application directories if they do not exist."""
    try:
        os.makedirs(APP_DIR, exist_ok=True)
        # Load settings to get custom directories if defined
        settings = load_settings()
        os.makedirs(os.path.dirname(settings["database_path"]), exist_ok=True)
        os.makedirs(settings["backup_directory"], exist_ok=True)
        os.makedirs(settings["reports_directory"], exist_ok=True)
    except Exception as e:
        print(f"Error creating directories: {e}")

def load_settings() -> dict:
    """Load settings from settings.json or create it with defaults if not present."""
    if not os.path.exists(SETTINGS_PATH):
        save_settings(DEFAULT_SETTINGS)
        return DEFAULT_SETTINGS.copy()
    
    try:
        with open(SETTINGS_PATH, 'r', encoding='utf-8') as f:
            data = json.load(f)
        
        # Merge missing defaults in case of outdated configuration file
        updated = False
        for k, v in DEFAULT_SETTINGS.items():
            if k not in data:
                data[k] = v
                updated = True
        
        if updated:
            save_settings(data)
            
        return data
    except Exception as e:
        logging.error(f"Failed to read settings from {SETTINGS_PATH}. Reverting to defaults. Error: {e}")
        return DEFAULT_SETTINGS.copy()

def save_settings(settings: dict) -> bool:
    """Save settings dict to settings.json."""
    try:
        os.makedirs(APP_DIR, exist_ok=True)
        with open(SETTINGS_PATH, 'w', encoding='utf-8') as f:
            json.dump(settings, f, indent=4, ensure_ascii=False)
        return True
    except Exception as e:
        logging.error(f"Failed to write settings to {SETTINGS_PATH}. Error: {e}")
        return False
