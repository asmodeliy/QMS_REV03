import os
from pathlib import Path
from dotenv import load_dotenv

load_dotenv()

BASE_DIR = Path(__file__).resolve().parent.parent
DB_PATH = (BASE_DIR / "rpmt.db").resolve()
PRODUCT_INFO_DB_PATH = (BASE_DIR / "product_info.db").resolve()

APP_ENV = os.environ.get("APP_ENV", "development")
SESSION_SECRET = os.environ.get("SESSION_SECRET", "rps-secret")
ADMIN_USER = os.environ.get("ADMIN_USER", "admin")
ADMIN_PASS = os.environ.get("ADMIN_PASS", "ramschip")

# CORS and session security
_cors_raw = os.environ.get("CORS_ORIGINS", "http://210.117.32.72:58080").strip()
CORS_ORIGINS = [o.strip() for o in _cors_raw.split(",") if o.strip()] if _cors_raw else []
SESSION_HTTPS_ONLY = os.environ.get("SESSION_HTTPS_ONLY", "").lower() in ("1", "true", "yes")
ENABLE_TEST_ENDPOINTS = os.environ.get("ENABLE_TEST_ENDPOINTS", "").lower() in ("1", "true", "yes")
ACTIVITY_LOG_RETENTION_DAYS = int(os.environ.get("ACTIVITY_LOG_RETENTION_DAYS", "30"))

OUTLOOK_EMAIL = os.environ.get("OUTLOOK_EMAIL", "")
OUTLOOK_PASSWORD = os.environ.get("OUTLOOK_PASSWORD", "")
ADMIN_NOTIFICATION_EMAIL = os.environ.get("ADMIN_EMAIL", "admin@ramschip.com")

GARAGE_MAX_UPLOAD_SIZE = int(os.environ.get('GARAGE_MAX_UPLOAD_SIZE', 10 * 1024 * 1024 * 1024))
_allowed = os.environ.get('GARAGE_ALLOWED_EXTENSIONS', '')
GARAGE_ALLOWED_EXTENSIONS = [ext.strip().lower() for ext in _allowed.split(',') if ext.strip()] if _allowed else []
GARAGE_ADMIN_EMAILS = [e.strip().lower() for e in os.environ.get('GARAGE_ADMIN_EMAILS', 'swlee@ramschip.com').split(',') if e.strip()]

SVIT_MAX_ATTACH_SIZE = int(os.environ.get('SVIT_MAX_ATTACH_SIZE', 50 * 1024 * 1024))  # 50MB default
_sv_allowed = os.environ.get('SVIT_ALLOWED_ATTACHMENTS', 'png,jpg,jpeg,gif,webp,pdf,mp4,mov')
SVIT_ALLOWED_ATTACHMENTS = [ext.strip().lower() for ext in _sv_allowed.split(',') if ext.strip()]

# -------------------------
# LLM configuration helpers
# -------------------------
LLM_BACKEND = os.environ.get('LLM_BACKEND', 'gpt4all')
LLM_MODEL_PATH = os.environ.get('LLM_MODEL_PATH', '')
# Prefer a larger default context for modern models (Llama-3 supports up to 8192)
LLM_N_CTX = int(os.environ.get('LLM_N_CTX', '4096'))

# Optional dedicated LLM folder (can be overridden by env LLM_DIR)
LLM_DIR = Path(os.environ.get('LLM_DIR', r'C:\Users\이상원\Downloads\Models')).resolve()

# If no explicit model path is configured, try to find a .gguf model in a few
# sensible locations inside the project and LLM_DIR (common build outputs).
if not LLM_MODEL_PATH:
    candidate_dirs = [
        LLM_DIR / 'models',
        LLM_DIR / 'gpt4all-rocky8' / 'build',
    ]
    found = None
    for d in candidate_dirs:
        try:
            if d.exists():
                # first .gguf file we find
                for p in d.rglob('*.gguf'):
                    found = p
                    break
        except Exception:
            continue
        if found:
            LLM_MODEL_PATH = str(found)
            break

# If the model filename hints at gpt4all and user didn't set backend explicitly,
# set a reasonable default to 'gpt4all'. This is a heuristic only.
try:
    if LLM_MODEL_PATH and 'gpt4all' in os.path.basename(LLM_MODEL_PATH).lower():
        # Respect explicit env setting; override only if backend was left as default
        if os.environ.get('LLM_BACKEND') is None:
            LLM_BACKEND = 'gpt4all'
except Exception:
    pass

# Convenience flag for quick checks
try:
    from pathlib import Path as _Path
    LLM_AVAILABLE = bool(LLM_MODEL_PATH and _Path(LLM_MODEL_PATH).exists())
except Exception:
    LLM_AVAILABLE = False

# Expose a helpful string for logs
LLM_INFO = {
    'backend': LLM_BACKEND,
    'model_path': LLM_MODEL_PATH,
    'n_ctx': LLM_N_CTX,
    'available': LLM_AVAILABLE,
}