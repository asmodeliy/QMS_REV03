"""RPMT 라우트 모듈"""

from .dashboard import router as dashboard_router, set_templates as set_dashboard_templates
from .project import router as projects_router, set_templates as set_projects_templates
from .admin import router as admin_router, set_templates as set_admin_templates
from .weekly import router as weekly_router, set_templates as set_weekly_templates
from .report import router as report_router, set_templates as set_report_templates

__all__ = [
    'dashboard_router', 'set_dashboard_templates',
    'projects_router', 'set_projects_templates',
    'admin_router', 'set_admin_templates',
    'weekly_router', 'set_weekly_templates',
    'report_router', 'set_report_templates',
]

