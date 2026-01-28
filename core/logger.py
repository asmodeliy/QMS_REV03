import logging
import json
from datetime import datetime
from pathlib import Path
from enum import Enum
from typing import Optional, Dict, Any

class LogLevel(str, Enum):
    """Log level enumeration"""
    DEBUG = "DEBUG"
    INFO = "INFO"
    WARNING = "WARNING"
    ERROR = "ERROR"
    CRITICAL = "CRITICAL"

class Logger:
    """Structured logging system for the application"""
    
    def __init__(self, module_name: str = "app"):
        """
        Initialize logger for a specific module
        
        Args:
            module_name: Name of the module (e.g., 'auth', 'rpmt', 'svit')
        """
        self.module_name = module_name
        self.logger = logging.getLogger(module_name)
        
                                      
        log_dir = Path(__file__).parent.parent / "logs"
        log_dir.mkdir(exist_ok=True)
        
                                                    
        if not self.logger.handlers:
            self._configure_logger(log_dir)
    
    def _configure_logger(self, log_dir: Path):
        """Configure logger with file and console handlers"""
                           
        json_formatter = logging.Formatter(
            '{"timestamp": "%(asctime)s", "level": "%(levelname)s", "module": "%(name)s", "message": "%(message)s"}',
            datefmt='%Y-%m-%d %H:%M:%S'
        )
        console_formatter = logging.Formatter(
            '[%(asctime)s] %(levelname)-8s [%(name)s] %(message)s',
            datefmt='%Y-%m-%d %H:%M:%S'
        )
        
                                    
        log_file = log_dir / f"{self.module_name}.log"
        file_handler = logging.FileHandler(log_file, encoding='utf-8')
        file_handler.setLevel(logging.DEBUG)
        file_handler.setFormatter(json_formatter)
        
                                          
        console_handler = logging.StreamHandler()
        console_handler.setLevel(logging.INFO)
        console_handler.setFormatter(console_formatter)
        
                                
        self.logger.setLevel(logging.DEBUG)
        self.logger.addHandler(file_handler)
        self.logger.addHandler(console_handler)
    
    def _format_message(self, message: str, context: Optional[Dict[str, Any]] = None) -> str:
        """Format log message with optional context"""
        if context:
            context_str = json.dumps(context, ensure_ascii=False)
            return f"{message} | {context_str}"
        return message
    
    def debug(self, message: str, context: Optional[Dict[str, Any]] = None):
        """Log debug message"""
        self.logger.debug(self._format_message(message, context))
    
    def info(self, message: str, context: Optional[Dict[str, Any]] = None):
        """Log info message"""
        self.logger.info(self._format_message(message, context))
    
    def warning(self, message: str, context: Optional[Dict[str, Any]] = None):
        """Log warning message"""
        self.logger.warning(self._format_message(message, context))
    
    def error(self, message: str, context: Optional[Dict[str, Any]] = None, exc_info: bool = False):
        """Log error message"""
        self.logger.error(self._format_message(message, context), exc_info=exc_info)
    
    def critical(self, message: str, context: Optional[Dict[str, Any]] = None, exc_info: bool = False):
        """Log critical message"""
        self.logger.critical(self._format_message(message, context), exc_info=exc_info)
    
                                                     
    def log_request(self, method: str, path: str, user: Optional[str] = None):
        """Log incoming request"""
        context = {
            "type": "request",
            "method": method,
            "path": path,
            "user": user or "anonymous"
        }
        self.debug(f"Request received", context)
    
    def log_response(self, status_code: int, message: str = "Success"):
        """Log response"""
        context = {
            "type": "response",
            "status_code": status_code,
        }
        level = "info" if 200 <= status_code < 300 else "warning" if status_code < 500 else "error"
        getattr(self, level)(f"Response: {message}", context)
    
    def log_database_operation(self, operation: str, table: str, details: Optional[Dict] = None):
        """Log database operation"""
        context = {
            "type": "database",
            "operation": operation,
            "table": table,
        }
        if details:
            context.update(details)
        self.debug(f"Database operation: {operation} on {table}", context)
    
    def log_error(self, error_type: str, message: str, details: Optional[Dict] = None):
        """Log error with structured data"""
        context = {
            "type": "error",
            "error_type": error_type,
            "timestamp": datetime.now().isoformat()
        }
        if details:
            context.update(details)
        self.error(message, context, exc_info=True)
    
    def log_authentication(self, event: str, user_id: Optional[str] = None, success: bool = True):
        """Log authentication events"""
        context = {
            "type": "authentication",
            "event": event,
            "user_id": user_id or "unknown",
            "success": success,
            "timestamp": datetime.now().isoformat()
        }
        level = "info" if success else "warning"
        getattr(self, level)(f"Auth event: {event}", context)
    
    def log_authorization(self, action: str, resource: str, user_id: str, allowed: bool):
        """Log authorization decision"""
        context = {
            "type": "authorization",
            "action": action,
            "resource": resource,
            "user_id": user_id,
            "allowed": allowed,
            "timestamp": datetime.now().isoformat()
        }
        level = "info" if allowed else "warning"
        getattr(self, level)(f"Authorization: {action} on {resource}", context)
    
    def log_file_operation(self, operation: str, file_path: str, size: Optional[int] = None):
        """Log file operation"""
        context = {
            "type": "file",
            "operation": operation,
            "file_path": file_path,
        }
        if size:
            context["size_bytes"] = size
        self.info(f"File operation: {operation} on {file_path}", context)


                                            
auth_logger = Logger("auth")
rpmt_logger = Logger("rpmt")
svit_logger = Logger("svit")
cits_logger = Logger("cits")
spec_center_logger = Logger("spec_center")
db_logger = Logger("database")
apqp_logger = Logger("apqp")
app_logger = Logger("app")
garage_logger = Logger("garage")
