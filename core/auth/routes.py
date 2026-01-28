
from fastapi import APIRouter ,Request ,Form ,Depends 
from fastapi .responses import HTMLResponse ,RedirectResponse 
from sqlalchemy import select 
from sqlalchemy .orm import Session 

from core .auth .models import User ,PendingUser, WebToken
from core .auth .db import get_auth_db 
from core .i18n import get_locale 
from core .activity_logger import get_activity_logger, ActionType
from core .utils import get_client_ip
from core .logger import auth_logger

router =APIRouter ()

templates =None 

def set_templates (tmpl ):
    global templates 
    templates =tmpl 


@router .get ("/login",response_class =HTMLResponse )
def login_page (request :Request, error :str =""):
    locale =get_locale (request )
                                         
    next_url = request.query_params.get("next", "/main")
    return templates .TemplateResponse (
    "auth/login.html",
    {"request":request ,"next":next_url ,"locale":locale ,"error":error }
    )


@router .get ("/register",response_class =HTMLResponse )
def register_page (request :Request ,error :str =""):
    locale =get_locale (request )
    return templates .TemplateResponse (
    "auth/register.html",
    {"request":request ,"locale":locale ,"error":error }
    )


@router .post ("/login")
async def do_login (
request :Request ,
db :Session =Depends (get_auth_db )
):
    activity_logger = get_activity_logger()
    ip_address = get_client_ip(request)
    
    try :
        form_data =await request .form ()
        email =form_data .get ("email","").strip ()
        password =form_data .get ("password","").strip ()
        next_url =form_data .get ("next","/main")

        auth_logger.log_request("POST", "/login", email)
        auth_logger.debug(f"Login attempt for {email}", {"ip": ip_address})

        if not email or not password :
                       
            auth_logger.warning("Login failed: invalid credentials", {"email": email or "unknown"})
            activity_logger.log_login(email or "unknown", ip_address, success=False)
            return RedirectResponse (url ="/auth/login?error=invalid",status_code =303 )

        user =db .execute (
        select (User ).where (User .email ==email )
        ).scalars ().first ()

        if user and user .is_active and user .verify_password (password ):
            request .session ["user_id"]=user .id 
            request .session ["email"]=user .email 
            request .session ["user_email"]=user .email         
            request .session ["english_name"]=user .english_name 
            request .session ["department"]=user .department 
            request .session ["role"]=user .role 
            request .session ["is_authenticated"]=True 

                       
            auth_logger.info(f"User {email} logged in successfully", {"user_id": user.id, "ip": ip_address})
            activity_logger.log_login(user.email, ip_address, success=True)
            
            return RedirectResponse (url =next_url or "/main",status_code =303 )

                   
        auth_logger.warning(f"Login failed for {email}: user not found or inactive", {"email": email, "ip": ip_address})
        activity_logger.log_login(email, ip_address, success=False)
        return RedirectResponse (url ="/auth/login?error=invalid",status_code =303 )

    except Exception as e:
                      
        email_for_log = email if 'email' in locals() else "unknown"
        auth_logger.error(f"Login error for {email_for_log}", {"ip": ip_address, "error": str(e)}, exc_info=True)
        activity_logger.log_login(email_for_log, ip_address, success=False)
        return RedirectResponse (url ="/auth/login?error=invalid",status_code =303 )


@router .post ("/register")
def do_register (
request :Request ,
english_name :str =Form (...),
email :str =Form (...),
password :str =Form (...),
confirm_password :str =Form (...),
department :str =Form (default =""),
db :Session =Depends (get_auth_db )
):
    auth_logger.log_request("POST", "/register", email)
    
    if not english_name or len (english_name )<2 :
        auth_logger.warning("Registration failed: invalid english name", {"email": email, "name": english_name})
        return RedirectResponse (url ="/auth/register?error=invalid_english_name",status_code =303 )

    if not email or '@'not in email :
        auth_logger.warning("Registration failed: invalid email", {"email": email})
        return RedirectResponse (url ="/auth/register?error=invalid_email",status_code =303 )

    if password !=confirm_password :
        auth_logger.warning("Registration failed: password mismatch", {"email": email})
        return RedirectResponse (url ="/auth/register?error=password_mismatch",status_code =303 )

    if len (password )<6 :
        auth_logger.warning("Registration failed: weak password", {"email": email})
        return RedirectResponse (url ="/auth/register?error=weak_password",status_code =303 )

    existing_user =db .execute (
    select (User ).where (User .email ==email )
    ).scalars ().first ()

    existing_pending =db .execute (
    select (PendingUser ).where (PendingUser .email ==email )
    ).scalars ().first ()

    if existing_user or existing_pending :
        auth_logger.warning("Registration failed: email already exists", {"email": email})
        return RedirectResponse (url ="/auth/register?error=email_exists",status_code =303 )

    pending_user =PendingUser (
    email =email ,
    english_name =english_name ,
    password_hash =User .hash_password (password ),
    department =department or "",
    status ="Pending"
    )

    db .add (pending_user )
    db .commit ()
    
    auth_logger.info(f"New user registration pending: {email}", {"department": department, "name": english_name})

    return RedirectResponse (url ="/auth/register/pending",status_code =303 )


@router .get ("/register/pending",response_class =HTMLResponse )
def register_pending (request :Request ):
    locale =get_locale (request )
    return templates .TemplateResponse (
    "auth/register_pending.html",
    {"request":request ,"locale":locale }
    )


@router .get ("/logout")
def logout (request :Request ):
    activity_logger = get_activity_logger()
    ip_address = get_client_ip(request)
    
                       
    user_email = request.session.get("user_email") or request.session.get("email")
    
    if user_email:
                 
        auth_logger.info(f"User {user_email} logged out", {"ip": ip_address})
        activity_logger.log_logout(user_email, ip_address)
    
    request .session .clear ()
    return RedirectResponse (url ="/",status_code =303 )


                                                   

from fastapi import HTTPException, status
from pydantic import BaseModel, Field

class LoginRequest(BaseModel):
    email: str = Field(..., description="User email")
    password: str = Field(..., description="User password")

class LoginResponse(BaseModel):
    success: bool
    user: dict = None
    error: str = None

@router.post("/api/login", response_model=LoginResponse)
async def api_login(
    login_data: LoginRequest,
    request: Request,
    db: Session = Depends(get_auth_db)
):
    """JSON API for desktop client login"""
    activity_logger = get_activity_logger()
    ip_address = get_client_ip(request)
    
    try:
        email = login_data.email.strip()
        password = login_data.password.strip()
        
        auth_logger.log_request("POST", "/api/login", email)
        
        if not email or not password:
            activity_logger.log_login(email or "unknown", ip_address, success=False)
            return LoginResponse(success=False, error="Email and password are required")
        
        user = db.execute(
            select(User).where(User.email == email)
        ).scalars().first()
        
        if user and user.is_active and user.verify_password(password):
                         
            request.session["user_id"] = user.id
            request.session["email"] = user.email
            request.session["user_email"] = user.email
            request.session["english_name"] = user.english_name
            request.session["department"] = user.department
            request.session["role"] = user.role
            request.session["is_authenticated"] = True
            
            auth_logger.info(f"API login successful: {email}", {"user_id": user.id, "ip": ip_address})
            activity_logger.log_login(user.email, ip_address, success=True)
            
            return LoginResponse(
                success=True,
                user={
                    "id": user.id,
                    "email": user.email,
                    "english_name": user.english_name,
                    "department": user.department,
                    "role": user.role
                }
            )
        else:
            auth_logger.warning(f"API login failed: {email}", {"ip": ip_address})
            activity_logger.log_login(email, ip_address, success=False)
            return LoginResponse(success=False, error="Invalid email or password")
    
    except Exception as e:
        auth_logger.error(f"API login error: {str(e)}", {"email": email})
        return LoginResponse(success=False, error="Login failed. Please try again.")


@router.get("/api/web-token")
async def get_web_token(request: Request, db: Session = Depends(get_auth_db)):
    """Generate a one-time token for browser login from desktop app"""
                                    
    user_id = request.session.get("user_id")
    if not user_id:
        return {"success": False, "error": "Not authenticated"}
    
                             
    user = db.execute(select(User).where(User.id == user_id)).scalars().first()
    if not user or not user.is_active:
        return {"success": False, "error": "User not found or inactive"}
    
                             
    import secrets
    import time
    
    token = secrets.token_urlsafe(32)
    expires_at = time.time() + 60                       
    
                                                
    try:
        web_token = WebToken(
            token=token,
            user_id=user_id,
            expires_at=expires_at
        )
        db.add(web_token)
        db.commit()
        auth_logger.info(f"Web token generated for user {user.email}: {token[:10]}...", {"user": user.email})
        return {"success": True, "token": token}
    except Exception as e:
        db.rollback()
        auth_logger.error(f"Failed to create web token: {str(e)}", {"email": email}, exc_info=True)
        return {"success": False, "error": str(e)}


@router.get("/api/web-login")
async def web_login_with_token(
    token: str,
    request: Request,
    db: Session = Depends(get_auth_db),
    next: str = None
):
    """Login to web using token from desktop app"""
    import time
    
                            
    web_token = db.execute(select(WebToken).where(WebToken.token == token)).scalars().first()
    
    if not web_token:
        auth_logger.warning(f"Invalid web token: {token}", {"token": token})
        return RedirectResponse(url="/auth/login?error=invalid_token")
    
                            
    if time.time() > web_token.expires_at:
        auth_logger.warning(f"Web token expired: {token}", {"token": token})
        db.delete(web_token)
        db.commit()
        return RedirectResponse(url="/auth/login?error=token_expired")
    
              
    user = db.execute(select(User).where(User.id == web_token.user_id)).scalars().first()
    
    if user and user.is_active:
                     
        request.session["user_id"] = user.id
        request.session["email"] = user.email
        request.session["user_email"] = user.email
        request.session["english_name"] = user.english_name
        request.session["department"] = user.department
        request.session["role"] = user.role
        request.session["is_authenticated"] = True
        
                           
        db.delete(web_token)
        db.commit()
        
        auth_logger.info(f"Web token login successful for user {user.email}", {"user": user.email})
        
                                                            
        redirect_url = next if next else "/main"
        redirect = RedirectResponse(url=redirect_url, status_code=302)
        return redirect

    auth_logger.error("User not found or inactive for web token")
    return RedirectResponse(url="/auth/login?error=invalid_user")


@router.get("/api/me")
async def get_me(request: Request, db: Session = Depends(get_auth_db)):
    """Get current user info (for desktop client session check)"""
    user_id = request.session.get("user_id")
    
    if not user_id:
        return {"authenticated": False, "user": None}
    
    user = db.execute(
        select(User).where(User.id == user_id)
    ).scalars().first()
    
    if user and user.is_active:
        return {
            "authenticated": True,
            "user": {
                "id": user.id,
                "email": user.email,
                "english_name": user.english_name,
                "department": user.department,
                "role": user.role
            }
        }
    
    return {"authenticated": False, "user": None}

