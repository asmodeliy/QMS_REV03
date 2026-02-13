import logging
import time
from fastapi import Request
from starlette.middleware.base import BaseHTTPMiddleware
from core.activity_logger import get_activity_logger, ActionType
from core.utils import get_client_ip

logger = logging.getLogger("rpmt")


def _get_app_logger():
    try:
        from core.logger import app_logger
        return app_logger
    except Exception:
                                                                       
        l = logging.getLogger('app')
        class _Fallback:
            def __init__(self, l):
                self._l = l
            def debug(self, msg, ctx=None):
                self._l.debug(f"{msg} {ctx}")
            def info(self, msg, ctx=None):
                self._l.info(f"{msg} {ctx}")
            def warning(self, msg, ctx=None):
                self._l.warning(f"{msg} {ctx}")
            def error(self, msg, ctx=None):
                self._l.error(f"{msg} {ctx}")
        return _Fallback(l)


class RequestLoggingMiddleware(BaseHTTPMiddleware):
    async def dispatch(self, request: Request, call_next):
        start_time = time.time()
        
        user_email = request.session.get("email", "anonymous") if hasattr(request, "session") else "anonymous"
        
        response = await call_next(request)
        process_time = time.time() - start_time

        context = {
            "method": request.method,
            "path": request.url.path,
            "user": user_email,
            "ip": request.client.host if request.client else "unknown",
            "status_code": response.status_code,
            "duration_ms": round(process_time * 1000, 2)
        }
        app_logger = _get_app_logger()
        if 200 <= response.status_code < 300:
            app_logger.debug(f"{request.method} {request.url.path}", context)
        elif 300 <= response.status_code < 400:
            app_logger.info(f"Redirect: {request.method} {request.url.path}", context)
        elif 400 <= response.status_code < 500:
            app_logger.warning(f"Client error: {request.method} {request.url.path}", context)
        else:
            app_logger.error(f"Server error: {request.method} {request.url.path}", context)

        if request.method == "GET" and 200 <= response.status_code < 400:
            path = request.url.path or ""
            if not self._should_skip_activity(path):
                module_name = self._module_from_path(path)
                activity_logger = get_activity_logger()
                activity_logger.log_action(
                    user_email=user_email,
                    action=ActionType.PAGE_VIEW,
                    module=module_name,
                    details={"path": path, "method": request.method},
                    ip_address=get_client_ip(request),
                    success=True
                )
        
        return response 

    def _should_skip_activity(self, path: str) -> bool:
        skip_prefixes = ("/static", "/img", "/uploads", "/favicon", "/health", "/api", "/gpt4all")
        return path.startswith(skip_prefixes)

    def _module_from_path(self, path: str) -> str:
        if not path or path == "/":
            return "main"
        seg = path.strip("/").split("/")[0]
        mapping = {
            "spec-center": "spec_center",
            "product-info": "product_info",
        }
        return mapping.get(seg, seg)