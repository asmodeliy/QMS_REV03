from fastapi import APIRouter ,Request ,Depends 
from fastapi .responses import HTMLResponse ,RedirectResponse 
from sqlalchemy .orm import Session 

from core.auth.db import get_auth_db
from core.auth.models import User
from core .utils import get_visit_token 
from core .i18n import get_locale 

router =APIRouter ()


templates =None 

def set_templates (tmpl ):
    global templates 
    templates =tmpl 


def ensure_admin (request :Request ):
    if not request .session .get ("is_authenticated"):
        return RedirectResponse (url ="/auth/login",status_code =303 )
    role = (request.session.get("role") or "").lower()
    if role != "admin":
        return RedirectResponse (url ="/main",status_code =303 )
    return None 


@router .get ("/admin",response_class =HTMLResponse )
@router .get ("/admin/dashboard",response_class =HTMLResponse )
def admin_dashboard (request :Request ,db :Session =Depends (get_auth_db )):
    r =ensure_admin (request )
    if r :
        return r 

    locale =get_locale (request )


    admin_email =request .session .get ("email")
    admin_user =db .query (User ).filter (User .email ==admin_email ).first ()

    return templates .TemplateResponse ("shared/admin_dashboard.html",{
    "request":request ,
    "locale":locale ,
    "admin_user":admin_user ,
    "visit":get_visit_token (request ),
    })

@router.get("/admin/svit")
def admin_module_svit_redirect(request: Request):
    return RedirectResponse(url="/admin/svit/register", status_code=303)


@router.get("/admin/garage")
def admin_module_garage_redirect(request: Request):
    return RedirectResponse(url="/api/garage/upload", status_code=303)
