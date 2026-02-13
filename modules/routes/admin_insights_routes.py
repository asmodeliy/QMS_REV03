from datetime import datetime, timedelta
import json
import sqlite3
from pathlib import Path
from typing import Dict, List, Tuple

from fastapi import APIRouter, Request, Depends, Form, HTTPException
from fastapi.responses import HTMLResponse, RedirectResponse, JSONResponse
from sqlalchemy.orm import Session

from core.auth.db import get_auth_db
from core.auth.models import User, ModulePermission
from core.config import BASE_DIR, ACTIVITY_LOG_RETENTION_DAYS
from core.i18n import get_locale
from core.logger import app_logger

router = APIRouter()

templates = None


def set_templates(tmpl):
    global templates
    templates = tmpl


def _ensure_admin(request: Request):
    if not request.session.get("is_authenticated"):
        return RedirectResponse(url="/auth/login", status_code=303)
    role = (request.session.get("role") or "").lower()
    if role != "admin":
        return RedirectResponse(url="/main", status_code=303)
    return None


MODULES: List[Tuple[str, str]] = [
    ("main", "Main"),
    ("rpmt", "RPMT"),
    ("svit", "SVIT"),
    ("cits", "CITS"),
    ("spec_center", "Spec-Center"),
    ("product_info", "Product-Info"),
]

ROLE_OPTIONS = ["None", "User", "Manager", "Admin"]


@router.get("/admin/permissions", response_class=HTMLResponse)
def permissions_page(request: Request, db: Session = Depends(get_auth_db)):
    r = _ensure_admin(request)
    if r:
        return r

    locale = get_locale(request)
    users = db.query(User).order_by(User.email.asc()).all()
    permissions = db.query(ModulePermission).filter(ModulePermission.is_active == True).all()

    perm_map: Dict[Tuple[int, str], str] = {}
    for p in permissions:
        perm_map[(p.user_id, p.module_name)] = p.role

    return templates.TemplateResponse(
        "shared/admin_permissions.html",
        {
            "request": request,
            "locale": locale,
            "users": users,
            "modules": MODULES,
            "roles": ROLE_OPTIONS,
            "perm_map": perm_map,
        },
    )


@router.post("/admin/permissions")
async def permissions_save(request: Request, db: Session = Depends(get_auth_db)):
    r = _ensure_admin(request)
    if r:
        return r

    form_data = dict(await request.form())

    updates = 0
    for key, value in form_data.items():
        if not key.startswith("perm_"):
            continue
        parts = key.split("_")
        if len(parts) < 3:
            continue
        user_id = int(parts[1])
        module_name = "_".join(parts[2:])
        role = value

        existing = db.query(ModulePermission).filter(
            ModulePermission.user_id == user_id,
            ModulePermission.module_name == module_name,
        ).first()

        if role == "None":
            if existing:
                existing.is_active = False
                updates += 1
            continue

        if existing:
            existing.role = role
            existing.is_active = True
        else:
            db.add(ModulePermission(user_id=user_id, module_name=module_name, role=role, is_active=True))
        updates += 1

    db.commit()
    app_logger.info("Permissions updated", {"count": updates})
    return RedirectResponse(url="/admin/permissions", status_code=303)


@router.get("/admin/metrics", response_class=HTMLResponse)
def metrics_page(request: Request):
    r = _ensure_admin(request)
    if r:
        return r

    locale = get_locale(request)
    return templates.TemplateResponse(
        "shared/admin_metrics.html",
        {"request": request, "locale": locale, "refresh_seconds": 60},
    )


@router.get("/admin/metrics/data", response_class=JSONResponse)
def metrics_data(request: Request):
    r = _ensure_admin(request)
    if r:
        raise HTTPException(status_code=403, detail="Forbidden")

    data = {
        "generated_at": datetime.utcnow().isoformat(),
        "rpmt": _load_rpmt_metrics(),
        "svit": _load_svit_metrics(),
        "cits": _load_cits_metrics(),
        "spec_center": _load_spec_metrics(),
    }
    return data


@router.get("/admin/activity", response_class=HTMLResponse)
def activity_page(request: Request):
    r = _ensure_admin(request)
    if r:
        return r

    locale = get_locale(request)
    summary = _load_activity_summary(days=ACTIVITY_LOG_RETENTION_DAYS)
    return templates.TemplateResponse(
        "shared/admin_activity.html",
        {"request": request, "locale": locale, "summary": summary, "days": ACTIVITY_LOG_RETENTION_DAYS},
    )


def _load_rpmt_metrics() -> Dict[str, int]:
    db_path = BASE_DIR / "rpmt.db"
    if not db_path.exists():
        return {"projects_total": 0, "projects_active": 0, "tasks_total": 0, "tasks_completed": 0}

    conn = sqlite3.connect(str(db_path))
    try:
        cur = conn.cursor()
        cur.execute("SELECT COUNT(1) FROM projects")
        projects_total = cur.fetchone()[0] or 0
        cur.execute("SELECT COUNT(1) FROM projects WHERE active = 1")
        projects_active = cur.fetchone()[0] or 0
        cur.execute("SELECT COUNT(1) FROM tasks")
        tasks_total = cur.fetchone()[0] or 0
        cur.execute("SELECT COUNT(1) FROM tasks WHERE status = 'Complete'")
        tasks_completed = cur.fetchone()[0] or 0
        return {
            "projects_total": projects_total,
            "projects_active": projects_active,
            "tasks_total": tasks_total,
            "tasks_completed": tasks_completed,
        }
    finally:
        conn.close()


def _load_svit_metrics() -> Dict[str, int]:
    db_path = BASE_DIR / "svit.db"
    if not db_path.exists():
        return {"issues_total": 0, "new": 0, "in_progress": 0, "pending": 0, "resolved": 0}

    conn = sqlite3.connect(str(db_path))
    try:
        cur = conn.cursor()
        cur.execute("SELECT COUNT(1) FROM issues")
        total = cur.fetchone()[0] or 0
        cur.execute("SELECT COUNT(1) FROM issues WHERE status = 'NEW'")
        new = cur.fetchone()[0] or 0
        cur.execute("SELECT COUNT(1) FROM issues WHERE status = 'IN_PROGRESS'")
        in_progress = cur.fetchone()[0] or 0
        cur.execute("SELECT COUNT(1) FROM issues WHERE status = 'PENDING_REVIEW'")
        pending = cur.fetchone()[0] or 0
        cur.execute("SELECT COUNT(1) FROM issues WHERE status = 'RESOLVED'")
        resolved = cur.fetchone()[0] or 0
        return {
            "issues_total": total,
            "new": new,
            "in_progress": in_progress,
            "pending": pending,
            "resolved": resolved,
        }
    finally:
        conn.close()


def _load_cits_metrics() -> Dict[str, int]:
    db_path = BASE_DIR / "customer_issue.db"
    if not db_path.exists():
        return {"issues_total": 0, "open": 0, "pending": 0, "close": 0}

    conn = sqlite3.connect(str(db_path))
    try:
        cur = conn.cursor()
        cur.execute("SELECT COUNT(1) FROM customer_issues")
        total = cur.fetchone()[0] or 0
        cur.execute("SELECT COUNT(1) FROM customer_issues WHERE status = 'OPEN'")
        open_count = cur.fetchone()[0] or 0
        cur.execute("SELECT COUNT(1) FROM customer_issues WHERE status = 'PENDING'")
        pending = cur.fetchone()[0] or 0
        cur.execute("SELECT COUNT(1) FROM customer_issues WHERE status = 'CLOSE'")
        close = cur.fetchone()[0] or 0
        return {
            "issues_total": total,
            "open": open_count,
            "pending": pending,
            "close": close,
        }
    finally:
        conn.close()


def _load_spec_metrics() -> Dict[str, int]:
    db_path = BASE_DIR / "spec_center.db"
    if not db_path.exists():
        return {"files_total": 0, "categories_total": 0}

    conn = sqlite3.connect(str(db_path))
    try:
        cur = conn.cursor()
        cur.execute("SELECT COUNT(1) FROM spec_files")
        files_total = cur.fetchone()[0] or 0
        cur.execute("SELECT COUNT(1) FROM spec_categories")
        categories_total = cur.fetchone()[0] or 0
        return {"files_total": files_total, "categories_total": categories_total}
    finally:
        conn.close()


def _load_activity_summary(days: int = 30) -> Dict[str, List[Tuple[str, int]]]:
    logs_dir = BASE_DIR / "logs"
    if not logs_dir.exists():
        return {"top_paths": [], "top_modules": [], "top_users": [], "recent": []}

    cutoff = datetime.now() - timedelta(days=days)
    top_paths: Dict[str, int] = {}
    top_modules: Dict[str, int] = {}
    top_users: Dict[str, int] = {}
    recent: List[Dict[str, str]] = []

    for log_path in sorted(logs_dir.glob("user_activity_*.log"), reverse=True):
        try:
            date_part = log_path.stem.replace("user_activity_", "")
            if len(date_part) != 8:
                continue
            log_date = datetime.strptime(date_part, "%Y%m%d")
            if log_date < cutoff:
                continue
        except Exception:
            continue

        try:
            with open(log_path, "r", encoding="utf-8") as f:
                for line in f:
                    try:
                        payload = json.loads(line.split("|", 2)[-1].strip())
                    except Exception:
                        continue

                    ts = payload.get("timestamp")
                    module = payload.get("module") or "unknown"
                    user = payload.get("user") or "unknown"
                    details = payload.get("details") or {}
                    path = details.get("path") or "-"

                    top_modules[module] = top_modules.get(module, 0) + 1
                    top_users[user] = top_users.get(user, 0) + 1
                    if path != "-":
                        top_paths[path] = top_paths.get(path, 0) + 1

                    if len(recent) < 50:
                        recent.append({
                            "timestamp": ts,
                            "user": user,
                            "module": module,
                            "path": path,
                        })
        except Exception:
            continue

    def _top(items: Dict[str, int], limit: int = 10) -> List[Tuple[str, int]]:
        return sorted(items.items(), key=lambda x: x[1], reverse=True)[:limit]

    return {
        "top_paths": _top(top_paths),
        "top_modules": _top(top_modules),
        "top_users": _top(top_users),
        "recent": recent,
    }
