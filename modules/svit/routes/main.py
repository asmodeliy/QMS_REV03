

from fastapi import APIRouter ,Request ,HTTPException ,Form ,UploadFile ,File 
from typing import List 
from fastapi .responses import HTMLResponse ,RedirectResponse 
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
    filename = re.sub(r'[#?&=%;]', '_', filename)
    filename = re.sub(r'\s+', '_', filename)
    return filename

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
log_attach :List [UploadFile ]=File (None ),
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


        saved_paths =[]
        if log_attach :
            upload_dir = BASE_DIR / "uploads" / "svit"
            upload_dir.mkdir(parents=True, exist_ok=True)
            svit_logger.info(f"svit upload: {len(log_attach)} file(s) received for issue {issue.id}")
            for up in log_attach :
                try:
                    if not up or not up .filename :
                        svit_logger.info(f"svit upload: skipping empty upload entry for issue {issue.id}")
                        continue 
                    timestamp =datetime .now ().strftime ("%Y%m%d_%H%M%S")
                    safe_name = sanitize_filename(Path (up .filename ).name)
                    unique_filename =f"issue_{issue .id }_{timestamp }_{safe_name }"
                    file_path =upload_dir /unique_filename 

                    # read and write with error handling
                    try:
                        contents = up.file.read()
                    except Exception as e:
                        svit_logger.exception(f"Error reading uploaded file {up.filename} for issue {issue.id}: {e}")
                        continue

                    try:
                        with open (file_path ,"wb")as f :
                            f .write (contents )
                    except Exception as e:
                        svit_logger.exception(f"Error writing uploaded file to disk {file_path} for issue {issue.id}: {e}")
                        continue

                    svit_logger.info(f"svit upload: saved {unique_filename} (orig={up.filename}) for issue {issue.id}")
                    saved_paths .append (Path ("uploads")/"svit"/unique_filename )
                except Exception:
                    svit_logger.exception(f"Unexpected error handling uploaded file for issue {issue.id}")
                    continue

        if saved_paths :

            issue .log_attach =",".join ([p .as_posix ()for p in saved_paths ])
            db .add (issue )
            db .commit ()

        return RedirectResponse (url ="/svit/?success=true",status_code =303 )

    except Exception :
        return RedirectResponse (url ="/svit/?error=true",status_code =303 )
    finally :
        db .close ()


@router .post ("/issue/update/{issue_id}")
def update_issue (
issue_id :int ,
request :Request ,
status :str =Form (default ="NEW"),
issue_phenomenon :str =Form (default =""),
temp :str =Form (default =""),
frequency :str =Form (default =""),
pattern :str =Form (default =""),
 expected_root_cause: str = Form(default=""),
 countermeasure: str = Form(default=""),
log_attach :List [UploadFile ]=File (None ),
):
    auth_check =ensure_authenticated (request )
    if auth_check :
        return auth_check 

    db =get_svit_db_sync ()

    try :
        temp_value =float (temp )if temp and temp .strip ()else None 

        issue =db .query (Issue ).filter (Issue .id ==issue_id ).first ()
        if not issue :
            raise HTTPException (status_code =404 ,detail ="Issue not found")


        new_paths =[]
        if log_attach :
            upload_dir = BASE_DIR / "uploads" / "svit"
            upload_dir.mkdir(parents=True, exist_ok=True)
            svit_logger.info(f"svit upload (update): {len(log_attach)} file(s) received for issue {issue_id}")
            for lf in log_attach :
                try:
                    if not lf or not lf .filename :
                        svit_logger.info(f"svit upload (update): skipping empty upload entry for issue {issue_id}")
                        continue 
                    timestamp =datetime .now ().strftime ("%Y%m%d_%H%M%S")
                    safe_name = sanitize_filename(Path (lf .filename ).name)
                    unique_filename =f"issue_{issue_id }_{timestamp }_{safe_name }"
                    file_path =upload_dir /unique_filename 

                    try:
                        contents = lf.file.read()
                    except Exception as e:
                        svit_logger.exception(f"Error reading uploaded file {lf.filename} for issue {issue_id}: {e}")
                        continue

                    try:
                        with open (file_path ,"wb")as f :
                            f .write (contents )
                    except Exception as e:
                        svit_logger.exception(f"Error writing uploaded file to disk {file_path} for issue {issue_id}: {e}")
                        continue

                    svit_logger.info(f"svit upload (update): saved {unique_filename} (orig={lf.filename}) for issue {issue_id}")
                    new_paths .append ((Path ("uploads")/"svit"/unique_filename ).as_posix ())
                except Exception:
                    svit_logger.exception(f"Unexpected error handling uploaded file for issue {issue_id}")
                    continue

        if new_paths :
            existing =[]
            if issue .log_attach :

                existing =[p .strip ().lstrip ('/').replace ('\\','/')for p in issue .log_attach .split (',')if p .strip ()]
            combined =existing +new_paths 
            issue .log_attach =",".join (combined )

        issue .status =status 
        issue .issue_phenomenon =issue_phenomenon or issue .issue_phenomenon 
        issue .expected_root_cause = expected_root_cause or issue.expected_root_cause
        issue .countermeasure = countermeasure or issue.countermeasure
        issue .temp =temp_value 
        issue .frequency =frequency or issue .frequency 
        issue .pattern =pattern or issue .pattern 

        db .commit ()
        return RedirectResponse (url =f"/svit/issue/{issue_id }?success=true",status_code =303 )

    except Exception :
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
    existing = [s.strip().lstrip('/').replace('\\', '/') for s in (issue.log_attach or '').split(',') if s.strip()]
    
    if p not in existing:
        found = False
        for existing_path in existing:
            if existing_path.endswith(p) or p.endswith(existing_path) or existing_path == p:
                p = existing_path
                found = True
                break
        
        if not found:
            raise HTTPException(status_code=404, detail=f'File not associated. Looking for: {p}, Available: {existing}')

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

    remaining = [s for s in existing if s != p]
    issue.log_attach = ','.join(remaining)
    db.add(issue)
    db.commit()
    return {'ok': True, 'remaining': issue.log_attach}
