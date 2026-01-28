from fastapi import APIRouter, Request, Depends
from fastapi.responses import JSONResponse
from sqlalchemy.orm import Session
from sqlalchemy import or_, func
from datetime import datetime, timedelta

from core.db import get_db
from core.auth.models import User
from core.auth.db import get_auth_db_sync
from models import Task, Project, StatusEnum

router = APIRouter()

def ensure_authenticated(request: Request):
    if not request.session.get("user_id"):
        return None
    return request.session.get("email")

@router.get("/api/notifications/count")
async def get_notification_count(request: Request, db: Session = Depends(get_db)):
    email = ensure_authenticated(request)
    if not email:
        return JSONResponse({"count": 0})

    auth_db = get_auth_db_sync()
    try:
        user = auth_db.query(User).filter(User.email == email).first()
    finally:
        auth_db.close()

    english_name = request.session.get("english_name", "").strip()
    department = request.session.get("department", "").strip()

    if not english_name and user:
        english_name = (user.english_name or "").strip()
    if not department and user:
        department = (user.department or "").strip()

    count = 0
    debug_info = {
        "user": english_name,
        "rpmt_debug": {},
        "svit_debug": {},
        "cits_debug": {}
    }

    try:
        if department:
            today = datetime.now().date()
            rpmt_q = db.query(Task).join(Project).filter(
                Task.dept_to.ilike(f"%{department}%"),
                or_(Task.archived == False, Task.archived == None),
                Task.due_date < today
            )
            rpmt_count = rpmt_q.count()
            debug_info["rpmt_debug"]["department"] = department
            debug_info["rpmt_debug"]["overdue_count"] = rpmt_count
            count += rpmt_count
    except Exception as e:
        debug_info["rpmt_debug"]["error"] = str(e)

    try:
        from modules.svit.models import SVITIssue, IssueStatusEnum
        svit_q = db.query(SVITIssue).filter(
            or_(
                SVITIssue.assignee == english_name,
                SVITIssue.creator == english_name
            ),
            or_(
                SVITIssue.status == IssueStatusEnum.NEW,
                SVITIssue.status == IssueStatusEnum.IN_PROGRESS
            )
        )
        svit_count = svit_q.count()
        debug_info["svit_debug"]["user"] = english_name
        debug_info["svit_debug"]["active_count"] = svit_count
        count += svit_count
    except Exception as e:
        debug_info["svit_debug"]["error"] = str(e)

    try:
        from modules.cits.models import CustomerIssue, IssueStatusEnum as CITSStatusEnum
        from modules.cits.db import SessionLocal as CITSSessionLocal

        cits_db = CITSSessionLocal()
        try:
            all_cits = cits_db.query(CustomerIssue).all()
            debug_info["cits_debug"]["total_tickets"] = len(all_cits)
            debug_info["cits_debug"]["sample_tickets"] = []

            for ticket in all_cits[:3]:
                debug_info["cits_debug"]["sample_tickets"].append({
                    "id": ticket.id,
                    "assignee": ticket.assignee,
                    "reporter": ticket.reporter,
                    "status": str(ticket.status)
                })

            target_name = (english_name or "").strip().lower()
            c_assignee = func.lower(func.trim(func.coalesce(CustomerIssue.assignee, "")))
            c_reporter = func.lower(func.trim(func.coalesce(CustomerIssue.reporter, "")))
            cits_count = cits_db.query(CustomerIssue).filter(
                or_(
                    c_assignee == target_name,
                    c_reporter == target_name
                ),
                or_(
                    CustomerIssue.status == CITSStatusEnum.OPEN,
                    CustomerIssue.status == CITSStatusEnum.PENDING
                )
            ).count()

            debug_info["cits_debug"]["filtered_count"] = cits_count
            debug_info["cits_debug"]["filter_user"] = english_name
            debug_info["cits_debug"]["filter_user_normalized"] = target_name
            count += cits_count
        finally:
            cits_db.close()
    except Exception as e:
        debug_info["cits_debug"]["error"] = str(e)

    return JSONResponse({"count": count})

@router.get("/api/notifications")
async def get_notifications(request: Request, db: Session = Depends(get_db)):
    email = ensure_authenticated(request)
    if not email:
        return JSONResponse({"notifications": []})

    auth_db = get_auth_db_sync()
    try:
        user = auth_db.query(User).filter(User.email == email).first()
    finally:
        auth_db.close()
    
    english_name = request.session.get("english_name", "").strip()
    department = request.session.get("department", "").strip()

    if not english_name and user:
        english_name = (user.english_name or "").strip()
    if not department and user:
        department = (user.department or "").strip()

    notifications = []

    try:
        if department:
            today = datetime.now().date()
            tasks = db.query(Task).join(Project).filter(
                Task.dept_to.ilike(f"%{department}%"),
                or_(Task.archived == False, Task.archived == None),
                Task.due_date < today
            ).order_by(Task.due_date.asc()).limit(20).all()

            for task in tasks:
                try:
                    if task.due_date:
                        days_left = (task.due_date - datetime.now().date()).days
                        if days_left < 0:
                            time_str = f"⚠️ {abs(days_left)}일 지남"
                        elif days_left == 0:
                            time_str = "⚠️ 오늘 마감"
                        elif days_left <= 3:
                            time_str = f"🔥 {days_left}일 남음"
                        else:
                            time_str = f"{days_left}일 남음"
                    else:
                        time_str = "기한 없음"

                    status_str = task.status.value if hasattr(task.status, 'value') else str(task.status)

                    notifications.append({
                        "id": f"rpmt-{task.id}",
                        "module": "rpmt",
                        "title": f"{task.project.code if task.project else 'Project'} - {task.cat2 or task.cat1 or 'Task'}",
                        "description": f"담당: {task.dept_to} | 상태: {status_str}",
                        "time": time_str,
                        "link": f"/rpmt/projects/{task.project_id}",
                        "read": False
                    })
                except Exception as e:
                    pass
    except Exception as e:
        pass

    try:
        from modules.svit.models import SVITIssue, IssueStatusEnum
        issues = db.query(SVITIssue).filter(
            or_(
                SVITIssue.assignee == english_name,
                SVITIssue.creator == english_name
            ),
            or_(
                SVITIssue.status == IssueStatusEnum.NEW,
                SVITIssue.status == IssueStatusEnum.IN_PROGRESS
            )
        ).order_by(SVITIssue.created_at.desc()).limit(20).all()

        for issue in issues:
            try:
                time_ago = datetime.now() - issue.created_at
                if time_ago.days > 0:
                    time_str = f"{time_ago.days}일 전"
                else:
                    hours = time_ago.seconds // 3600
                    time_str = f"{hours}시간 전" if hours > 0 else "방금"

                status_str = issue.status.value if hasattr(issue.status, 'value') else str(issue.status)

                notifications.append({
                    "id": f"svit-{issue.id}",
                    "module": "svit",
                    "title": f"[{issue.shuttle_id}] {issue.node or 'Issue'}",
                    "description": f"담당: {issue.assignee or '미지정'} | 상태: {status_str}",
                    "time": time_str,
                    "link": f"/svit/issues/{issue.id}",
                    "read": False
                })
            except Exception as e:
                pass
    except Exception as e:
        pass

    try:
        from modules.cits.models import CustomerIssue, IssueStatusEnum as CITSStatusEnum
        from modules.cits.db import SessionLocal as CITSSessionLocal

        cits_db = CITSSessionLocal()
        try:
            target_name = (english_name or "").strip().lower()
            c_assignee = func.lower(func.trim(func.coalesce(CustomerIssue.assignee, "")))
            c_reporter = func.lower(func.trim(func.coalesce(CustomerIssue.reporter, "")))
            tickets = cits_db.query(CustomerIssue).filter(
                or_(
                    c_assignee == target_name,
                    c_reporter == target_name
                ),
                or_(
                    CustomerIssue.status == CITSStatusEnum.OPEN,
                    CustomerIssue.status == CITSStatusEnum.PENDING
                )
            ).order_by(CustomerIssue.created_at.desc()).limit(20).all()

            for ticket in tickets:
                try:
                    time_ago = datetime.now() - ticket.created_at
                    if time_ago.days > 0:
                        time_str = f"{time_ago.days}일 전"
                    else:
                        hours = time_ago.seconds // 3600
                        time_str = f"{hours}시간 전" if hours > 0 else "방금"

                    status_str = ticket.status.value if hasattr(ticket.status, 'value') else str(ticket.status)

                    notifications.append({
                    "id": f"cits-{ticket.id}",
                    "module": "cits",
                    "title": f"[{ticket.ticket_no}] {ticket.title}",
                    "description": f"담당: {ticket.assignee or '미지정'} | 우선순위: {ticket.priority or 'N/A'}",
                    "time": time_str,
                    "link": f"/cits/issue/{ticket.id}",
                    "read": False
                })
                except Exception as e:
                    pass
        finally:
            cits_db.close()
    except Exception as e:
        pass

    return JSONResponse({"notifications": notifications[:30]})

@router.post("/api/notifications/{notification_id}/read")
async def mark_notification_read(notification_id: str, request: Request):
    email = ensure_authenticated(request)
    if not email:
        return JSONResponse({"success": False})

    return JSONResponse({"success": True})

@router.get("/api/notifications/debug")
async def debug_notifications(request: Request, db: Session = Depends(get_db)):
    return JSONResponse({"message": "Debug endpoint"})
