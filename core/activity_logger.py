
import logging
from datetime import datetime
from pathlib import Path
from typing import Optional
import json

from core.config import BASE_DIR

         
LOGS_DIR = BASE_DIR / "logs"
LOGS_DIR.mkdir(exist_ok=True)

          
class ActionType:
        
    LOGIN = "login"
    LOGOUT = "logout"
    REGISTER = "register"
    PASSWORD_RESET = "password_reset"
    
          
    PROJECT_CREATE = "project_create"
    PROJECT_UPDATE = "project_update"
    PROJECT_DELETE = "project_delete"
    TASK_CREATE = "task_create"
    TASK_UPDATE = "task_update"
    TASK_DELETE = "task_delete"
    TASK_FILE_UPLOAD = "task_file_upload"
    TASK_FILE_DELETE = "task_file_delete"
    
          
    SVIT_ISSUE_CREATE = "svit_issue_create"
    SVIT_ISSUE_UPDATE = "svit_issue_update"
    SVIT_ISSUE_DELETE = "svit_issue_delete"
    SVIT_FILE_UPLOAD = "svit_file_upload"
    
          
    CITS_ISSUE_CREATE = "cits_issue_create"
    CITS_ISSUE_UPDATE = "cits_issue_update"
    CITS_ISSUE_DELETE = "cits_issue_delete"
    CITS_COMMENT_ADD = "cits_comment_add"
    CITS_FILE_UPLOAD = "cits_file_upload"
    
                 
    SPEC_UPLOAD = "spec_upload"
    SPEC_DELETE = "spec_delete"
    SPEC_DOWNLOAD = "spec_download"
    
         
    ADMIN_USER_APPROVE = "admin_user_approve"
    ADMIN_USER_REJECT = "admin_user_reject"
    ADMIN_USER_DELETE = "admin_user_delete"
    ADMIN_SETTINGS_UPDATE = "admin_settings_update"


class UserActivityLogger:
    
    def __init__(self):
                     
        self.activity_log_file = LOGS_DIR / f"user_activity_{datetime.now().strftime('%Y%m%d')}.log"
        
               
        self.logger = logging.getLogger("user_activity")
        self.logger.setLevel(logging.INFO)
        
                        
        if not self.logger.handlers:
            file_handler = logging.FileHandler(
                self.activity_log_file,
                encoding='utf-8'
            )
            file_handler.setLevel(logging.INFO)
            
                   
            formatter = logging.Formatter(
                '%(asctime)s | %(levelname)s | %(message)s',
                datefmt='%Y-%m-%d %H:%M:%S'
            )
            file_handler.setFormatter(formatter)
            self.logger.addHandler(file_handler)
    
    def log_action(
        self,
        user_email: str,
        action: str,
        module: str,
        details: Optional[dict] = None,
        ip_address: Optional[str] = None,
        success: bool = True
    ):
        """        
        Args:
            user_email: 사용자 이메일
            action: 액션 타입 (ActionType 상수 사용)
            module: 모듈명 (rpmt, svit, cits, spec_center 등)
            details: 추가 상세 정보 (dict)
            ip_address: 사용자 IP 주소
            success: 성공 여부
        """
        log_entry = {
            "timestamp": datetime.now().isoformat(),
            "user": user_email,
            "action": action,
            "module": module,
            "success": success,
            "ip": ip_address or "unknown",
        }
        
        if details:
            log_entry["details"] = details
        
                         
        self.logger.info(json.dumps(log_entry, ensure_ascii=False))
    
    def log_login(self, user_email: str, ip_address: str, success: bool = True):
        self.log_action(
            user_email=user_email,
            action=ActionType.LOGIN,
            module="auth",
            ip_address=ip_address,
            success=success
        )
    
    def log_logout(self, user_email: str, ip_address: str):
        self.log_action(
            user_email=user_email,
            action=ActionType.LOGOUT,
            module="auth",
            ip_address=ip_address
        )
    
    def log_project_action(
        self,
        user_email: str,
        action: str,
        project_id: Optional[int] = None,
        project_name: Optional[str] = None,
        ip_address: Optional[str] = None
    ):
        details = {}
        if project_id:
            details["project_id"] = project_id
        if project_name:
            details["project_name"] = project_name
        
        self.log_action(
            user_email=user_email,
            action=action,
            module="rpmt",
            details=details,
            ip_address=ip_address
        )
    
    def log_task_action(
        self,
        user_email: str,
        action: str,
        task_id: Optional[int] = None,
        task_name: Optional[str] = None,
        project_id: Optional[int] = None,
        ip_address: Optional[str] = None
    ):
        details = {}
        if task_id:
            details["task_id"] = task_id
        if task_name:
            details["task_name"] = task_name
        if project_id:
            details["project_id"] = project_id
        
        self.log_action(
            user_email=user_email,
            action=action,
            module="rpmt",
            details=details,
            ip_address=ip_address
        )
    
    def log_file_action(
        self,
        user_email: str,
        action: str,
        module: str,
        filename: str,
        file_size: Optional[int] = None,
        ip_address: Optional[str] = None
    ):
        details = {"filename": filename}
        if file_size:
            details["file_size_bytes"] = file_size
        
        self.log_action(
            user_email=user_email,
            action=action,
            module=module,
            details=details,
            ip_address=ip_address
        )
    
    def log_admin_action(
        self,
        admin_email: str,
        action: str,
        target_user: Optional[str] = None,
        details: Optional[dict] = None,
        ip_address: Optional[str] = None
    ):
        action_details = details or {}
        if target_user:
            action_details["target_user"] = target_user
        
        self.log_action(
            user_email=admin_email,
            action=action,
            module="admin",
            details=action_details,
            ip_address=ip_address
        )


          
_activity_logger = None

def get_activity_logger() -> UserActivityLogger:
    global _activity_logger
    if _activity_logger is None:
        _activity_logger = UserActivityLogger()
    return _activity_logger
