"""
MCP Server Implementation for QMS

This module implements an MCP server that exposes QMS functionality to LLMs.
It provides tools, resources, and prompts for interacting with the QMS system.
"""
from typing import List, Dict, Any, Optional
from datetime import date, datetime
from mcp.server.fastmcp import FastMCP
from sqlalchemy.orm import Session
from sqlalchemy import select, func

from core.db import get_db
from models import Project, Task, User, StatusEnum, RoleEnum

# SVIT imports
from modules.svit.models import Issue, Shuttle, IssueStatusEnum
from modules.svit.db import get_svit_db_sync

# RPMT imports
from modules.rpmt.models import Project as RPMTProject, Task as RPMTTask, PDKDKEntry
from modules.rpmt.db import get_rpmt_db_sync

# CITS imports
from modules.cits.models import CustomerIssue, Customer, ContactPerson, IssueConversation
from modules.cits.db import get_customer_db_sync

# Spec-Center imports
from modules.spec_center.models import SpecCategory, SpecFile
from modules.spec_center.db import get_spec_db_sync


# Initialize FastMCP server
mcp = FastMCP(
    name="QMS-MCP-Server"
)


# Helper function to get database session with proper cleanup
def with_db_session(func):
    """Decorator to manage database session lifecycle"""
    def wrapper(*args, **kwargs):
        db = next(get_db())
        try:
            return func(db, *args, **kwargs)
        finally:
            db.close()
    return wrapper


# ==================== TOOLS ====================

@mcp.tool()
def list_projects(active_only: bool = True, limit: int = 50) -> List[Dict[str, Any]]:
    """
    List all projects in the QMS system.
    
    Args:
        active_only: If True, only return active projects (default: True)
        limit: Maximum number of projects to return (default: 50, max: 100)
    
    Returns:
        List of projects with their details
    """
    @with_db_session
    def _impl(db: Session):
        limit_val = min(limit, 100)
        query = select(Project)
        if active_only:
            query = query.where(Project.active == True)
        query = query.limit(limit_val).order_by(Project.created_at.desc())
        
        projects = db.execute(query).scalars().all()
        
        return [{
            "id": p.id,
            "code": p.code,
            "process": p.process,
            "metal_option": p.metal_option,
            "ip_code": p.ip_code,
            "pdk_ver": p.pdk_ver,
            "active": p.active,
            "created_at": p.created_at.isoformat() if p.created_at else None
        } for p in projects]
    
    return _impl()


@mcp.tool()
def get_project_details(project_id: int) -> Dict[str, Any]:
    """
    Get detailed information about a specific project.
    
    Args:
        project_id: The ID of the project
    
    Returns:
        Detailed project information including task summary
    """
    @with_db_session
    def _impl(db: Session):
        project = db.execute(
            select(Project).where(Project.id == project_id)
        ).scalar_one_or_none()
        
        if not project:
            return {"error": f"Project with ID {project_id} not found"}
        
        # Get task statistics using database aggregation
        task_stats = {
            "total": db.execute(
                select(func.count(Task.id)).where(Task.project_id == project_id)
            ).scalar() or 0,
            "complete": db.execute(
                select(func.count(Task.id)).where(
                    Task.project_id == project_id,
                    Task.status == StatusEnum.COMPLETE
                )
            ).scalar() or 0,
            "in_progress": db.execute(
                select(func.count(Task.id)).where(
                    Task.project_id == project_id,
                    Task.status == StatusEnum.IN_PROGRESS
                )
            ).scalar() or 0,
            "not_started": db.execute(
                select(func.count(Task.id)).where(
                    Task.project_id == project_id,
                    Task.status == StatusEnum.NOT_STARTED
                )
            ).scalar() or 0,
            "na": db.execute(
                select(func.count(Task.id)).where(
                    Task.project_id == project_id,
                    Task.status == StatusEnum.NA
                )
            ).scalar() or 0
        }
        
        return {
            "id": project.id,
            "code": project.code,
            "process": project.process,
            "metal_option": project.metal_option,
            "ip_code": project.ip_code,
            "pdk_ver": project.pdk_ver,
            "active": project.active,
            "created_at": project.created_at.isoformat() if project.created_at else None,
            "task_statistics": task_stats
        }
    
    return _impl()


@mcp.tool()
def list_tasks(
    project_id: Optional[int] = None,
    status: Optional[str] = None,
    limit: int = 50
) -> List[Dict[str, Any]]:
    """
    List tasks in the QMS system.
    
    Args:
        project_id: Filter by project ID (optional)
        status: Filter by status: "Complete", "In-progress", "Not Started", "N/A" (optional)
        limit: Maximum number of tasks to return (default: 50, max: 100)
    
    Returns:
        List of tasks with their details
    
    Raises:
        ValueError: If status value is invalid
    """
    @with_db_session
    def _impl(db: Session):
        limit_val = min(limit, 100)
        query = select(Task).where(Task.archived == False)
        
        if project_id is not None:
            query = query.where(Task.project_id == project_id)
        
        if status:
            try:
                status_enum = StatusEnum(status)
                query = query.where(Task.status == status_enum)
            except ValueError:
                raise ValueError(f"Invalid status: {status}. Valid values: Complete, In-progress, Not Started, N/A")
        
        query = query.limit(limit_val).order_by(Task.updated_at.desc())
        tasks = db.execute(query).scalars().all()
        
        return [{
            "id": t.id,
            "project_id": t.project_id,
            "cat1": t.cat1,
            "cat2": t.cat2,
            "dept_from": t.dept_from,
            "dept_to": t.dept_to,
            "due_date": t.due_date.isoformat() if t.due_date else None,
            "status": t.status.value if t.status else None,
            "reason": t.reason,
            "updated_at": t.updated_at.isoformat() if t.updated_at else None
        } for t in tasks]
    
    return _impl()


@mcp.tool()
def get_task_details(task_id: int) -> Dict[str, Any]:
    """
    Get detailed information about a specific task.
    
    Args:
        task_id: The ID of the task
    
    Returns:
        Detailed task information
    """
    @with_db_session
    def _impl(db: Session):
        task = db.execute(
            select(Task).where(Task.id == task_id)
        ).scalar_one_or_none()
        
        if not task:
            return {"error": f"Task with ID {task_id} not found"}
        
        return {
            "id": task.id,
            "project_id": task.project_id,
            "cat1": task.cat1,
            "cat2": task.cat2,
            "dept_from": task.dept_from,
            "dept_to": task.dept_to,
            "due_date": task.due_date.isoformat() if task.due_date else None,
            "status": task.status.value if task.status else None,
            "reason": task.reason,
            "updated_at": task.updated_at.isoformat() if task.updated_at else None,
            "ord": task.ord,
            "file_name": task.file_name,
            "archived": task.archived
        }
    
    return _impl()


@mcp.tool()
def get_project_summary() -> Dict[str, Any]:
    """
    Get a summary of all projects in the system.
    
    Returns:
        Summary statistics about projects
    """
    @with_db_session
    def _impl(db: Session):
        total_projects = db.execute(select(func.count(Project.id))).scalar()
        active_projects = db.execute(
            select(func.count(Project.id)).where(Project.active == True)
        ).scalar()
        
        # Get status distribution using database aggregation
        total_tasks = db.execute(select(func.count(Task.id))).scalar()
        task_status_dist = {
            "complete": db.execute(
                select(func.count(Task.id)).where(Task.status == StatusEnum.COMPLETE)
            ).scalar() or 0,
            "in_progress": db.execute(
                select(func.count(Task.id)).where(Task.status == StatusEnum.IN_PROGRESS)
            ).scalar() or 0,
            "not_started": db.execute(
                select(func.count(Task.id)).where(Task.status == StatusEnum.NOT_STARTED)
            ).scalar() or 0,
            "na": db.execute(
                select(func.count(Task.id)).where(Task.status == StatusEnum.NA)
            ).scalar() or 0
        }
        
        return {
            "total_projects": total_projects,
            "active_projects": active_projects,
            "inactive_projects": total_projects - active_projects,
            "total_tasks": total_tasks,
            "task_status_distribution": task_status_dist
        }
    
    return _impl()


@mcp.tool()
def list_users(active_only: bool = True, limit: int = 50) -> List[Dict[str, Any]]:
    """
    List users in the QMS system.
    
    Args:
        active_only: If True, only return active users (default: True)
        limit: Maximum number of users to return (default: 50, max: 100)
    
    Returns:
        List of users with their details (excluding sensitive information)
    """
    @with_db_session
    def _impl(db: Session):
        limit_val = min(limit, 100)
        query = select(User)
        if active_only:
            query = query.where(User.is_active == True)
        query = query.limit(limit_val).order_by(User.created_at.desc())
        
        users = db.execute(query).scalars().all()
        
        return [{
            "id": u.id,
            "email": u.email,
            "english_name": u.english_name,
            "department": u.department,
            "role": u.role.value if u.role else None,
            "is_active": u.is_active,
            "created_at": u.created_at.isoformat() if u.created_at else None
        } for u in users]
    
    return _impl()


# ==================== SVIT TOOLS ====================

@mcp.tool()
def list_issues(status: Optional[str] = None, shuttle_id: Optional[str] = None, limit: int = 50) -> List[Dict[str, Any]]:
    """
    List issues in the SVIT system.
    
    Args:
        status: Filter by issue status (NEW, IN_PROGRESS, PENDING_REVIEW, RESOLVED)
        shuttle_id: Filter by shuttle ID
        limit: Maximum number of issues to return (default: 50, max: 100)
    
    Returns:
        List of SVIT issues with their details
    """
    try:
        db = get_svit_db_sync()
        limit_val = min(limit, 100)
        query = select(Issue)
        
        if status:
            query = query.where(Issue.status == status)
        if shuttle_id:
            query = query.where(Issue.shuttle_id == shuttle_id)
            
        query = query.limit(limit_val).order_by(Issue.created_at.desc())
        issues = db.execute(query).scalars().all()
        db.close()
        
        return [{
            "id": i.id,
            "tracking_no": i.tracking_no,
            "shuttle_id": i.shuttle_id,
            "node": i.node,
            "ip_ic": i.ip_ic,
            "family": i.family,
            "issue_phenomenon": i.issue_phenomenon,
            "status": i.status,
            "assignee": i.assignee,
            "reviewer": i.reviewer,
            "creator": i.creator,
            "created_at": i.created_at.isoformat() if i.created_at else None,
            "updated_at": i.updated_at.isoformat() if i.updated_at else None,
            "resolved_at": i.resolved_at.isoformat() if i.resolved_at else None
        } for i in issues]
    except Exception as e:
        return [{"error": f"Failed to list issues: {str(e)}"}]


@mcp.tool()
def get_issue_details(tracking_no: str) -> Dict[str, Any]:
    """
    Get detailed information about a specific SVIT issue.
    
    Args:
        tracking_no: The tracking number of the issue
    
    Returns:
        Detailed issue information
    """
    try:
        db = get_svit_db_sync()
        issue = db.execute(
            select(Issue).where(Issue.tracking_no == tracking_no)
        ).scalar_one_or_none()
        db.close()
        
        if not issue:
            return {"error": f"Issue with tracking_no {tracking_no} not found"}
        
        return {
            "id": issue.id,
            "tracking_no": issue.tracking_no,
            "shuttle_id": issue.shuttle_id,
            "node": issue.node,
            "ip_ic": issue.ip_ic,
            "family": issue.family,
            "issue_phenomenon": issue.issue_phenomenon,
            "status": issue.status,
            "input_v": issue.input_v,
            "frequency": issue.frequency,
            "pattern": issue.pattern,
            "volt": issue.volt,
            "temp": issue.temp,
            "freq": issue.freq,
            "phs": issue.phs,
            "report_date": issue.report_date.isoformat() if issue.report_date else None,
            "expected_root_cause": issue.expected_root_cause,
            "countermeasure": issue.countermeasure,
            "update_note": issue.update_note,
            "resolved_note": issue.resolved_note,
            "assignee": issue.assignee,
            "reviewer": issue.reviewer,
            "creator": issue.creator,
            "created_at": issue.created_at.isoformat() if issue.created_at else None,
            "updated_at": issue.updated_at.isoformat() if issue.updated_at else None,
            "resolved_at": issue.resolved_at.isoformat() if issue.resolved_at else None
        }
    except Exception as e:
        return {"error": f"Failed to get issue details: {str(e)}"}


@mcp.tool()
def list_shuttles(limit: int = 50) -> List[Dict[str, Any]]:
    """
    List shuttles in the SVIT system.
    
    Args:
        limit: Maximum number of shuttles to return (default: 50, max: 100)
    
    Returns:
        List of shuttles with their details
    """
    try:
        db = get_svit_db_sync()
        limit_val = min(limit, 100)
        query = select(Shuttle).limit(limit_val).order_by(Shuttle.created_at.desc())
        shuttles = db.execute(query).scalars().all()
        db.close()
        
        return [{
            "id": s.id,
            "shuttle_id": s.shuttle_id,
            "ip_ic": s.ip_ic,
            "node": s.node,
            "family": s.family,
            "power_1": s.power_1,
            "power_2": s.power_2,
            "power_3": s.power_3,
            "power_4": s.power_4,
            "power_5": s.power_5,
            "power_6": s.power_6,
            "power_7": s.power_7,
            "created_at": s.created_at.isoformat() if s.created_at else None,
            "updated_at": s.updated_at.isoformat() if s.updated_at else None
        } for s in shuttles]
    except Exception as e:
        return [{"error": f"Failed to list shuttles: {str(e)}"}]


# ==================== RPMT TOOLS ====================

@mcp.tool()
def list_rpmt_projects(active_only: bool = True, limit: int = 50) -> List[Dict[str, Any]]:
    """
    List RPMT (Risk & Project Management) projects.
    
    Args:
        active_only: If True, only return active projects (default: True)
        limit: Maximum number of projects to return (default: 50, max: 100)
    
    Returns:
        List of RPMT projects with their details
    """
    try:
        db = get_rpmt_db_sync()
        limit_val = min(limit, 100)
        query = select(RPMTProject)
        
        if active_only:
            query = query.where(RPMTProject.active == True)
            
        query = query.limit(limit_val).order_by(RPMTProject.created_at.desc())
        projects = db.execute(query).scalars().all()
        db.close()
        
        return [{
            "id": p.id,
            "code": p.code,
            "process": p.process,
            "metal_option": p.metal_option,
            "ip_code": p.ip_code,
            "pdk_ver": p.pdk_ver,
            "active": p.active,
            "created_at": p.created_at.isoformat() if p.created_at else None
        } for p in projects]
    except Exception as e:
        return [{"error": f"Failed to list RPMT projects: {str(e)}"}]


@mcp.tool()
def list_rpmt_tasks(project_code: Optional[str] = None, status: Optional[str] = None, limit: int = 50) -> List[Dict[str, Any]]:
    """
    List RPMT tasks with optional filtering.
    
    Args:
        project_code: Filter by project code (optional)
        status: Filter by task status (Complete, In-progress, Not Started, N/A)
        limit: Maximum number of tasks to return (default: 50, max: 100)
    
    Returns:
        List of RPMT tasks with their details
    """
    try:
        db = get_rpmt_db_sync()
        limit_val = min(limit, 100)
        query = select(RPMTTask).where(RPMTTask.archived == False)
        
        if project_code:
            project = db.execute(
                select(RPMTProject).where(RPMTProject.code == project_code)
            ).scalar_one_or_none()
            if project:
                query = query.where(RPMTTask.project_id == project.id)
        
        if status:
            query = query.where(RPMTTask.status == status)
        
        query = query.limit(limit_val).order_by(RPMTTask.updated_at.desc())
        tasks = db.execute(query).scalars().all()
        db.close()
        
        return [{
            "id": t.id,
            "project_code": t.project.code if t.project else "N/A",
            "cat1": t.cat1,
            "cat2": t.cat2,
            "dept_from": t.dept_from,
            "dept_to": t.dept_to,
            "status": t.status.value if hasattr(t.status, 'value') else str(t.status),
            "due_date": t.due_date.isoformat() if t.due_date else None,
            "reason": t.reason,
            "updated_at": t.updated_at.isoformat() if t.updated_at else None
        } for t in tasks]
    except Exception as e:
        return [{"error": f"Failed to list RPMT tasks: {str(e)}"}]


@mcp.tool()
def get_pdk_dk_entries(project_code: Optional[str] = None, limit: int = 20) -> List[Dict[str, Any]]:
    """
    List PDK/DK entries for verification tracking.
    
    Args:
        project_code: Filter by project code (optional)
        limit: Maximum number of entries to return (default: 20, max: 100)
    
    Returns:
        List of PDK/DK entries
    """
    try:
        db = get_rpmt_db_sync()
        limit_val = min(limit, 100)
        query = select(PDKDKEntry)
        
        if project_code:
            project = db.execute(
                select(RPMTProject).where(RPMTProject.code == project_code)
            ).scalar_one_or_none()
            if project:
                query = query.where(PDKDKEntry.project_id == project.id)
        
        query = query.limit(limit_val).order_by(PDKDKEntry.updated_at.desc())
        entries = db.execute(query).scalars().all()
        db.close()
        
        return [{
            "id": e.id,
            "project_code": e.project.code if e.project else "N/A",
            "type": e.type,
            "category": e.category,
            "engineer_version_kickoff": e.engineer_version_kickoff,
            "qa_version_kickoff": e.qa_version_kickoff,
            "updated_at": e.updated_at.isoformat() if e.updated_at else None
        } for e in entries]
    except Exception as e:
        return [{"error": f"Failed to list PDK/DK entries: {str(e)}"}]


# ==================== CITS TOOLS ====================

@mcp.tool()
def list_customers(active_only: bool = True, limit: int = 50) -> List[Dict[str, Any]]:
    """
    List customers in the CITS (Configuration Item Tracking System).
    
    Args:
        active_only: If True, only return active customers (default: True)
        limit: Maximum number of customers to return (default: 50, max: 100)
    
    Returns:
        List of customers with their details
    """
    try:
        db = get_customer_db_sync()
        limit_val = min(limit, 100)
        query = select(Customer)
        
        if active_only:
            query = query.where(Customer.is_active == True)
        
        query = query.limit(limit_val).order_by(Customer.created_at.desc())
        customers = db.execute(query).scalars().all()
        db.close()
        
        return [{
            "id": c.id,
            "name": c.name,
            "company": c.company,
            "email": c.email,
            "is_active": c.is_active,
            "created_at": c.created_at.isoformat() if c.created_at else None
        } for c in customers]
    except Exception as e:
        return [{"error": f"Failed to list customers: {str(e)}"}]


@mcp.tool()
def list_customer_issues(status: Optional[str] = None, limit: int = 50) -> List[Dict[str, Any]]:
    """
    List customer issues from CITS.
    
    Args:
        status: Filter by status (OPEN, PENDING, CLOSE)
        limit: Maximum number of issues to return (default: 50, max: 100)
    
    Returns:
        List of customer issues
    """
    try:
        db = get_customer_db_sync()
        limit_val = min(limit, 100)
        query = select(CustomerIssue)
        
        if status:
            query = query.where(CustomerIssue.status == status)
        
        query = query.limit(limit_val).order_by(CustomerIssue.created_at.desc())
        issues = db.execute(query).scalars().all()
        db.close()
        
        return [{
            "id": i.id,
            "ticket_no": i.ticket_no,
            "title": i.title,
            "description": i.description[:100] if i.description else None,
            "status": i.status,
            "tag": i.tag,
            "customer": i.customer,
            "ip_ic": i.ip_ic,
            "priority": i.priority,
            "assignee": i.assignee,
            "created_at": i.created_at.isoformat() if i.created_at else None
        } for i in issues]
    except Exception as e:
        return [{"error": f"Failed to list customer issues: {str(e)}"}]


@mcp.tool()
def get_issue_conversations(ticket_no: str) -> Dict[str, Any]:
    """
    Get conversation history for a customer issue.
    
    Args:
        ticket_no: The ticket number of the issue
    
    Returns:
        Issue details with conversation history
    """
    try:
        db = get_customer_db_sync()
        issue = db.execute(
            select(CustomerIssue).where(CustomerIssue.ticket_no == ticket_no)
        ).scalar_one_or_none()
        
        if not issue:
            return {"error": f"Issue with ticket_no {ticket_no} not found"}
        
        # Get conversations for this issue
        conversations = db.execute(
            select(IssueConversation).where(IssueConversation.issue_id == issue.id)
            .order_by(IssueConversation.created_at.desc())
        ).scalars().all()
        db.close()
        
        return {
            "ticket_no": issue.ticket_no,
            "title": issue.title,
            "status": issue.status,
            "assignee": issue.assignee,
            "conversation_count": len(conversations),
            "conversations": [{
                "type": c.type,
                "content": c.content[:150],
                "created_by": c.created_by,
                "created_at": c.created_at.isoformat() if c.created_at else None
            } for c in conversations[:10]]
        }
    except Exception as e:
        return {"error": f"Failed to get issue conversations: {str(e)}"}


# ==================== SPEC-CENTER TOOLS ====================

@mcp.tool()
def list_spec_categories(parent_only: bool = False, limit: int = 50) -> List[Dict[str, Any]]:
    """
    List specification categories (hierarchical).
    
    Args:
        parent_only: If True, only return top-level categories (default: False)
        limit: Maximum number of categories to return (default: 50, max: 100)
    
    Returns:
        List of specification categories
    """
    try:
        db = get_spec_db_sync()
        limit_val = min(limit, 100)
        query = select(SpecCategory).where(SpecCategory.is_active == True)
        
        if parent_only:
            query = query.where(SpecCategory.parent_id == None)
        
        query = query.limit(limit_val).order_by(SpecCategory.order, SpecCategory.name)
        categories = db.execute(query).scalars().all()
        db.close()
        
        return [{
            "id": c.id,
            "name": c.name,
            "description": c.description,
            "parent_id": c.parent_id,
            "icon": c.icon,
            "order": c.order,
            "created_at": c.created_at.isoformat() if c.created_at else None
        } for c in categories]
    except Exception as e:
        return [{"error": f"Failed to list spec categories: {str(e)}"}]


@mcp.tool()
def list_spec_files(category_id: Optional[int] = None, limit: int = 50) -> List[Dict[str, Any]]:
    """
    List specification files.
    
    Args:
        category_id: Filter by category ID (optional)
        limit: Maximum number of files to return (default: 50, max: 100)
    
    Returns:
        List of specification files
    """
    try:
        db = get_spec_db_sync()
        limit_val = min(limit, 100)
        query = select(SpecFile).where(SpecFile.is_active == True)
        
        if category_id:
            query = query.where(SpecFile.category_id == category_id)
        
        query = query.limit(limit_val).order_by(SpecFile.order, SpecFile.created_at.desc())
        files = db.execute(query).scalars().all()
        db.close()
        
        return [{
            "id": f.id,
            "filename": f.filename,
            "original_name": f.original_name,
            "category_id": f.category_id,
            "file_size": f.file_size,
            "file_type": f.file_type,
            "description": f.description,
            "uploaded_by": f.uploaded_by,
            "created_at": f.created_at.isoformat() if f.created_at else None
        } for f in files]
    except Exception as e:
        return [{"error": f"Failed to list spec files: {str(e)}"}]


@mcp.tool()
def search_spec_content(keyword: str, limit: int = 5) -> List[Dict[str, Any]]:
    """
    Search for specification content by keyword.
    Searches across document titles, keywords, and content.
    
    Args:
        keyword: Search keyword (e.g., "ISO26262", "AEC-Q100", "functional safety")
        limit: Maximum number of results to return (default: 5, max: 20)
    
    Returns:
        List of matching specification documents with preview content
    """
    try:
        from modules.spec_center.parser import SpecCenterParser
        
        parser = SpecCenterParser(spec_center_path="uploads/spec_center")
        
        # Try to load from index first, if not available parse
        if not parser.documents:
            if not parser.load_index(".spec_center_index.json"):
                parser.parse_all_documents()
        
        # Search by keyword
        results = parser.get_document_by_keyword(keyword)
        
        limit_val = min(limit, 20)
        
        return [{
            "file_name": r["file_name"],
            "file_path": r["file_path"],
            "file_size": r["file_size"],
            "keywords": r["keywords"],
            "preview": r["content_preview"][:300],
            "content": r.get("full_content", "")[:2000]
        } for r in results[:limit_val]]
    except Exception as e:
        return [{"error": f"Failed to search spec content: {str(e)}"}]




@mcp.resource("qms://projects/list")
def get_projects_resource() -> str:
    """Get a list of all active projects as a formatted resource"""
    projects = list_projects(active_only=True)
    
    output = "# QMS Active Projects\n\n"
    for p in projects:
        output += f"## Project: {p['code']}\n"
        output += f"- ID: {p['id']}\n"
        output += f"- Process: {p['process']}\n"
        output += f"- IP Code: {p['ip_code']}\n"
        output += f"- PDK Version: {p['pdk_ver']}\n"
        output += f"- Created: {p['created_at']}\n\n"
    
    return output


@mcp.resource("qms://projects/{project_id}")
def get_project_resource(project_id: int) -> str:
    """Get detailed information about a specific project"""
    details = get_project_details(project_id)
    
    if "error" in details:
        return f"Error: {details['error']}"
    
    output = f"# Project: {details['code']}\n\n"
    output += f"- ID: {details['id']}\n"
    output += f"- Process: {details['process']}\n"
    output += f"- Metal Option: {details['metal_option']}\n"
    output += f"- IP Code: {details['ip_code']}\n"
    output += f"- PDK Version: {details['pdk_ver']}\n"
    output += f"- Active: {details['active']}\n"
    output += f"- Created: {details['created_at']}\n\n"
    
    stats = details['task_statistics']
    output += "## Task Statistics\n"
    output += f"- Total Tasks: {stats['total']}\n"
    output += f"- Complete: {stats['complete']}\n"
    output += f"- In Progress: {stats['in_progress']}\n"
    output += f"- Not Started: {stats['not_started']}\n"
    output += f"- N/A: {stats['na']}\n"
    
    return output


@mcp.resource("qms://summary")
def get_summary_resource() -> str:
    """Get a summary of the entire QMS system"""
    summary = get_project_summary()
    
    output = "# QMS System Summary\n\n"
    output += f"## Projects\n"
    output += f"- Total Projects: {summary['total_projects']}\n"
    output += f"- Active Projects: {summary['active_projects']}\n"
    output += f"- Inactive Projects: {summary['inactive_projects']}\n\n"
    
    output += f"## Tasks\n"
    output += f"- Total Tasks: {summary['total_tasks']}\n"
    dist = summary['task_status_distribution']
    output += f"- Complete: {dist['complete']}\n"
    output += f"- In Progress: {dist['in_progress']}\n"
    output += f"- Not Started: {dist['not_started']}\n"
    output += f"- N/A: {dist['na']}\n"
    
    return output


# ==================== PROMPTS ====================

@mcp.prompt()
def analyze_project_status(project_code: str) -> str:
    """Generate a prompt for analyzing project status"""
    return f"""Please analyze the status of project '{project_code}' in the QMS system.

Use the following tools to gather information:
1. Use list_projects() to find the project ID
2. Use get_project_details() to get detailed information
3. Use list_tasks() with the project_id to see all tasks

Provide a comprehensive analysis including:
- Overall project progress
- Task completion rate
- Any blocked or delayed tasks
- Recommendations for improvement
"""


@mcp.prompt()
def generate_project_report(project_id: int, style: str = "formal") -> str:
    """Generate a prompt for creating a project report"""
    styles = {
        "formal": "formal, professional tone suitable for management",
        "technical": "technical, detailed analysis with metrics",
        "summary": "brief executive summary highlighting key points"
    }
    
    style_desc = styles.get(style, styles["formal"])
    
    return f"""Please generate a {style_desc} report for project ID {project_id}.

Use the following tools:
1. get_project_details({project_id}) - Get project information
2. list_tasks(project_id={project_id}) - Get all tasks for this project

Structure the report with:
- Project Overview
- Current Status
- Task Breakdown
- Timeline and Milestones
- Risk Assessment
- Next Steps
"""


@mcp.prompt()
def suggest_task_prioritization() -> str:
    """Generate a prompt for task prioritization suggestions"""
    return """Please analyze all tasks in the QMS system and provide prioritization recommendations.

Use these tools:
1. list_tasks() to get all tasks
2. get_project_summary() to understand the overall system status

Provide recommendations for:
- High-priority tasks that are overdue or at risk
- Tasks that can be parallelized
- Resource allocation suggestions
- Dependencies and blockers
"""


def run_mcp_server(transport: str = "stdio"):
    """
    Run the MCP server
    
    Args:
        transport: Transport type ("stdio", "http", or "streamable-http")
    """
    mcp.run(transport=transport)


if __name__ == "__main__":
    run_mcp_server()
