"""
MCP Routes for FastAPI Integration

This module provides FastAPI routes for integrating the MCP server
with the main QMS FastAPI application.
"""
import json
from fastapi import APIRouter, Request, Depends, HTTPException
from fastapi.responses import JSONResponse, StreamingResponse
from sqlalchemy.orm import Session
from typing import Dict, Any

from core.db import get_db
from modules.mcp.server import (
    list_projects,
    get_project_details,
    list_tasks,
    get_task_details,
    get_project_summary,
    list_users
)


router = APIRouter()


def _require_admin(request: Request):
    """Require user to be admin (role==Admin or email in GARAGE_ADMIN_EMAILS)."""
    sess = getattr(request, 'session', None)
    if not sess or not sess.get('is_authenticated'):
        raise HTTPException(status_code=401, detail='Authentication required')
    email = sess.get('email', '')
    role = sess.get('role', '')

    # Import GARAGE_ADMIN_EMAILS with fallback so this works when app is run as top-level module
    GARAGE_ADMIN_EMAILS = []
    try:
        from ...core.config import GARAGE_ADMIN_EMAILS as _GARAGE_ADMIN_EMAILS
    except Exception:
        try:
            from core.config import GARAGE_ADMIN_EMAILS as _GARAGE_ADMIN_EMAILS
        except Exception:
            _GARAGE_ADMIN_EMAILS = None
    if _GARAGE_ADMIN_EMAILS is not None:
        GARAGE_ADMIN_EMAILS = _GARAGE_ADMIN_EMAILS

    if (role and role.lower() == 'admin') or (email and email.lower() in GARAGE_ADMIN_EMAILS):
        return

    # Not admin
    raise HTTPException(status_code=403, detail='Admin access required')


@router.get("/mcp/health")
def mcp_health_check(request: Request) -> Dict[str, Any]:
    """Health check endpoint for MCP server (admin-only)"""
    _require_admin(request)
    return {
        "status": "healthy",
        "service": "QMS MCP Server",
        "version": "1.0.0"
    }


@router.get("/mcp/tools")
def list_mcp_tools(request: Request) -> Dict[str, Any]:
    """List all available MCP tools (admin-only)"""
    _require_admin(request)
    return {
        "tools": [
            {
                "name": "list_projects",
                "description": "List all projects in the QMS system",
                "parameters": ["active_only", "limit"]
            },
            {
                "name": "get_project_details",
                "description": "Get detailed information about a specific project",
                "parameters": ["project_id"]
            },
            {
                "name": "list_tasks",
                "description": "List tasks in the QMS system",
                "parameters": ["project_id", "status", "limit"]
            },
            {
                "name": "get_task_details",
                "description": "Get detailed information about a specific task",
                "parameters": ["task_id"]
            },
            {
                "name": "get_project_summary",
                "description": "Get a summary of all projects in the system",
                "parameters": []
            },
            {
                "name": "list_users",
                "description": "List users in the QMS system",
                "parameters": ["active_only", "limit"]
            }
        ]
    }


@router.get("/mcp/resources")
def list_mcp_resources(request: Request) -> Dict[str, Any]:
    """List all available MCP resources (admin-only)"""
    _require_admin(request)
    return {
        "resources": [
            {
                "uri": "qms://projects/list",
                "description": "Get a list of all active projects"
            },
            {
                "uri": "qms://projects/{project_id}",
                "description": "Get detailed information about a specific project"
            },
            {
                "uri": "qms://summary",
                "description": "Get a summary of the entire QMS system"
            }
        ]
    }


@router.get("/mcp/prompts")
def list_mcp_prompts(request: Request) -> Dict[str, Any]:
    """List all available MCP prompts (admin-only)"""
    _require_admin(request)
    return {
        "prompts": [
            {
                "name": "analyze_project_status",
                "description": "Analyze the status and progress of a specific project",
                "arguments": [
                    {
                        "name": "project_id",
                        "description": "The ID of the project to analyze",
                        "required": True
                    }
                ]
            },
            {
                "name": "generate_project_report",
                "description": "Generate a comprehensive report for a project",
                "arguments": [
                    {
                        "name": "project_id",
                        "description": "The ID of the project to report on",
                        "required": True
                    }
                ]
            },
            {
                "name": "suggest_task_prioritization",
                "description": "Suggest task prioritization for better project management",
                "arguments": [
                    {
                        "name": "project_id",
                        "description": "The ID of the project (optional, for all projects if not provided)",
                        "required": False
                    }
                ]
            }
        ]
    }


@router.post("/mcp/invoke/{tool_name}")
async def invoke_mcp_tool(
    tool_name: str,
    request: Request,
    db: Session = Depends(get_db)
) -> Dict[str, Any]:
    _require_admin(request)
    """
    Invoke an MCP tool with parameters
    
    Args:
        tool_name: Name of the tool to invoke
        request: FastAPI request containing JSON body with tool parameters
    
    Returns:
        Result of the tool invocation
    """
    try:
        params = await request.json()
    except json.JSONDecodeError:
        params = {}
    except Exception as e:
        raise HTTPException(status_code=400, detail=f"Invalid JSON: {str(e)}")
    
    tool_mapping = {
        "list_projects": list_projects,
        "get_project_details": get_project_details,
        "list_tasks": list_tasks,
        "get_task_details": get_task_details,
        "get_project_summary": get_project_summary,
        "list_users": list_users
    }
    
    if tool_name not in tool_mapping:
        raise HTTPException(status_code=404, detail=f"Tool '{tool_name}' not found")
    
    try:
        result = tool_mapping[tool_name](**params)
        return {
            "success": True,
            "tool": tool_name,
            "result": result
        }
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error invoking tool: {str(e)}")


@router.get("/api/mcp/info")
def get_mcp_info(request: Request) -> Dict[str, Any]:
    """Get information about the MCP integration (admin-only)"""
    _require_admin(request)
    return {
        "name": "QMS MCP Server",
        "version": "1.0.0",
        "description": "Model Context Protocol server for QMS (Quality Management System)",
        "features": [
            "Project management tools",
            "Task tracking tools",
            "User management tools",
            "System summary resources",
            "LLM-friendly prompts"
        ],
        "endpoints": {
            "health": "/mcp/health",
            "tools": "/mcp/tools",
            "resources": "/mcp/resources",
            "invoke": "/mcp/invoke/{tool_name}",
            "info": "/api/mcp/info"
        }
    }
