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


# ==================== RESOURCES ====================

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
