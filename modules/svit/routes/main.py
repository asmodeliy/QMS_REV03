

from fastapi import APIRouter ,Request ,HTTPException ,Form ,UploadFile ,File 
from typing import List 
from fastapi .responses import HTMLResponse ,RedirectResponse ,JSONResponse 
from sqlalchemy .orm import Session 
from pathlib import Path 
from core.config import BASE_DIR
import os 
from datetime import datetime 
import re
import sqlite3

from core .i18n import get_locale ,t as i18n_t 
from modules .svit .db import get_svit_db_sync 
from modules .svit .models import Issue ,IssueStatusEnum ,Shuttle 
from core .logger import svit_logger 

SVIT_DB_PATH = Path(__file__).parent.parent / "svit.db"

def sanitize_filename(filename: str) -> str:
    """Remove or replace characters that cause issues in URLs"""
    filename = re.sub(r'[#?&=%;]', '_', filename)
    filename = re.sub(r'\s+', '_', filename)
    return filename


# Upload helper utilities
import unicodedata
import tempfile
import shutil
from core.config import SVIT_ALLOWED_ATTACHMENTS, SVIT_MAX_ATTACH_SIZE


def save_upload_file(up: UploadFile, upload_dir: Path, issue_id: int) -> Path:
    """Safely save an UploadFile to upload_dir, enforcing allowed extensions and size limits.
    Returns a Path relative to project uploads (Path('uploads')/'svit'/filename).
    Raises ValueError on validation error.
    """
    orig_name = Path(up.filename).name
    norm_name = unicodedata.normalize('NFC', orig_name)
    ext = norm_name.rsplit('.', 1)[-1].lower() if '.' in norm_name else ''

    if ext not in SVIT_ALLOWED_ATTACHMENTS:
        raise ValueError(f"disallowed file type: .{ext}")

    upload_dir.mkdir(parents=True, exist_ok=True)

    tmp = None
    size = 0
    try:
        tmp = tempfile.NamedTemporaryFile(delete=False, dir=str(upload_dir))
        while True:
            chunk = up.file.read(64 * 1024)
            if not chunk:
                break
            size += len(chunk)
            if size > SVIT_MAX_ATTACH_SIZE:
                raise ValueError('file too large')
            tmp.write(chunk)
        tmp.flush()
        tmp.close()

        timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
        safe = sanitize_filename(norm_name)
        unique = f"issue_{issue_id}_{timestamp}_{safe}"
        final_path = upload_dir / unique
        # atomic replace (same filesystem)
        os.replace(tmp.name, final_path)
        return Path('uploads') / 'svit' / unique
    except Exception:
        if tmp is not None:
            try:
                os.unlink(tmp.name)
            except Exception:
                pass
        raise
router =APIRouter (tags =["svit"])

templates =None 

def set_templates (tmpl ):
    global templates 
    templates =tmpl 


def ensure_authenticated (request :Request ):
    if not request .session .get ("is_authenticated"):
        return RedirectResponse (url ="/auth/login",status_code =303 )
    return None 


@router .get ("/",response_class =HTMLResponse )
def svit_main (request :Request ,status :str =None ):
                                                                     
    session_param = request.query_params.get("session")
    if session_param:
                                          
        response = RedirectResponse(url="/svit/", status_code=303)
        response.set_cookie("rams_sess", session_param, max_age=30*60, path="/", httponly=True)
        return response

    auth_check =ensure_authenticated (request )
    if auth_check :
        return auth_check 

    if templates is None :
        return HTMLResponse ("<h1>Error: Templates not initialized</h1>")

    locale =get_locale (request )
    user_email = request.session.get("user_email", "anonymous")
    svit_logger.log_request("GET", "/svit", user_email)

    db =get_svit_db_sync ()

    try :
        query =db .query (Issue ).order_by (Issue .created_at .desc ())

        qparams = request.query_params
        shuttle = (qparams.get('shuttle') or '').strip()
        node = (qparams.get('node') or '').strip()
        ip = (qparams.get('ip') or '').strip()
        family = (qparams.get('family') or '').strip()

        if status :
            try_status =status .upper ()
            query =query .filter (Issue .status ==try_status )
        if shuttle:
            query = query.filter(Issue.shuttle_id == shuttle)
        if node:
            query = query.filter(Issue.node == node)
        if ip:
            query = query.filter(Issue.ip_ic == ip)
        if family:
            query = query.filter(Issue.family == family)

        try:
            issues = query.all()
        except ValueError:
            try:
                import sqlite3
                sqlite_conn = sqlite3.connect(str(SVIT_DB_PATH))
                sqlite_conn.row_factory = sqlite3.Row
                sqlite_cursor = sqlite_conn.cursor()
                
                where_clause = "WHERE 1=1"
                params = []
                if status:
                    where_clause += " AND status = ?"
                    params.append(status.upper())
                if shuttle:
                    where_clause += " AND shuttle_id = ?"
                    params.append(shuttle)
                if node:
                    where_clause += " AND node = ?"
                    params.append(node)
                if ip:
                    where_clause += " AND ip_ic = ?"
                    params.append(ip)
                if family:
                    where_clause += " AND family = ?"
                    params.append(family)
                
                sql = f"SELECT * FROM issues {where_clause} ORDER BY created_at DESC"
                sqlite_cursor.execute(sql, params)
                rows = sqlite_cursor.fetchall()
                
                issues = []
                for row in rows:
                    issue = type('Issue', (), dict(row))()
                    issues.append(issue)
                
                sqlite_conn.close()
            except Exception:
                issues = []

        processed_issues = []
        for issue in issues:
            try:
                if hasattr(issue, 'created_at') and isinstance(issue.created_at, str):
                    try:
                        from datetime import datetime as dt
                        issue.created_at = dt.fromisoformat(issue.created_at.replace('Z', '+00:00'))
                    except:
                        issue.created_at = None
                
                if hasattr(issue, 'updated_at') and isinstance(issue.updated_at, str):
                    try:
                        from datetime import datetime as dt
                        issue.updated_at = dt.fromisoformat(issue.updated_at.replace('Z', '+00:00'))
                    except:
                        issue.updated_at = None
                
                if hasattr(issue, 'report_date') and isinstance(issue.report_date, str):
                    try:
                        from datetime import datetime as dt
                        issue.report_date = dt.fromisoformat(issue.report_date.replace('Z', '+00:00'))
                    except:
                        issue.report_date = None
                
                if hasattr(issue, 'resolved_at') and isinstance(issue.resolved_at, str):
                    try:
                        from datetime import datetime as dt
                        issue.resolved_at = dt.fromisoformat(issue.resolved_at.replace('Z', '+00:00'))
                    except:
                        issue.resolved_at = None
                
                processed_issues.append(issue)
            except Exception:
                continue
        
        issues = processed_issues

        for issue in issues :
            if issue .status =="Closed":
                issue .status ="RESOLVED"
            elif issue .status =="Resolved":
                issue .status ="PENDING_REVIEW"

        shuttles =db .query (Shuttle ).order_by (Shuttle .shuttle_id ).all ()

        shuttles_data =[]
        shuttle_list = []
        node_list = []
        ip_list = []
        family_list = []
        for s in shuttles :
            powers =[getattr (s ,f"power_{i }")for i in range (1 ,8 )]
            shuttles_data .append ((s ,powers ))
            if s.shuttle_id and s.shuttle_id not in shuttle_list:
                shuttle_list.append(s.shuttle_id)
            if s.node and s.node not in node_list:
                node_list.append(s.node)
            if s.ip_ic and s.ip_ic not in ip_list:
                ip_list.append(s.ip_ic)
            if s.family and s.family not in family_list:
                family_list.append(s.family)

        total_issues =len (issues )
        new_issues =len ([i for i in issues if i .status =="NEW"])
        in_progress =len ([i for i in issues if i .status =="IN_PROGRESS"])
        resolved =len ([i for i in issues if i .status =="RESOLVED"])


        def t (key :str ,*args ,**kwargs ):
            return i18n_t (key ,locale ,**kwargs )

        return templates .TemplateResponse ("modules/svit/main.html",{
        "request":request ,
        "locale":locale ,
        "t":t ,
        "issues":issues ,
        "shuttles": shuttles ,
        "shuttles_data":shuttles_data ,
        "filter_shuttle_list": shuttle_list,
        "filter_node_list": node_list,
        "filter_ip_list": ip_list,
        "filter_family_list": family_list,
        "total_issues":total_issues ,
        "new_issues":new_issues ,
        "in_progress":in_progress ,
        "resolved":resolved ,
        "filter_status":status or "",
        })
    finally :
        db .close ()


@router .get ("/issue/{issue_id}",response_class =HTMLResponse )
def issue_detail (issue_id :int ,request :Request ):
    auth_check =ensure_authenticated (request )
    if auth_check :
        return auth_check 

    if templates is None :
        return HTMLResponse ("<h1>Error: Templates not initialized</h1>")

    locale =get_locale (request )

    db =get_svit_db_sync ()

    try :
        issue =db .query (Issue ).filter (Issue .id ==issue_id ).first ()
        if not issue :
            raise HTTPException (status_code =404 ,detail ="Issue not found")

        if issue .status =="Closed":
            issue .status ="RESOLVED"
        elif issue .status =="Resolved":
            issue .status ="PENDING_REVIEW"

        def t (key :str ,*args ,**kwargs ):
            return i18n_t (key ,locale ,**kwargs )

        return templates .TemplateResponse ("modules/svit/issue_detail.html",{
        "request":request ,
        "locale":locale ,
        "t":t ,
        "issue":issue ,
        })
    finally :
        db .close ()


@router .get ("/help",response_class =HTMLResponse )
def svit_help (request :Request ):
    auth_check =ensure_authenticated (request )
    if auth_check :
        return auth_check 

    if templates is None :
        return HTMLResponse ("<h1>Error: Templates not initialized</h1>")

    locale =get_locale (request )

    def t (key :str ,*args ,**kwargs ):
        return i18n_t (key ,locale ,**kwargs )

    return templates .TemplateResponse ("modules/svit/help.html",{
    "request":request ,
    "locale":locale ,
    "t":t ,
    })


def ensure_admin (request :Request ):
    if not request .session .get ("is_authenticated"):
        return RedirectResponse (url ="/auth/login",status_code =303 )
    if request .session .get ("role")!="Admin":
        return RedirectResponse (url ="/main",status_code =303 )
    return None 


@router .get ("/admin/register",response_class =HTMLResponse )
def admin_register_page (request :Request ):
    auth_check =ensure_admin (request )
    if auth_check :
        return auth_check 

    if templates is None :
        return HTMLResponse ("<h1>Error: Templates not initialized</h1>")

    locale =get_locale (request )
    db =get_svit_db_sync ()

    try :
        shuttles =db .query (Shuttle ).order_by (Shuttle .updated_at .desc ()).all ()

        shuttles_data =[]
        for s in shuttles :
            powers =[getattr (s ,f"power_{i }")for i in range (1 ,8 )]
            shuttles_data .append ((s ,powers ))

        def t (key :str ,*args ,**kwargs ):
            return i18n_t (key ,locale ,**kwargs )

        return templates .TemplateResponse ("modules/svit/admin_register.html",{
        "request":request ,
        "locale":locale ,
        "t":t ,
        "shuttles_data":shuttles_data ,
        })
    finally :
        db .close ()


@router .post ("/admin/register")
def admin_register_shuttle (
request :Request ,
shuttle_id :str =Form (...),
ip_ic :str =Form (...),
node :str =Form (default =""),
family :str =Form (default =""),
power_1 :str =Form (default =""),
power_2 :str =Form (default =""),
power_3 :str =Form (default =""),
power_4 :str =Form (default =""),
power_5 :str =Form (default =""),
power_6 :str =Form (default =""),
power_7 :str =Form (default =""),
):
    auth_check =ensure_admin (request )
    if auth_check :
        return auth_check 

    db =get_svit_db_sync ()

    try :
        existing =db .query (Shuttle ).filter (
        Shuttle .shuttle_id ==shuttle_id ,
        Shuttle .ip_ic ==ip_ic 
        ).first ()

        if existing :
            existing .node =node or existing .node 
            existing .family =family or existing .family 
            existing .power_1 =power_1 or existing .power_1 
            existing .power_2 =power_2 or existing .power_2 
            existing .power_3 =power_3 or existing .power_3 
            existing .power_4 =power_4 or existing .power_4 
            existing .power_5 =power_5 or existing .power_5 
            existing .power_6 =power_6 or existing .power_6 
            existing .power_7 =power_7 or existing .power_7 
        else :
            shuttle =Shuttle (
            shuttle_id =shuttle_id ,
            ip_ic =ip_ic ,
            node =node or None ,
            family =family or None ,
            power_1 =power_1 or None ,
            power_2 =power_2 or None ,
            power_3 =power_3 or None ,
            power_4 =power_4 or None ,
            power_5 =power_5 or None ,
            power_6 =power_6 or None ,
            power_7 =power_7 or None ,
            )
            db .add (shuttle )

        db .commit ()
        return RedirectResponse (url ="/svit/admin/register?success=true",status_code =303 )

    except Exception:
        return RedirectResponse (url ="/svit/admin/register?error=true",status_code =303 )
    finally :
        db .close ()


@router .post ("/admin/delete-mpw/{mpw_id}")
def delete_mpw (mpw_id :int ,request :Request ):
    auth_check =ensure_admin (request )
    if auth_check :
        return auth_check 

    db =get_svit_db_sync ()

    try :
        shuttle =db .query (Shuttle ).filter (Shuttle .id ==mpw_id ).first ()
        if shuttle :
            db .delete (shuttle )
            db .commit ()
        return RedirectResponse (url ="/svit/admin/register?success=true",status_code =303 )

    except Exception:
        return RedirectResponse (url ="/svit/admin/register?error=true",status_code =303 )
    finally :
        db .close ()


@router .post ("/admin/update-mpw")
def update_mpw (
request :Request ,
mpw_db_id :int =Form (...),
shuttle_id :str =Form (default =""),
ip_ic :str =Form (default =""),
node :str =Form (default =""),
family :str =Form (default =""),
power_1 :str =Form (default =""),
power_2 :str =Form (default =""),
power_3 :str =Form (default =""),
power_4 :str =Form (default =""),
power_5 :str =Form (default =""),
power_6 :str =Form (default =""),
power_7 :str =Form (default =""),
):
    auth_check =ensure_admin (request )
    if auth_check :
        return auth_check 

    db =get_svit_db_sync ()
    try :
        shuttle =db .query (Shuttle ).filter (Shuttle .id ==mpw_db_id ).first ()
        if not shuttle :
            return RedirectResponse (url ="/svit/admin/register?error=true",status_code =303 )


        if shuttle_id and shuttle_id != shuttle.shuttle_id:
            conflict = db.query(Shuttle).filter(Shuttle.shuttle_id == shuttle_id).first()
            if conflict:
                return RedirectResponse(url ="/svit/admin/register?error=true",status_code =303 )
            shuttle.shuttle_id = shuttle_id

        shuttle .ip_ic =ip_ic or shuttle .ip_ic 
        shuttle .node =node or shuttle .node 
        shuttle .family =family or shuttle .family 
        shuttle .power_1 =power_1 or shuttle .power_1 
        shuttle .power_2 =power_2 or shuttle .power_2 
        shuttle .power_3 =power_3 or shuttle .power_3 
        shuttle .power_4 =power_4 or shuttle .power_4 
        shuttle .power_5 =power_5 or shuttle .power_5 
        shuttle .power_6 =power_6 or shuttle .power_6 
        shuttle .power_7 =power_7 or shuttle .power_7 



        db .add (shuttle )
        db .commit ()
        return RedirectResponse (url ="/svit/admin/register?success=true",status_code =303 )
    except Exception :
        return RedirectResponse (url ="/svit/admin/register?error=true",status_code =303 )
    finally :
        db .close ()


@router .post ("/issue/delete/{issue_id}")
def delete_issue (issue_id :int ,request :Request ):
    auth_check =ensure_authenticated (request )
    if auth_check :
        return auth_check 

    db =get_svit_db_sync ()

    try :
        issue =db .query (Issue ).filter (Issue .id ==issue_id ).first ()
        if issue :
            db .delete (issue )
            db .commit ()
        return RedirectResponse (url ="/svit/?success=true",status_code =303 )

    except Exception :
        return RedirectResponse (url ="/svit/?error=true",status_code =303 )
    finally :
        db .close ()


@router .post ("/issue/create")
def create_issue (
request :Request ,
shuttle_id_actual :str =Form (default =""),
status :str =Form (default ="NEW"),
title :str =Form (default =""),
issue_phenomenon :str =Form (default =""),
temp :str =Form (default =""),
input_v :str =Form (default =""),
frequency :str =Form (default =""),
pattern :str =Form (default =""),
expected_from_paste: str = Form(default=""),
countermeasure_from_paste: str = Form(default=""),
log_attach :List [UploadFile ]=File (None ),
expected_root_attach: List[UploadFile] = File(None),
countermeasure_attach: List[UploadFile] = File(None),
):
    auth_check =ensure_authenticated (request )
    if auth_check :
        return auth_check 

    db =get_svit_db_sync ()

    try :
        shuttle_id =shuttle_id_actual if shuttle_id_actual else ""

        temp_value =float (temp )if temp and temp .strip ()else None 

        shuttle =db .query (Shuttle ).filter (Shuttle .shuttle_id ==shuttle_id ).first ()
        node =shuttle .node if shuttle else None 
        ip_ic =shuttle .ip_ic if shuttle else None 
        family =shuttle .family if shuttle else None 


        shuttle_prefix =shuttle_id .split ('_')[0 ]if '_'in shuttle_id else shuttle_id 

        existing_issues =db .query (Issue ).filter (
        Issue .tracking_no .like (f"{shuttle_prefix }_%")
        ).all ()

        max_sequence =0 
        for issue in existing_issues :
            try :
                seq_str =issue .tracking_no .split ('_')[-1 ]
                seq =int (seq_str )
                if seq >max_sequence :
                    max_sequence =seq 
            except (ValueError ,IndexError ):
                pass 

        next_sequence =max_sequence +1 
        tracking_no =f"{shuttle_prefix }_{next_sequence :04d}"

        creator =request .session .get ("english_name")or request .session .get ("user_name","Unknown")

        issue =Issue (
        tracking_no =tracking_no ,
        shuttle_id =shuttle_id ,
        node =node ,
        ip_ic =ip_ic ,
        family =family ,
        status =status ,
        issue_phenomenon =issue_phenomenon or title ,
        temp =temp_value ,
        input_v =input_v ,
        frequency =frequency ,
        pattern =pattern ,
        creator =creator ,
        )
        db .add (issue )
        db .commit ()


        saved_paths = []
        saved_expected_paths = []
        saved_counter_paths = []
        upload_errors = []
        upload_expected_errors = []
        upload_counter_errors = []
        upload_dir = BASE_DIR / "uploads" / "svit"

        if log_attach:
            for up in log_attach:
                try:
                    if not up or not up.filename:
                        svit_logger.info(f"svit upload: skipping empty upload entry for issue {issue.id}")
                        continue
                    try:
                        rel_path = save_upload_file(up, upload_dir, issue.id)
                        svit_logger.info(f"svit upload: saved {rel_path} (orig={up.filename}) for issue {issue.id}")
                        saved_paths.append(rel_path)
                    except ValueError as ve:
                        svit_logger.info(f"svit upload: rejected file {up.filename} for issue {issue.id}: {ve}")
                        upload_errors.append(str(ve))
                    except Exception as e:
                        svit_logger.exception(f"svit upload: unexpected error saving {up.filename} for issue {issue.id}: {e}")
                        upload_errors.append('internal_error')
                except Exception:
                    svit_logger.exception(f"Unexpected error handling uploaded file for issue {issue.id}")
                    continue

        # expected/root-cause specific attachments
        if expected_root_attach:
            for up in expected_root_attach:
                try:
                    if not up or not up.filename:
                        svit_logger.info(f"svit expected upload: skipping empty upload entry for issue {issue.id}")
                        continue
                    try:
                        rel_path = save_upload_file(up, upload_dir, issue.id)
                        svit_logger.info(f"svit expected upload: saved {rel_path} (orig={up.filename}) for issue {issue.id}")
                        saved_expected_paths.append(rel_path)
                    except ValueError as ve:
                        svit_logger.info(f"svit expected upload: rejected file {up.filename} for issue {issue.id}: {ve}")
                        upload_expected_errors.append(str(ve))
                    except Exception as e:
                        svit_logger.exception(f"svit expected upload: unexpected error saving {up.filename} for issue {issue.id}: {e}")
                        upload_expected_errors.append('internal_error')
                except Exception:
                    svit_logger.exception(f"Unexpected error handling expected upload for issue {issue.id}")
                    continue

        # If paste-origin files were sent but parsed into saved_paths, move them to expected list
        if expected_from_paste and saved_paths and not saved_expected_paths:
            svit_logger.info(f"create_issue: moving saved_paths to expected_root_attach due to expected_from_paste for issue {issue.id}: {saved_paths}")
            saved_expected_paths = saved_paths
            saved_paths = []

        # countermeasure specific attachments
        if countermeasure_attach:
            for up in countermeasure_attach:
                try:
                    if not up or not up.filename:
                        svit_logger.info(f"svit counter upload: skipping empty upload entry for issue {issue.id}")
                        continue
                    try:
                        rel_path = save_upload_file(up, upload_dir, issue.id)
                        svit_logger.info(f"svit counter upload: saved {rel_path} (orig={up.filename}) for issue {issue.id}")
                        saved_counter_paths.append(rel_path)
                    except ValueError as ve:
                        svit_logger.info(f"svit counter upload: rejected file {up.filename} for issue {issue.id}: {ve}")
                        upload_counter_errors.append(str(ve))
                    except Exception as e:
                        svit_logger.exception(f"svit counter upload: unexpected error saving {up.filename} for issue {issue.id}: {e}")
                        upload_counter_errors.append('internal_error')
                except Exception:
                    svit_logger.exception(f"Unexpected error handling counter upload for issue {issue.id}")
                    continue

        # If paste-origin files were sent but parsed into saved_paths, move them to countermeasure list
        if countermeasure_from_paste and saved_paths and not saved_counter_paths:
            svit_logger.info(f"create_issue: moving saved_paths to countermeasure_attach due to countermeasure_from_paste for issue {issue.id}: {saved_paths}")
            saved_counter_paths = saved_paths
            saved_paths = []

        if saved_paths:
            issue.log_attach = ",".join([p.as_posix() for p in saved_paths])
            db.add(issue)
            db.commit()

        if saved_expected_paths:
            issue.expected_root_attach = ",".join([p.as_posix() for p in saved_expected_paths])
            db.add(issue)
            db.commit()
            svit_logger.info(f"create_issue: expected_root_attach set for issue {issue.id}: {issue.expected_root_attach}")

        if saved_counter_paths:
            issue.countermeasure_attach = ",".join([p.as_posix() for p in saved_counter_paths])
            db.add(issue)
            db.commit()
            svit_logger.info(f"create_issue: countermeasure_attach set for issue {issue.id}: {issue.countermeasure_attach}")

        # If there were upload errors, log and respond accordingly
        if upload_errors or upload_expected_errors or upload_counter_errors:
            svit_logger.info(f"Issue {issue.id} created with upload errors: {upload_errors + upload_expected_errors + upload_counter_errors}")
            if request.headers.get('x-requested-with','').lower() == 'xmlhttprequest':
                return JSONResponse({'ok': False, 'upload_error': True})
            return RedirectResponse(url=f"/svit/?success=false&upload_error=true", status_code=303)

        # Success response
        if request.headers.get('x-requested-with','').lower() == 'xmlhttprequest':
            return JSONResponse({'ok': True, 'issue_id': issue.id, 'log_attach': issue.log_attach, 'expected_root_attach': issue.expected_root_attach, 'countermeasure_attach': issue.countermeasure_attach})
        return RedirectResponse (url ="/svit/?success=true",status_code =303 )

    except Exception :
        if request.headers.get('x-requested-with','').lower() == 'xmlhttprequest':
            return JSONResponse({'ok': False, 'error': True})
        return RedirectResponse (url ="/svit/?error=true",status_code =303 )
    finally :
        db .close ()


@router .post ("/issue/update/{issue_id}")
async def update_issue (
issue_id :int ,
request :Request ,
status :str =Form (default ="NEW"),
issue_phenomenon :str =Form (default =""),
temp :str =Form (default =""),
frequency :str =Form (default =""),
pattern :str =Form (default =""),
 expected_root_cause: str = Form(default=""),
 countermeasure: str = Form(default=""),
 expected_from_paste: str = Form(default=""),
 countermeasure_from_paste: str = Form(default=""),
log_attach :List [UploadFile ]=File (None ),
expected_root_attach: List[UploadFile] = File(None),
countermeasure_attach: List[UploadFile] = File(None),
):
    auth_check =ensure_authenticated (request )
    if auth_check :
        return auth_check 

    db =get_svit_db_sync ()

    try :
        # Debug: capture raw FormData keys and attached filenames to diagnose client uploads
        try:
            form = await request.form()
            keys = list(form.keys())
            details = []
            for k in keys:
                values = form.getlist(k) if hasattr(form, 'getlist') else [form[k]]
                for v in values:
                    if hasattr(v, 'filename'):
                        details.append((k, getattr(v, 'filename', None)))
                    else:
                        details.append((k, str(v)[:200]))
            svit_logger.info(f"update_issue: raw form keys for issue {issue_id}: {keys}, details: {details}")
            try:
                hdrs = dict(request.headers)
                svit_logger.info(f"update_issue: request headers for issue {issue_id}: {hdrs}")
            except Exception:
                pass
        except Exception as _e:
            svit_logger.exception(f"update_issue: error reading raw form for issue {issue_id}: {_e}")

        temp_value =float (temp )if temp and temp .strip ()else None 

        issue =db .query (Issue ).filter (Issue .id ==issue_id ).first ()
        if not issue :
            raise HTTPException (status_code =404 ,detail ="Issue not found")


        new_paths = []
        new_expected_paths = []
        new_counter_paths = []
        upload_errors = []
        upload_expected_errors = []
        upload_counter_errors = []
        upload_dir = BASE_DIR / "uploads" / "svit"

        # Debug: log incoming file fields and filenames to diagnose where pasted images are routed
        try:
            la_files = [lf.filename for lf in (log_attach or []) if getattr(lf, 'filename', None)]
        except Exception:
            la_files = []
        try:
            er_files = [ef.filename for ef in (expected_root_attach or []) if getattr(ef, 'filename', None)]
        except Exception:
            er_files = []
        try:
            cm_files = [cf.filename for cf in (countermeasure_attach or []) if getattr(cf, 'filename', None)]
        except Exception:
            cm_files = []
        svit_logger.info(f"update_issue: incoming files for issue {issue_id}: log_attach={la_files}, expected_root_attach={er_files}, countermeasure_attach={cm_files}")

        if log_attach:
            for lf in log_attach:
                try:
                    if not lf or not lf.filename:
                        svit_logger.info(f"svit upload (update): skipping empty upload entry for issue {issue_id}")
                        continue
                    try:
                        rel = save_upload_file(lf, upload_dir, issue_id)
                        svit_logger.info(f"svit upload (update): saved {rel} (orig={lf.filename}) for issue {issue_id}")
                        new_paths.append(rel.as_posix())
                    except ValueError as ve:
                        svit_logger.info(f"svit upload (update): rejected file {lf.filename} for issue {issue_id}: {ve}")
                        upload_errors.append(str(ve))
                    except Exception as e:
                        svit_logger.exception(f"svit upload (update): unexpected error saving {lf.filename} for issue {issue_id}: {e}")
                        upload_errors.append('internal_error')
                except Exception:
                    svit_logger.exception(f"Unexpected error handling uploaded file for issue {issue_id}")
                    continue
        # expected/root-cause specific attachments (update)
        if expected_root_attach:
            for lf in expected_root_attach:
                try:
                    if not lf or not lf.filename:
                        svit_logger.info(f"svit expected upload (update): skipping empty upload entry for issue {issue_id}")
                        continue
                    try:
                        rel = save_upload_file(lf, upload_dir, issue_id)
                        svit_logger.info(f"svit expected upload (update): saved {rel} (orig={lf.filename}) for issue {issue_id}")
                        new_expected_paths.append(rel.as_posix())
                    except ValueError as ve:
                        svit_logger.info(f"svit expected upload (update): rejected file {lf.filename} for issue {issue_id}: {ve}")
                        upload_expected_errors.append(str(ve))
                    except Exception as e:
                        svit_logger.exception(f"svit expected upload (update): unexpected error saving {lf.filename} for issue {issue_id}: {e}")
                        upload_expected_errors.append('internal_error')
                except Exception:
                    svit_logger.exception(f"Unexpected error handling expected upload for issue {issue_id}")
                    continue

        # countermeasure specific attachments (update)
        if countermeasure_attach:
            for lf in countermeasure_attach:
                try:
                    if not lf or not lf.filename:
                        svit_logger.info(f"svit counter upload (update): skipping empty upload entry for issue {issue_id}")
                        continue
                    try:
                        rel = save_upload_file(lf, upload_dir, issue_id)
                        svit_logger.info(f"svit counter upload (update): saved {rel} (orig={lf.filename}) for issue {issue_id}")
                        new_counter_paths.append(rel.as_posix())
                    except ValueError as ve:
                        svit_logger.info(f"svit counter upload (update): rejected file {lf.filename} for issue {issue_id}: {ve}")
                        upload_counter_errors.append(str(ve))
                    except Exception as e:
                        svit_logger.exception(f"svit counter upload (update): unexpected error saving {lf.filename} for issue {issue_id}: {e}")
                        upload_counter_errors.append('internal_error')
                except Exception:
                    svit_logger.exception(f"Unexpected error handling counter upload for issue {issue_id}")
                    continue

        svit_logger.info(f"update_issue: processed new_paths={new_paths}, new_expected_paths={new_expected_paths}")

        # If paste-origin files were sent but ended up in new_paths, and the client indicated expected_from_paste,
        # move them into expected_root_attach instead of log_attach.
        if expected_from_paste and new_paths and not new_expected_paths:
            svit_logger.info(f"update_issue: moving new_paths to expected_root_attach due to expected_from_paste for issue {issue_id}: {new_paths}")
            new_expected_paths.extend(new_paths)
            new_paths = []

        if countermeasure_from_paste and new_paths and not new_counter_paths:
            svit_logger.info(f"update_issue: moving new_paths to countermeasure_attach due to countermeasure_from_paste for issue {issue_id}: {new_paths}")
            new_counter_paths.extend(new_paths)
            new_paths = []

        if new_paths:
            existing = []
            if issue.log_attach:
                existing = [p.strip().lstrip('/').replace('\\','/') for p in issue.log_attach.split(',') if p.strip()]
            combined = existing + new_paths
            issue.log_attach = ",".join(combined)

        if upload_errors or upload_expected_errors or upload_counter_errors:
            svit_logger.info(f"Issue {issue_id} updated with upload errors: {upload_errors + upload_expected_errors + upload_counter_errors}")
            if request.headers.get('x-requested-with','').lower() == 'xmlhttprequest':
                return JSONResponse({'ok': False, 'upload_error': True})
            return RedirectResponse(url=f"/svit/issue/{issue_id}?success=false&upload_error=true", status_code=303)

        if new_expected_paths:
            existing_expected = []
            if issue.expected_root_attach:
                existing_expected = [p.strip().lstrip('/').replace('\\','/') for p in issue.expected_root_attach.split(',') if p.strip()]
            combined_expected = existing_expected + new_expected_paths
            issue.expected_root_attach = ",".join(combined_expected)
            svit_logger.info(f"update_issue: expected_root_attach for issue {issue_id} updated to: {issue.expected_root_attach}")

        if new_counter_paths:
            existing_counter = []
            if issue.countermeasure_attach:
                existing_counter = [p.strip().lstrip('/').replace('\\','/') for p in issue.countermeasure_attach.split(',') if p.strip()]
            combined_counter = existing_counter + new_counter_paths
            issue.countermeasure_attach = ",".join(combined_counter)
            svit_logger.info(f"update_issue: countermeasure_attach for issue {issue_id} updated to: {issue.countermeasure_attach}")

        issue .status =status 
        issue .issue_phenomenon =issue_phenomenon or issue .issue_phenomenon 
        issue .expected_root_cause = expected_root_cause or issue.expected_root_cause
        issue .countermeasure = countermeasure or issue.countermeasure
        issue .temp =temp_value 
        issue .frequency =frequency or issue .frequency 
        issue .pattern =pattern or issue .pattern 

        db .commit ()
        # Success response
        if request.headers.get('x-requested-with','').lower() == 'xmlhttprequest':
            return JSONResponse({'ok': True, 'issue_id': issue_id, 'log_attach': issue.log_attach, 'expected_root_attach': issue.expected_root_attach, 'countermeasure_attach': issue.countermeasure_attach})
        return RedirectResponse (url =f"/svit/issue/{issue_id }?success=true",status_code =303 )

    except Exception :
        if request.headers.get('x-requested-with','').lower() == 'xmlhttprequest':
            return JSONResponse({'ok': False, 'error': True})
        return RedirectResponse (url =f"/svit/issue/{issue_id }?error=true",status_code =303 )
    finally :
        db .close ()


@router.post('/issue/{issue_id}/file-delete')
def delete_issue_file(issue_id: int, request: Request, path: str = Form(...)):
    auth_check = ensure_authenticated(request)
    if auth_check:
        return auth_check

    db = get_svit_db_sync()
    issue = db.query(Issue).filter(Issue.id == issue_id).first()
    if not issue:
        raise HTTPException(status_code=404, detail='Issue not found')

    p = path.lstrip('/').replace('\\', '/')
    log_existing = [s.strip().lstrip('/').replace('\\', '/') for s in (issue.log_attach or '').split(',') if s.strip()]
    expected_existing = [s.strip().lstrip('/').replace('\\', '/') for s in (issue.expected_root_attach or '').split(',') if s.strip()]
    counter_existing = [s.strip().lstrip('/').replace('\\', '/') for s in (issue.countermeasure_attach or '').split(',') if s.strip()]

    # Determine if the path belongs to log attachments, expected-root attachments, or countermeasure attachments
    target_column = None
    if p in log_existing:
        target_column = 'log'
    elif p in expected_existing:
        target_column = 'expected'
    elif p in counter_existing:
        target_column = 'counter'
    else:
        # try fuzzy matching by suffix
        found = False
        for existing_path in log_existing:
            if existing_path.endswith(p) or p.endswith(existing_path) or existing_path == p:
                p = existing_path
                target_column = 'log'
                found = True
                break
        if not found:
            for existing_path in expected_existing:
                if existing_path.endswith(p) or p.endswith(existing_path) or existing_path == p:
                    p = existing_path
                    target_column = 'expected'
                    found = True
                    break
        if not found:
            for existing_path in counter_existing:
                if existing_path.endswith(p) or p.endswith(existing_path) or existing_path == p:
                    p = existing_path
                    target_column = 'counter'
                    found = True
                    break
        if not found:
            raise HTTPException(status_code=404, detail=f'File not associated. Looking for: {p}, Available: {log_existing + expected_existing + counter_existing}')

    try:
        full = BASE_DIR / p
        if full.exists():
            full.unlink()
            try:
                from core.config import BASE_DIR as PROJECT_BASE
                import logging
                LOG_DIR = PROJECT_BASE / 'logs'
                LOG_DIR.mkdir(parents=True, exist_ok=True)
                logger = logging.getLogger('file_deletions')
                if not logger.handlers:
                    fh = logging.FileHandler(LOG_DIR / 'file_deletions.log', encoding='utf-8')
                    fh.setFormatter(logging.Formatter('%(asctime)s\t%(levelname)s\t%(message)s'))
                    logger.addHandler(fh)
                    logger.setLevel(logging.INFO)
                logger.info(f"svit\t{p.split('/')[-1]}\tuser={request.session.get('email') or 'anon'}\tip={getattr(request.client,'host','unknown')}\tdeleted")
            except Exception:
                pass
    except Exception:
        pass

    if target_column == 'log':
        remaining = [s for s in log_existing if s != p]
        issue.log_attach = ','.join(remaining)
        db.add(issue)
        db.commit()
        return {'ok': True, 'remaining': issue.log_attach}
    elif target_column == 'expected':
        remaining = [s for s in expected_existing if s != p]
        issue.expected_root_attach = ','.join(remaining)
        db.add(issue)
        db.commit()
        return {'ok': True, 'remaining': issue.expected_root_attach}
    else:  # counter
        remaining = [s for s in counter_existing if s != p]
        issue.countermeasure_attach = ','.join(remaining)
        db.add(issue)
        db.commit()
        return {'ok': True, 'remaining': issue.countermeasure_attach}
