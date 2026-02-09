from fastapi import APIRouter ,Request ,HTTPException ,Depends ,Form 
from fastapi .responses import HTMLResponse ,RedirectResponse ,JSONResponse 
from core .i18n import get_locale 
from core .utils import get_visit_token 
from sqlalchemy .orm import Session 
from core .auth .db import get_auth_db 
from datetime import datetime as dt 
from core .auth .models import PendingUser ,User 
from sqlalchemy import select 
from core .logger import app_logger

router =APIRouter ()

templates =None 

def set_templates (tmpl ):
    global templates 
    templates =tmpl 

def ensure_admin_html (request :Request ):


    if request .session .get ("role")=="Admin":
        return None 

    return None 

def ensure_admin_api (request :Request ):
    if request .session .get ("role")!="Admin":
        raise HTTPException (status_code =401 ,detail ="Not authenticated")

@router .get ("/main",response_class =HTMLResponse )
def main (request :Request ):
    session_param = request.query_params.get("session")
    if session_param:
        response = RedirectResponse(url="/main", status_code=303)
        response.set_cookie("rams_sess", session_param, max_age=30*60, path="/", httponly=True)
        return response

    locale =get_locale (request )
    visit =get_visit_token (request )
    user_email = request.session.get("user_email", "anonymous")
    app_logger.log_request("GET", "/main", user_email)
    return templates .TemplateResponse ("main.html",{"request":request ,"locale":locale ,"visit":visit })


@router .get ("/apqp",response_class =HTMLResponse )
def apqp_page (request :Request ):
    locale =get_locale (request )
    return templates .TemplateResponse ("modules/apqp/index.html",{"request":request ,"locale":locale })


@router .get ("/apqp/help",response_class =HTMLResponse )
def apqp_help (request :Request ):
    locale =get_locale (request )
    return templates .TemplateResponse ("modules/apqp/help.html",{"request":request ,"locale":locale })


@router .get ("/tbd",response_class =HTMLResponse )
def tbd_redirect (request :Request ):
    return RedirectResponse(url="/spec-center", status_code=303)

@router .get ("/",response_class =HTMLResponse )
def index (request :Request ):
    return RedirectResponse (url ="/main",status_code =303 )

@router .get ("/dashboard",response_class =HTMLResponse )
def dashboard_redirect (request :Request ):
    return RedirectResponse (url ="/rpmt/dashboard",status_code =303 )

                                                                                     
                                                                                              
@router.api_route("/main/auth/api/login", methods=["GET","POST","PUT","DELETE","PATCH"])
def redirect_auth_login(request: Request):
    return RedirectResponse(url="/auth/api/login", status_code=307)

                                                                                    
@router.api_route("/main/api/{rest:path}", methods=["GET","POST","PUT","DELETE","PATCH"])
def redirect_main_api(rest: str, request: Request):
    target = f"/api/{rest}"
    app_logger.info(f"Redirect: {request.method} /main/api/{rest} -> {target}", {"path": request.url.path})
    return RedirectResponse(url=target, status_code=307)

@router.api_route("/main/auth/api/{rest:path}", methods=["GET","POST","PUT","DELETE","PATCH"])
def redirect_main_auth_api(rest: str, request: Request):
    target = f"/auth/api/{rest}"
    app_logger.info(f"Redirect: {request.method} /main/auth/api/{rest} -> {target}", {"path": request.url.path})
    return RedirectResponse(url=target, status_code=307)

@router .get ("/download", response_class=HTMLResponse)
def download_page(request: Request):
    locale = get_locale(request)
    visit = get_visit_token(request)

                                    
    import json
    from core.config import BASE_DIR
    meta_path = BASE_DIR / "static" / "downloads" / "qms-desktop.json"
    metadata = None
    try:
        if meta_path.exists():
            with open(meta_path, 'r', encoding='utf-8') as f:
                metadata = json.load(f)
                                         
                if 'sizeBytes' in metadata:
                    sz = int(metadata['sizeBytes'])
                    for unit in ['bytes','KB','MB','GB']:
                        if sz < 1024 or unit == 'GB':
                            metadata['size'] = f"{sz:.2f} {unit}" if unit != 'bytes' else f"{sz} bytes"
                            break
                        sz = sz / 1024
    except Exception:
        metadata = None

    return templates.TemplateResponse("downloads/index.html", {"request": request, "locale": locale, "visit": visit, "metadata": metadata})



@router .get ("/main/admin",response_class =HTMLResponse )
def admin_users_page (request :Request ,db :Session =Depends (get_auth_db )):
    r =ensure_admin_html (request )
    if r :
        if isinstance (r ,tuple )and r [0 ]=="access_denied":
            app_logger.warning("Access denied to admin page", {"user": request.session.get("user_email", "unknown")})
            locale =get_locale (request )
            return templates .TemplateResponse ("shared/access_denied.html",{
            "request":request ,
            "locale":locale ,
            })
        return r 

    user_email = request.session.get("user_email", "admin")
    app_logger.log_request("GET", "/main/admin", user_email)
    locale =get_locale (request )
    pending_users =db .execute (
    select (PendingUser ).where (PendingUser .status =="Pending").order_by (PendingUser .created_at .desc ())
    ).scalars ().all ()

    approved_pending_users =db .execute (
    select (PendingUser ).where (PendingUser .status =="Approved").order_by (PendingUser .reviewed_at .desc ())
    ).scalars ().all ()

    approved_users =[]
    for pending in approved_pending_users :
        user =db .execute (
        select (User ).where (User .email ==pending .email )
        ).scalars ().first ()
        reviewer =None 
        if pending .reviewed_by :
            reviewer =db .execute (
            select (User ).where (User .email ==pending .reviewed_by )
            ).scalars ().first ()
        if user :
            approved_users .append ({"pending":pending ,"user":user ,"reviewer":reviewer })

    rejected_users =db .execute (
    select (PendingUser ).where (PendingUser .status =="Rejected").order_by (PendingUser .reviewed_at .desc ())
    ).scalars ().all ()

    return templates .TemplateResponse ("shared/admin_users.html",{
    "request":request ,
    "pending_users":pending_users ,
    "approved_users":approved_users ,
    "rejected_users":rejected_users ,
    "locale":locale ,
    "visit":get_visit_token (request ),
    })


@router .post ("/main/admin/users/{user_id}/approve")
def approve_user (user_id :int ,request :Request ,role :str =Form ("User"),db :Session =Depends (get_auth_db )):
    ensure_admin_api (request )
    
    admin_email = request.session.get("user_email", "admin")

    pending_user =db .get (PendingUser ,user_id )
    if not pending_user or pending_user .status !="Pending":
        app_logger.warning(f"Approve user failed: user not found", {"user_id": user_id, "admin": admin_email})
        raise HTTPException (status_code =404 ,detail ="Pending user not found")

    existing =db .execute (
    select (User ).where (User .email ==pending_user .email )
    ).scalars ().first ()

    if existing :
        app_logger.warning(f"Approve user failed: user already exists", {"email": pending_user.email, "admin": admin_email})
        raise HTTPException (status_code =400 ,detail ="User already exists")

    valid_roles =["Admin","Manager","User"]
    if role not in valid_roles :
        role ="User"

    new_user =User (
    email =pending_user .email ,
    english_name =pending_user .english_name ,
    password_hash =pending_user .password_hash ,
    department =pending_user .department ,
    role =role 
    )

    db .add (new_user )

    pending_user .status ="Approved"
    pending_user .reviewed_at =dt .utcnow ()
    pending_user .reviewed_by =request .session .get ("email")

    db .commit ()
    
    app_logger.info(f"User {pending_user.email} approved", {"admin": admin_email, "role": role})

    return JSONResponse ({"ok":True ,"message":"사용자가 승인되었습니다"})


@router .post ("/main/admin/users/{user_id}/reject")
def reject_user (user_id :int ,request :Request ,db :Session =Depends (get_auth_db )):
    ensure_admin_api (request )
    
    admin_email = request.session.get("user_email", "admin")

    pending_user =db .get (PendingUser ,user_id )
    if not pending_user or pending_user .status !="Pending":
        app_logger.warning(f"Reject user failed: user not found", {"user_id": user_id, "admin": admin_email})
        raise HTTPException (status_code =404 ,detail ="Pending user not found")

    pending_user .status ="Rejected"
    pending_user .reviewed_at =dt .utcnow ()
    pending_user .reviewed_by =request .session .get ("email")

    db .commit ()
    
    app_logger.info(f"User {pending_user.email} rejected", {"admin": admin_email})

    return JSONResponse ({"ok":True ,"message":"사용자가 거부되었습니다"})


@router .post ("/main/admin/users/{user_id}/update-role")
def update_user_role (user_id :int ,request :Request ,role :str =Form ("User"),db :Session =Depends (get_auth_db )):
    ensure_admin_api (request )

    user =db .get (User ,user_id )
    if not user :
        raise HTTPException (status_code =404 ,detail ="User not found")

    valid_roles =["Admin","Manager","User"]
    if role not in valid_roles :
        role ="User"

    user .role =role 
    db .commit ()

    return JSONResponse ({"ok":True ,"message":"역할이 업데이트되었습니다"})



@router .get ("/main/admin/feedback")
def feedback_page (request :Request ):
    if request .session .get ("role")!="Admin":
        return RedirectResponse (url ="/auth/login?next=/main/admin/feedback",status_code =303 )

    locale =get_locale (request )
    visit =get_visit_token (request )
    return templates .TemplateResponse (
    "modules/rpmt/feedback.html",
    {"request":request ,"visit":visit ,"locale":locale }
    )

@router .get ("/main/admin/feedback.json")
def feedback_list (request :Request ):
    if request .session .get ("role")!="Admin":
        raise HTTPException (status_code =401 ,detail ="Not authenticated")

    from modules.routes.help_routes import load_feedbacks 
    feedbacks =load_feedbacks ()
    feedbacks .sort (key =lambda x :x .get ('timestamp',''),reverse =True )
    return feedbacks 


@router .get ("/main/admin/feedback/unread-count")
def unread_feedback_count (request :Request ):
    if request .session .get ("role")!="Admin":
        raise HTTPException (status_code =401 ,detail ="Not authenticated")

    from routes .help_routes import load_feedbacks 
    feedbacks =load_feedbacks ()
    count =sum (1 for f in feedbacks if f .get ('status')=='New')
    return {"count":count }


@router .post ("/main/admin/feedback/{feedback_id}/status")
async def update_feedback_status (feedback_id :int ,request :Request ):
    if request .session .get ("role")!="Admin":
        raise HTTPException (status_code =401 ,detail ="Not authenticated")

    from routes .help_routes import load_feedbacks ,save_feedbacks 

    try :
        data =await request .json ()
        new_status =data .get ("status","Read")

        feedbacks =load_feedbacks ()
        feedback =next ((f for f in feedbacks if f .get ("id")==feedback_id ),None )

        if not feedback :
            return {"ok":False ,"error":"피드백을 찾을 수 없습니다"}

        feedback ["status"]=new_status 
        save_feedbacks (feedbacks )

        return {"ok":True }
    except Exception as e :
        return {"ok":False ,"error":str (e )}


@router .post ("/main/admin/feedback/{feedback_id}/reply")
async def reply_feedback (feedback_id :int ,request :Request ):
    if request .session .get ("role")!="Admin":
        raise HTTPException (status_code =401 ,detail ="Not authenticated")

    from routes .help_routes import load_feedbacks ,save_feedbacks ,send_reply_email 

    try :
        data =await request .json ()
        reply_message =data .get ("reply","")

        feedbacks =load_feedbacks ()
        feedback =next ((f for f in feedbacks if f .get ("id")==feedback_id ),None )

        if not feedback :
            return {"ok":False ,"error":"피드백을 찾을 수 없습니다"}

        send_reply_email (feedback ,reply_message )

        feedback ["status"]="Replied"
        feedback ["admin_reply"]=reply_message 
        feedback ["replied_at"]=dt .isoformat (dt .now ())
        save_feedbacks (feedbacks )

        return {"ok":True }
    except Exception as e :
        return {"ok":False ,"error":str (e )}

