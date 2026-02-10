"""
GPT4All Chat API Routes with RAG Support

This module provides REST API endpoints for interacting with the local GPT4All LLM.
It includes RAG (Retrieval Augmented Generation) capabilities for context-aware responses.
"""
import os
from fastapi import APIRouter, HTTPException, Request
from fastapi.responses import RedirectResponse
from pydantic import BaseModel
from typing import Optional, Dict, Any, List
import json

from modules.mcp.gpt4all_client import QMSAssistant, GPT4ALL_AVAILABLE

try:
    from modules.mcp.rag_retriever import RAGRetriever
    from modules.mcp.rag_indexer import RAGIndexer
    RAG_AVAILABLE = True
except ImportError:
    RAG_AVAILABLE = False


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

# Global assistant and RAG instances (singletons)
_assistant_instance = None
_rag_retriever_instance = None


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
        model_path = os.environ.get('GPT4ALL_MODEL_PATH', r'/home/ronnie/LLM/models')
        model_name = os.environ.get('GPT4ALL_MODEL_NAME', 'Meta-Llama-3-8B-Instruct.Q5_K_M')
        
        print(f"Initializing QMSAssistant with model_path={model_path}, model_name={model_name}")
        _assistant_instance = QMSAssistant(model_name=model_name, model_path=model_path, enable_rag=True)
        _assistant_instance.load_model()
    return _assistant_instance


def get_rag_retriever() -> Optional['RAGRetriever']:
    """Get or create the RAG retriever instance"""
    global _rag_retriever_instance
    if _rag_retriever_instance is None and RAG_AVAILABLE:
        try:
            indexer = RAGIndexer()
            _rag_retriever_instance = RAGRetriever(indexer=indexer)
        except Exception as e:
            print(f"Warning: Failed to initialize RAG retriever: {e}")
    return _rag_retriever_instance


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
    Chat with the local GPT4All LLM about QMS data (ADMIN ONLY)
    
    Args:
        payload: Chat request with message and optional reset flag
        request: The HTTP request object
    
    Returns:
        Response from the assistant
    """
    try:
        _require_admin(request)
        import time
        import signal
        import threading
        
        assistant = get_assistant()
        
        if payload.reset:
            assistant.reset_conversation()
        
        print(f"\n[GPT4All] Received message: {payload.message[:100]}...")
        start_time = time.time()
        
        # Set timeout - max 30 seconds for response
        MAX_RESPONSE_TIME = 30
        response_container = [None]
        error_container = [None]
        
        def generate_response():
            try:
                response_container[0] = assistant.chat(payload.message, max_tokens=64)
            except Exception as e:
                error_container[0] = e
        
        # Run response generation in thread with timeout
        response_thread = threading.Thread(target=generate_response, daemon=True)
        response_thread.start()
        response_thread.join(timeout=MAX_RESPONSE_TIME)
        
        if response_thread.is_alive():
            # Timeout occurred
            elapsed = time.time() - start_time
            print(f"[GPT4All] TIMEOUT: Response took longer than {MAX_RESPONSE_TIME}s (elapsed: {elapsed:.2f}s)")
            return ChatResponse(
                response="응답 생성 시간 초과 (30초). 서버 모델 성능을 확인해주세요.",
                success=False
            )
        
        if error_container[0]:
            raise error_container[0]
        
        response = response_container[0] or ""
        
        # Limit response length
        if len(response) > 2000:
            response = response[:2000] + "...[응답이 너무 길어서 자름]"
        
        elapsed = time.time() - start_time
        print(f"[GPT4All] Response generated in {elapsed:.2f}s: {response[:100]}...")
        
        return ChatResponse(response=response, success=True)
    
    except HTTPException:
        raise
    except Exception as e:
        print(f"[GPT4All] Error: {str(e)}")
        import traceback
        traceback.print_exc()
        raise HTTPException(status_code=500, detail=str(e))

@router.post("/gpt4all/reset")
def reset_conversation(request: Request) -> Dict[str, str]:
    """Reset the conversation history (ADMIN ONLY)"""
    try:
        _require_admin(request)
        assistant = get_assistant()
        assistant.reset_conversation()
        return {"message": "Conversation history cleared"}
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


# ==================== RAG ENDPOINTS ====================

class RAGSearchRequest(BaseModel):
    """Request model for RAG search"""
    query: str
    limit: int = 5


class RAGSearchResult(BaseModel):
    """Result model for RAG search"""
    file_path: str
    file_name: str
    summary: str
    content: str
    keywords: List[str]
    score: int


@router.post("/gpt4all/rag/search")
def rag_search(payload: RAGSearchRequest, request: Request) -> Dict[str, Any]:
    """Search the RAG knowledge base (admin-only)
    
    Args:
        payload: Search request with query and limit
        request: HTTP request object
    
    Returns:
        Search results with documents and scores
    """
    try:
        _require_admin(request)
        
        if not RAG_AVAILABLE:
            raise HTTPException(
                status_code=503,
                detail="RAG system is not available"
            )
        
        retriever = get_rag_retriever()
        if not retriever:
            raise HTTPException(
                status_code=503,
                detail="RAG system initialization failed"
            )
        
        results = retriever.retrieve(payload.query, limit=payload.limit)
        
        return {
            "query": payload.query,
            "results": results,
            "count": len(results)
        }
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/gpt4all/rag/index")
def rag_index_project(request: Request) -> Dict[str, Any]:
    """Index the entire QMS project for RAG (admin-only)
    
    This endpoint triggers a full re-indexing of the project.
    Warning: This may take a while with large projects.
    
    Args:
        request: HTTP request object
    
    Returns:
        Indexing statistics
    """
    try:
        _require_admin(request)
        
        if not RAG_AVAILABLE:
            raise HTTPException(
                status_code=503,
                detail="RAG system is not available"
            )
        
        indexer = RAGIndexer()
        print("Starting project indexing...")
        counts = indexer.index_project()
        stats = indexer.get_stats()
        
        return {
            "success": True,
            "message": "Project indexed successfully",
            "indexed_counts": counts,
            "statistics": stats
        }
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/gpt4all/rag/stats")
def rag_stats(request: Request) -> Dict[str, Any]:
    """Get RAG system statistics (admin-only)
    
    Args:
        request: HTTP request object
    
    Returns:
        RAG system statistics
    """
    try:
        _require_admin(request)
        
        if not RAG_AVAILABLE:
            raise HTTPException(
                status_code=503,
                detail="RAG system is not available"
            )
        
        retriever = get_rag_retriever()
        if not retriever:
            raise HTTPException(
                status_code=503,
                detail="RAG system not initialized"
            )
        
        stats = retriever.get_stats()
        return stats
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/gpt4all/chat/with-context")
def chat_with_context(payload: ChatRequest, request: Request) -> ChatResponse:
    """Chat with explicit RAG context retrieval (admin-only)
    
    Args:
        payload: Chat request
        request: HTTP request object
    
    Returns:
        Chat response with RAG context
    """
    try:
        _require_admin(request)
        assistant = get_assistant()
        
        if payload.reset:
            assistant.reset_conversation()
        
        # Force RAG context retrieval
        response = assistant.chat(payload.message, use_rag=True)
        
        return ChatResponse(response=response, success=True)
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/gpt4all/chat/no-context")
def chat_without_context(payload: ChatRequest, request: Request) -> ChatResponse:
    """Chat without RAG context (admin-only)
    
    Args:
        payload: Chat request
        request: HTTP request object
    
    Returns:
        Chat response without RAG context
    """
    try:
        _require_admin(request)
        assistant = get_assistant()
        
        if payload.reset:
            assistant.reset_conversation()
        
        # Disable RAG context
        response = assistant.chat(payload.message, use_rag=False)
        
        return ChatResponse(response=response, success=True)
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/gpt4all/status-extended")
def gpt4all_status_extended(request: Request) -> Dict[str, Any]:
    """Get extended GPT4All status including RAG info (admin-only)
    
    Args:
        request: HTTP request object
    
    Returns:
        Extended status information
    """
    try:
        _require_admin(request)
        
        status = {
            "gpt4all": {
                "available": GPT4ALL_AVAILABLE,
                "loaded": _assistant_instance is not None,
                "model": _assistant_instance.model_name if _assistant_instance else None
            },
            "rag": {
                "available": RAG_AVAILABLE,
                "enabled": _assistant_instance.enable_rag if _assistant_instance else False
            }
        }
        
        if RAG_AVAILABLE:
            retriever = get_rag_retriever()
            if retriever:
                stats = retriever.get_stats()
                status["rag_stats"] = stats
        
        return status
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

# ==================== TEST ENDPOINTS (NO AUTH) ====================

@router.post("/gpt4all/chat/test")
def chat_test(payload: ChatRequest) -> ChatResponse:
    """Test chat endpoint without authentication
    
    WARNING: This endpoint is for testing only and should not be used in production.
    Remove this endpoint after testing performance.
    
    Args:
        payload: Chat request with message
    
    Returns:
        Chat response
    """
    try:
        import time
        import threading
        
        assistant = get_assistant()
        
        if payload.reset:
            assistant.reset_conversation()
        
        print(f"\n[Test] Starting chat: {payload.message[:50]}")
        start = time.time()
        
        # Use default max_tokens=128
        response_container = [None]
        error_container = [None]
        
        def generate():
            try:
                step1 = time.time()
                response_container[0] = assistant.chat(payload.message)
                step2 = time.time()
                print(f"[Test] Chat time: {step2-step1:.2f}s")
            except Exception as e:
                error_container[0] = e
        
        response_thread = threading.Thread(target=generate, daemon=True)
        response_thread.start()
        response_thread.join(timeout=60)
        
        if response_thread.is_alive():
            print("[Test] TIMEOUT after 60s")
            return ChatResponse(response="Timeout", success=False)
        
        if error_container[0]:
            raise error_container[0]
        
        elapsed = time.time() - start
        print(f"[Test] Total time: {elapsed:.2f}s")
        
        return ChatResponse(response=response_container[0] or "", success=True)
    except Exception as e:
        print(f"[Test] Error: {e}")
        raise HTTPException(status_code=500, detail=str(e))