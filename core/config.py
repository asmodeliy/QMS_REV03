import os 
from pathlib import Path 
from dotenv import load_dotenv 

load_dotenv ()

BASE_DIR =Path (__file__ ).resolve ().parent .parent 
DB_PATH =(BASE_DIR /"rpmt.db").resolve ()
PRODUCT_INFO_DB_PATH = (BASE_DIR / "product_info.db").resolve()

SESSION_SECRET =os .environ .get ("SESSION_SECRET","rps-secret")
ADMIN_USER =os .environ .get ("ADMIN_USER","admin")
ADMIN_PASS =os .environ .get ("ADMIN_PASS","ramschip")

OUTLOOK_EMAIL =os .environ .get ("OUTLOOK_EMAIL","")
OUTLOOK_PASSWORD =os .environ .get ("OUTLOOK_PASSWORD","")
ADMIN_NOTIFICATION_EMAIL =os .environ .get ("ADMIN_EMAIL","admin@ramschip.com")

GARAGE_MAX_UPLOAD_SIZE = int(os.environ.get('GARAGE_MAX_UPLOAD_SIZE', 2 * 1024 * 1024 * 1024))
_allowed = os.environ.get('GARAGE_ALLOWED_EXTENSIONS', '')
GARAGE_ALLOWED_EXTENSIONS = [ext.strip().lower() for ext in _allowed.split(',') if ext.strip()] if _allowed else []
GARAGE_ADMIN_EMAILS = [e.strip().lower() for e in os.environ.get('GARAGE_ADMIN_EMAILS', 'swlee@ramschip.com').split(',') if e.strip()]
