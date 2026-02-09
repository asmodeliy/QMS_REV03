"""
GPT4All Chat API Routes

This module provides REST API endpoints for interacting with the local GPT4All LLM.
"""
import os
from fastapi import APIRouter, HTTPException, Request
from fastapi.responses import RedirectResponse
from pydantic import BaseModel
from typing import Optional, Dict, Any
import json

from modules.mcp.gpt4all_client import QMSAssistant, GPT4ALL_AVAILABLE


router = APIRouter()


def _require_admin(request: 'Request'):
    sess = getattr(request, 'session', None)
    # Debug: log session contents to help diagnose cross-request/session issues
    try:
        from ...core.logger import app_logger
    except Exception:
        app_logger = None

    if app_logger:
        try:
            app_logger.debug("_require_admin: session=%s", dict(sess) if sess else sess)
        except Exception:
            app_logger.debug("_require_admin: session (unserializable)")
    else:
        try:
            print(f"_require_admin: session={dict(sess) if sess else sess}")
        except Exception:
            print("_require_admin: session (unserializable)")

    if not sess or not sess.get('is_authenticated'):
        if app_logger:
            app_logger.warning("Authentication required in _require_admin", {"session": dict(sess) if sess else None})
        raise HTTPException(status_code=401, detail='Authentication required')

    email = sess.get('email', '')
    role = sess.get('role', '')

    # Import GARAGE_ADMIN_EMAILS with a fallback so this works when app is run as top-level module
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

    if app_logger:
        app_logger.debug("_require_admin: role=%s, email=%s, GARAGE_ADMIN_EMAILS=%s", role, email, GARAGE_ADMIN_EMAILS)
    else:
        print(f"_require_admin: role={role}, email={email}, GARAGE_ADMIN_EMAILS={GARAGE_ADMIN_EMAILS}")

    if (role and role.lower() == 'admin') or (email and email.lower() in GARAGE_ADMIN_EMAILS):
        return

    if app_logger:
        try:
            app_logger.warning("Admin access required in _require_admin", {"session": dict(sess)})
        except Exception:
            app_logger.warning("Admin access required in _require_admin (unserializable session)")
    raise HTTPException(status_code=403, detail='Admin access required')

# Global assistant instance (singleton)
_assistant_instance = None


def get_assistant() -> QMSAssistant:
    """Get or create the assistant instance"""
    global _assistant_instance
    if _assistant_instance is None:
        if not GPT4ALL_AVAILABLE:
            raise HTTPException(
                status_code=503,
                detail="GPT4All is not installed. Install with: pip install gpt4all"
            )
        
        # Get model path from environment variable
        model_path = os.environ.get('GPT4ALL_MODEL_PATH', '/home/ronnie/llm/models')
        model_name = os.environ.get('GPT4ALL_MODEL_NAME', 'Meta-Llama-3-8B-Instruct.Q4_0.gguf')
        
        print(f"Initializing QMSAssistant with model_path={model_path}, model_name={model_name}")
        _assistant_instance = QMSAssistant(model_name=model_name, model_path=model_path)
        _assistant_instance.load_model()
    return _assistant_instance


class ChatRequest(BaseModel):
    """Request model for chat endpoint"""
    message: str
    reset: bool = False


class ChatResponse(BaseModel):
    """Response model for chat endpoint"""
    response: str
    success: bool = True


@router.get("/gpt4all")
def gpt4all_root(request: Request):
    """Browser-friendly root for GPT4All.

    Redirects admins to the UI page; returns 403 for non-admin attempts.
    """
    _require_admin(request)
    return RedirectResponse(url="/ai-chat", status_code=303)


@router.get("/gpt4all/status")
def gpt4all_status(request: Request) -> Dict[str, Any]:
    """Check if GPT4All is available and ready (admin-only)"""
    _require_admin(request)
    return {
        "available": GPT4ALL_AVAILABLE,
        "loaded": _assistant_instance is not None,
        "model": _assistant_instance.model_name if _assistant_instance else None
    }


@router.post("/gpt4all/chat", response_model=ChatResponse)
def chat_with_gpt4all(payload: ChatRequest, request: Request) -> ChatResponse:
    """
    Chat with the local GPT4All LLM about QMS data (admin-only)
    
    Args:
        payload: Chat request with message and optional reset flag
        request: The HTTP request object (used to check session/admin)
    
    Returns:
        Response from the assistant
    """
    try:
        _require_admin(request)
        assistant = get_assistant()
        
        if payload.reset:
            assistant.reset_conversation()
        
        response = assistant.chat(payload.message)
        
        return ChatResponse(response=response, success=True)
    
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/gpt4all/reset")
def reset_conversation(request: Request) -> Dict[str, str]:
    """Reset the conversation history (admin-only)"""
    try:
        _require_admin(request)
        assistant = get_assistant()
        assistant.reset_conversation()
        return {"message": "Conversation history cleared"}
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/gpt4all/quick/projects")
def quick_projects(request: Request) -> ChatResponse:
    """Quick endpoint to ask about projects (admin-only)"""
    try:
        _require_admin(request)
        assistant = get_assistant()
        response = assistant.ask_about_projects()
        return ChatResponse(response=response, success=True)
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/gpt4all/quick/tasks")
def quick_tasks(request: Request) -> ChatResponse:
    """Quick endpoint to ask about tasks (admin-only)"""
    try:
        _require_admin(request)
        assistant = get_assistant()
        response = assistant.ask_about_tasks()
        return ChatResponse(response=response, success=True)
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/gpt4all/quick/summary")
def quick_summary(request: Request) -> ChatResponse:
    """Quick endpoint to get system summary (admin-only)"""
    try:
        _require_admin(request)
        assistant = get_assistant()
        response = assistant.ask_for_summary()
        return ChatResponse(response=response, success=True)
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
