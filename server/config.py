import os
from dotenv import load_dotenv

# Load env variables from .env file
load_dotenv()

DATABASE_URL = os.environ.get("DATABASE_URL", "sqlite:///./academyos_licensing.db")
AOS_SIGNING_SALT = os.environ.get("AOS_SIGNING_SALT", "dev_fallback_salt_do_not_use_in_production")
JWT_SECRET_KEY = os.environ.get("JWT_SECRET_KEY", "dev_jwt_secret_key_change_me_in_production")
ACCESS_TOKEN_EXPIRE_MINUTES = int(os.environ.get("ACCESS_TOKEN_EXPIRE_MINUTES", "60"))
