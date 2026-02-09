from fastapi import APIRouter ,Request 
from fastapi .responses import RedirectResponse 
from pathlib import Path 

from core .i18n import get_locale 

router =APIRouter ()

templates =None 

def set_templates (tmpl ):
    global templates 
    templates =tmpl 


def ensure_authenticated (request :Request ):
    if not request .session .get ("is_authenticated"):
        return RedirectResponse (url ="/main",status_code =303 )
    return None 


@router .get ("/profile")
async def profile (request :Request ):
    auth_check =ensure_authenticated (request )
    if auth_check :
        return auth_check 

    locale =get_locale (request )
    email =request .session .get ("email")
    english_name =request .session .get ("english_name","")
    department =request .session .get ("department","")
    role =request .session .get ("role","User")

    return templates .TemplateResponse ("shared/profile.html",{
    "request":request ,
    "locale":locale ,
    "email":email ,
    "english_name":english_name ,
    "department":department ,
    "role":role ,
    })


from fastapi import Form, Depends, HTTPException
from fastapi.responses import JSONResponse
from sqlalchemy.orm import Session
from core.auth.db import get_auth_db
from core.auth.models import User
from core.logger import auth_logger


@router.post('/profile/change-password')
async def change_password(request: Request, db: Session = Depends(get_auth_db)):
    auth_check = ensure_authenticated(request)
    if auth_check:
        return auth_check

    try:
        form = await request.form()
        current = (form.get('current_password') or '').strip()
        newpw = (form.get('new_password') or '').strip()
        confirm = (form.get('confirm_password') or '').strip()

        if not current or not newpw or not confirm:
            return JSONResponse({'ok': False, 'error': 'Missing form fields'}, status_code=400)
        if newpw != confirm:
            return JSONResponse({'ok': False, 'error': 'New passwords do not match'}, status_code=400)
        if len(newpw) < 6:
            return JSONResponse({'ok': False, 'error': 'Password too short'}, status_code=400)

        email = request.session.get('email')
        if not email:
            return JSONResponse({'ok': False, 'error': 'Not authenticated'}, status_code=401)

        user = db.query(User).filter(User.email == email).first()
        if not user or not user.verify_password(current):
            auth_logger.info(f"Password change failed for {email}: current password mismatch")
            return JSONResponse({'ok': False, 'error': 'Current password incorrect'}, status_code=400)

        user.password_hash = User.hash_password(newpw)
        db.add(user)
        db.commit()
        auth_logger.info(f"Password changed for {email}")
        return JSONResponse({'ok': True, 'message': 'Password changed successfully'})

    except Exception as e:
        auth_logger.exception(f"Error changing password: {e}")
        raise HTTPException(status_code=500, detail=str(e))
