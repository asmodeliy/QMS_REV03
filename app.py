from pathlib import Path
from fastapi import FastAPI, Request
from fastapi.responses import RedirectResponse, FileResponse
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates
from fastapi.exceptions import HTTPException
from starlette.middleware.sessions import SessionMiddleware
from fastapi.middleware.cors import CORSMiddleware
from starlette.middleware.gzip import GZipMiddleware

from services import compute_derived
from core.config import BASE_DIR, SESSION_SECRET
from core.middleware import RequestLoggingMiddleware
from core.i18n import t, get_locale
import re
import logging

app = FastAPI(title="RAMSCHIP QMS")

                                                                                   
try:
    from core.logger import app_logger
except Exception:
    class _FallbackAppLogger:
        def __init__(self, l):
            self._l = l
        def info(self, msg, data=None):
            self._l.info(f"{msg} {data}")
    app_logger = _FallbackAppLogger(logging.getLogger('app'))

app_logger.info("Application started", {"version": "1.0.0", "modules": ["rpmt", "svit", "cits", "spec_center", "apqp", "product_info"]})

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.add_middleware(RequestLoggingMiddleware)

app.add_middleware(
    SessionMiddleware,
    secret_key=SESSION_SECRET,
    session_cookie="rams_sess",
    max_age=30 * 60,
    same_site="lax",
    https_only=False
)

app.add_middleware(GZipMiddleware, minimum_size=1000)

templates = Jinja2Templates(directory=str(BASE_DIR / "templates"))
templates.env.globals["compute"] = compute_derived
templates.env.globals["img"] = lambda path: f"/img/{path}"

_current_locale = {"locale": "en"}

def t_with_current_locale(key, locale=None):
    if locale is None:
        locale = _current_locale.get("locale", "en")
    return t(key, locale)

templates.env.globals["t"] = t_with_current_locale

@app.middleware("http")
async def set_locale_middleware(request: Request, call_next):
    _current_locale["locale"] = get_locale(request)
    response = await call_next(request)
    return response

app.mount("/static", StaticFiles(directory=str(BASE_DIR / "static")), name="static")
app.mount("/uploads", StaticFiles(directory=str(BASE_DIR / "uploads")), name="uploads")
app.mount("/img", StaticFiles(directory=str(BASE_DIR / "img")), name="img")

from modules.routes.auth_routes import router as auth_router, set_templates as set_auth_templates
from modules.routes.main_routes import router as main_router, set_templates as set_main_templates
from modules.routes.help_routes import router as help_router, set_templates as set_help_templates
from modules.routes.profile_routes import router as profile_router, set_templates as set_profile_templates
from modules.routes.admin_dashboard_routes import router as admin_dashboard_router, set_templates as set_admin_dashboard_templates
from modules.routes.notification_routes import router as notification_router
from modules.routes.garage_routes import router as garage_router, set_templates as set_garage_templates

from modules.routes.admin_routes import router as legacy_admin_router, set_templates as set_legacy_admin_templates

from modules.rpmt.routes import (
    dashboard_router as rpmt_dashboard_router, set_dashboard_templates,
    projects_router as rpmt_projects_router, set_projects_templates,
    admin_router as rpmt_admin_router, set_admin_templates,
    weekly_router as rpmt_weekly_router, set_weekly_templates,
    report_router as rpmt_report_router, set_report_templates
)

from modules.svit import router as svit_router, set_templates as set_svit_templates

from modules.cits import router as cits_router, set_templates as set_cits_templates

from modules.spec_center import routes as spec_center_module
from modules.db_browser import routes as db_browser_routes
from modules.product_info import router as product_info_router, set_templates as set_product_info_templates

set_auth_templates(templates)
set_main_templates(templates)
set_help_templates(templates)
set_profile_templates(templates)
set_dashboard_templates(templates)
set_projects_templates(templates)
set_admin_templates(templates)
set_weekly_templates(templates)
set_report_templates(templates)
set_svit_templates(templates)
set_cits_templates(templates)
set_admin_dashboard_templates(templates)
set_product_info_templates(templates)

set_legacy_admin_templates(templates)

set_spec_center_templates = getattr(spec_center_module, 'set_templates', None)
if set_spec_center_templates:
    set_spec_center_templates(templates)

                                         
set_garage_templates(templates)

app.include_router(auth_router, prefix="/auth", tags=["auth"])
app.include_router(main_router, tags=["main"])
app.include_router(profile_router, tags=["profile"])

app.include_router(help_router, tags=["help"])
app.include_router(admin_dashboard_router, tags=["admin-dashboard"])
app.include_router(legacy_admin_router, tags=["admin"])
app.include_router(notification_router, tags=["notifications"]) 
app.include_router(garage_router, prefix="/api/garage", tags=["garage"])
app.include_router(rpmt_dashboard_router, prefix="/rpmt", tags=["rpmt-dashboard"])
app.include_router(rpmt_projects_router, prefix="/rpmt", tags=["rpmt-projects"])
app.include_router(rpmt_admin_router, prefix="/rpmt", tags=["rpmt-admin"])
app.include_router(rpmt_weekly_router, prefix="/rpmt", tags=["rpmt-weekly"])
app.include_router(rpmt_report_router, prefix="/rpmt", tags=["rpmt-reports"])

app.include_router(svit_router, prefix="/svit", tags=["svit"])
app.include_router(cits_router, prefix="/cits", tags=["cits"])
app.include_router(product_info_router, tags=["product-info"])

app.include_router(spec_center_module.router, tags=["spec-center"])
app.include_router(db_browser_routes.router, tags=["db-browser"])

@app.get("/favicon.ico")
def get_favicon():
    """Serve favicon"""
    favicon_path = BASE_DIR / "static" / "favicon.ico"
    if favicon_path.exists():
        return FileResponse(favicon_path, media_type="image/x-icon")
    raise HTTPException(status_code=404, detail="Favicon not found")

@app.get("/file/{module}/{filename:path}")
def serve_file(module: str, filename: str):
    """Serve files with special character handling (especially # in filenames)"""
    import urllib.parse
    filename = urllib.parse.unquote(filename)
    
    valid_modules = ["svit", "cits", "uploads", "rpmt", "spec_center"]
    if module not in valid_modules:
        raise HTTPException(status_code=400, detail="Invalid module")
    
    file_path = BASE_DIR / "uploads" / module / filename
    
    try:
        file_path = file_path.resolve()
        uploads_dir = (BASE_DIR / "uploads").resolve()
        if not str(file_path).startswith(str(uploads_dir)):
            raise HTTPException(status_code=403, detail="Forbidden")
    except:
        raise HTTPException(status_code=403, detail="Forbidden")
    
    if not file_path.exists():
        safe_filename = re.sub(r'[#?&=%;]', '_', filename)
        file_path = BASE_DIR / "uploads" / module / safe_filename
    
    if not file_path.exists():
        raise HTTPException(status_code=404, detail="File not found")
    
    return FileResponse(file_path)

@app.get('/download/app-desktop')
def download_app_desktop(request: Request):
    """Serve the locally-built QMS Desktop Windows exe as an attachment.
    Place the built file at: static/downloads/qms-desktop.exe
    """
    file_path = BASE_DIR / "static" / "downloads" / "qms-desktop.exe"
    if not file_path.exists():
        raise HTTPException(status_code=404, detail="Download not available")

                                                   
    return FileResponse(file_path, media_type='application/octet-stream', headers={
        'Content-Disposition': 'attachment; filename="qms-desktop.exe"'
    })

@app.get("/api/set-language/{lang}")
def set_language(lang: str, request: Request):
    if lang in ["ko", "en"]:
        response = RedirectResponse(url=request.headers.get("referer", "/"), status_code=303)
        response.set_cookie("lang", lang, max_age=31536000, path="/")
        return response
    raise HTTPException(status_code=400, detail="Invalid language")
