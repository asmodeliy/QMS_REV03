from fastapi import APIRouter ,Request ,Depends 
from fastapi .responses import HTMLResponse ,RedirectResponse 
from sqlalchemy .orm import Session 

from models import User 
from core .db import get_db 
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
    if request .session .get ("role")!="Admin":
        return RedirectResponse (url ="/main",status_code =303 )
    return None 


@router .get ("/admin-dashboard",response_class =HTMLResponse )
def admin_dashboard (request :Request ,db :Session =Depends (get_db )):
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
