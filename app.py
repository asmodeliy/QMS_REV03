from pathlib import Path
from fastapi import FastAPI, Request, HTTPException
from pydantic import BaseModel
from fastapi.responses import RedirectResponse, FileResponse
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates
from fastapi.exceptions import HTTPException
from starlette.middleware.sessions import SessionMiddleware
from fastapi.middleware.cors import CORSMiddleware
from starlette.middleware.gzip import GZipMiddleware

try:
    from .services import compute_derived
except Exception:
    from services import compute_derived
try:
    from .core.config import BASE_DIR, SESSION_SECRET
except Exception:
    from core.config import BASE_DIR, SESSION_SECRET
try:
    from .core.middleware import RequestLoggingMiddleware
except Exception:
    from core.middleware import RequestLoggingMiddleware
try:
    from .core.i18n import t, get_locale
except Exception:
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

try:
    from .modules.routes.auth_routes import router as auth_router, set_templates as set_auth_templates
    from .modules.routes.main_routes import router as main_router, set_templates as set_main_templates
    from .modules.routes.help_routes import router as help_router, set_templates as set_help_templates
    from .modules.routes.profile_routes import router as profile_router, set_templates as set_profile_templates
    from .modules.routes.admin_dashboard_routes import router as admin_dashboard_router, set_templates as set_admin_dashboard_templates
    from .modules.routes.notification_routes import router as notification_router
    from .modules.routes.garage_routes import router as garage_router, set_templates as set_garage_templates

    from .modules.routes.admin_routes import router as legacy_admin_router, set_templates as set_legacy_admin_templates
except Exception:
    from modules.routes.auth_routes import router as auth_router, set_templates as set_auth_templates
    from modules.routes.main_routes import router as main_router, set_templates as set_main_templates
    from modules.routes.help_routes import router as help_router, set_templates as set_help_templates
    from modules.routes.profile_routes import router as profile_router, set_templates as set_profile_templates
    from modules.routes.admin_dashboard_routes import router as admin_dashboard_router, set_templates as set_admin_dashboard_templates
    from modules.routes.notification_routes import router as notification_router
    from modules.routes.garage_routes import router as garage_router, set_templates as set_garage_templates

    from modules.routes.admin_routes import router as legacy_admin_router, set_templates as set_legacy_admin_templates

try:
    from .modules.rpmt.routes import (
        dashboard_router as rpmt_dashboard_router, set_dashboard_templates,
        projects_router as rpmt_projects_router, set_projects_templates,
        admin_router as rpmt_admin_router, set_admin_templates,
        weekly_router as rpmt_weekly_router, set_weekly_templates,
        report_router as rpmt_report_router, set_report_templates
    )

    from .modules.svit import router as svit_router, set_templates as set_svit_templates

    from .modules.cits import router as cits_router, set_templates as set_cits_templates

    from .modules.spec_center import routes as spec_center_module
    from .modules.db_browser import routes as db_browser_routes
    from .modules.mcp.routes import router as mcp_router
    from .modules.mcp.gpt4all_routes import router as gpt4all_router
    from .modules.product_info import router as product_info_router, set_templates as set_product_info_templates
except Exception:
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
    from modules.mcp.routes import router as mcp_router
    from modules.mcp.gpt4all_routes import router as gpt4all_router
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
app.include_router(mcp_router, tags=["mcp"])
app.include_router(gpt4all_router, tags=["gpt4all"])

@app.get("/ai-chat")
def ai_chat_page(request: Request):
    """Serve the GPT4All chat interface (admin-only)"""
    # Require admin role or be in GARAGE_ADMIN_EMAILS
    sess = getattr(request, 'session', None)
    if not sess or not sess.get('is_authenticated'):
        return RedirectResponse(url='/auth/login?next=/ai-chat', status_code=303)
    email = sess.get('email', '')
    role = sess.get('role', '')
    try:
        from .core.config import GARAGE_ADMIN_EMAILS
        if not ((role and role.lower() == 'admin') or (email and email.lower() in GARAGE_ADMIN_EMAILS)):
            return RedirectResponse(url='/main', status_code=303)
    except Exception:
        return RedirectResponse(url='/main', status_code=303)

    return templates.TemplateResponse("gpt4all_chat.html", {"request": request})

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

@app.get("/health")
def health_check():
    """Health check endpoint for Docker and monitoring"""
    return {
        "status": "healthy",
        "service": "QMS Application",
        "version": "1.0.0"
    }


@app.get("/api/me")
def api_me(request: Request):
    """Return session-based authentication info for desktop clients."""
    # Prefer explicit is_authenticated flag in session
    if not request.session.get("is_authenticated") or not request.session.get("user_id"):
        return {"authenticated": False, "user": None}

    return {
        "authenticated": True,
        "user": {
            "id": request.session.get("user_id"),
            "email": request.session.get("email"),
            "english_name": request.session.get("english_name"),
            "department": request.session.get("department"),
            "role": request.session.get("role")
        }
    }


@app.get('/api/garage/files')
def api_garage_files(request: Request):
    """Compatibility endpoint for Desktop: list files in uploads/garage."""
    if not request.session.get('is_authenticated'):
        raise HTTPException(status_code=401, detail='Authentication required')
    files = []
    final_dir = BASE_DIR / 'uploads' / 'garage'
    garage_logger = None
    try:
        from core.logger import app_logger, garage_logger as gl
        garage_logger = gl
    except Exception:
        pass

    try:
        if final_dir.exists():
            for p in sorted(final_dir.iterdir(), key=lambda x: x.stat().st_mtime, reverse=True):
                if not p.is_file():
                    continue
                stat = p.stat()
                orig = '-'.join(p.name.split('-')[2:]) if len(p.name.split('-')) >= 3 else p.name
                files.append({
                    'safe_name': p.name,
                    'filename': orig,
                    'size': stat.st_size,
                    'created': int(stat.st_mtime)
                })
        return {'ok': True, 'files': files}
    except Exception as e:
        if garage_logger:
            garage_logger.log_error('list_files_compat_error', 'Failed to list files via compatibility endpoint', {'error': str(e)})
        raise HTTPException(status_code=500, detail='Failed to list garage files')

@app.get('/api/garage/debug')
def api_garage_debug(request: Request):
    """Compatibility debug endpoint for desktop: session check."""
    if not request.session.get('is_authenticated'):
        raise HTTPException(status_code=401, detail='Authentication required')
    return {'session': True, 'email': request.session.get('email')}

@app.get("/api/set-language/{lang}")
def set_language(lang: str, request: Request):
    if lang in ["ko", "en"]:
        response = RedirectResponse(url=request.headers.get("referer", "/"), status_code=303)
        response.set_cookie("lang", lang, max_age=31536000, path="/")
        return response
    raise HTTPException(status_code=400, detail="Invalid language")

# AI Assistant API
class AIQuery(BaseModel):
    question: str

@app.post("/api/ai-assistant/query")
async def ai_assistant_query(query: AIQuery, request: Request):
    """AI Assistant natural language query endpoint"""
    import sqlite3
    
    question = query.question.lower()
    
    try:
        # Simple pattern matching for now
        if "프로젝트" in question or "project" in question:
            # Query projects
            conn = sqlite3.connect("rpmt.db")
            conn.row_factory = sqlite3.Row
            cursor = conn.cursor()
            
            if "활성" in question or "active" in question:
                cursor.execute("SELECT * FROM projects WHERE active = 1 ORDER BY created_at DESC")
            else:
                cursor.execute("SELECT * FROM projects ORDER BY created_at DESC LIMIT 10")
            
            projects = [dict(row) for row in cursor.fetchall()]
            conn.close()
            
            if not projects:
                answer = "등록된 프로젝트가 없습니다."
            else:
                answer = f"현재 {len(projects)}개의 프로젝트가 있습니다:\n\n"
                for i, proj in enumerate(projects[:5], 1):
                    answer += f"{i}. {proj['code']}"
                    if proj.get('process'):
                        answer += f" ({proj['process']})"
                    answer += f"\n   PDK: {proj.get('pdk_ver', 'N/A')}\n"
                    answer += f"   상태: {'Active' if proj['active'] else 'Inactive'}\n\n"
            
            return {"answer": answer, "success": True}
        
        elif "태스크" in question or "task" in question:
            # Query tasks
            conn = sqlite3.connect("rpmt.db")
            conn.row_factory = sqlite3.Row
            cursor = conn.cursor()
            
            if "완료" in question or "complete" in question:
                cursor.execute("SELECT * FROM tasks WHERE status = 'COMPLETE' AND archived = 0 ORDER BY id DESC")
            else:
                cursor.execute("SELECT * FROM tasks WHERE archived = 0 ORDER BY id DESC LIMIT 10")
            
            tasks = [dict(row) for row in cursor.fetchall()]
            conn.close()
            
            if not tasks:
                answer = "등록된 태스크가 없습니다."
            else:
                answer = f"태스크 {len(tasks)}개:\n\n"
                for task in tasks[:5]:
                    status_icon = "✓" if task['status'] == "COMPLETE" else "○"
                    answer += f"{status_icon} {task['cat1']}: {task['cat2']}\n"
                
                # Calculate stats
                conn = sqlite3.connect("rpmt.db")
                cursor = conn.cursor()
                cursor.execute("SELECT COUNT(*) as total FROM tasks WHERE archived = 0")
                total = cursor.fetchone()[0]
                cursor.execute("SELECT COUNT(*) as completed FROM tasks WHERE status = 'COMPLETE' AND archived = 0")
                completed = cursor.fetchone()[0]
                conn.close()
                
                if total > 0:
                    percentage = (completed / total * 100)
                    answer += f"\n진행률: {percentage:.0f}% ({completed}/{total} 태스크 완료)"
            
            return {"answer": answer, "success": True}
        
        elif "svit" in question or "이슈" in question or "issue" in question:
            # Query SVIT issues
            conn = sqlite3.connect("svit.db")
            conn.row_factory = sqlite3.Row
            cursor = conn.cursor()
            
            if "진행" in question or "progress" in question:
                cursor.execute("SELECT * FROM issues WHERE status = 'IN_PROGRESS' ORDER BY id DESC")
            else:
                cursor.execute("SELECT * FROM issues ORDER BY id DESC LIMIT 10")
            
            issues = [dict(row) for row in cursor.fetchall()]
            conn.close()
            
            if not issues:
                answer = "등록된 이슈가 없습니다."
            else:
                answer = f"이슈 {len(issues)}건:\n\n"
                for issue in issues[:5]:
                    status_icons = {"NEW": "🆕", "IN_PROGRESS": "🔄", "RESOLVED": "✅"}
                    icon = status_icons.get(issue['status'], "❓")
                    answer += f"{icon} {issue['tracking_no']} [{issue['status']}]\n"
                    if issue.get('issue_phenomenon'):
                        answer += f"   {issue['issue_phenomenon']}\n"
                answer += "\n"
                
                # Calculate status counts
                conn = sqlite3.connect("svit.db")
                cursor = conn.cursor()
                cursor.execute("SELECT status, COUNT(*) as count FROM issues GROUP BY status")
                stats = {row[0]: row[1] for row in cursor.fetchall()}
                conn.close()
                
                answer += "상태별: "
                answer += ", ".join([f"{status} {count}건" for status, count in stats.items()])
            
            return {"answer": answer, "success": True}
        
        elif "사용자" in question or "user" in question:
            # Query users
            conn = sqlite3.connect("auth_db.db")
            conn.row_factory = sqlite3.Row
            cursor = conn.cursor()
            cursor.execute("SELECT * FROM users ORDER BY id")
            
            users = [dict(row) for row in cursor.fetchall()]
            conn.close()
            
            if not users:
                answer = "등록된 사용자가 없습니다."
            else:
                answer = f"사용자 {len(users)}명:\n\n"
                for user in users:
                    answer += f"• {user['english_name']} ({user['department']})\n"
                    answer += f"  {user['email']}\n"
            
            return {"answer": answer, "success": True}
        
        else:
            # Default response
            answer = "죄송합니다. 질문을 이해하지 못했습니다.\n\n"
            answer += "다음과 같은 질문을 해보세요:\n"
            answer += "• 활성 프로젝트 목록을 보여줘\n"
            answer += "• 완료된 태스크는 몇 개야?\n"
            answer += "• SVIT 이슈 상태를 알려줘\n"
            answer += "• 사용자 목록을 보여줘"
            
            return {"answer": answer, "success": False}
    
    except Exception as e:
        return {
            "answer": f"오류가 발생했습니다: {str(e)}\n다시 시도해주세요.",
            "success": False
        }
