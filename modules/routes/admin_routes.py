from typing import Optional 
from datetime import date ,datetime 
import shutil 

from fastapi import APIRouter ,Request ,Depends ,Form ,UploadFile ,HTTPException 
from fastapi .responses import HTMLResponse ,RedirectResponse ,FileResponse ,PlainTextResponse ,JSONResponse 
from sqlalchemy .orm import Session 
from sqlalchemy import select 

from models import Project ,Task ,StatusEnum ,User ,PendingUser ,PDKDKEntry 
from core .db import get_db ,engine 
from core .config import BASE_DIR ,DB_PATH 
from core .utils import (
build_groups_keep_order ,
get_visit_token ,
build_redirect_url 
)
from data .default_tasks import DEFAULT_TASK_TEMPLATE 
from core .i18n import get_locale 
from datetime import datetime as dt 

router =APIRouter ()

import logging
logger = logging.getLogger(__name__)

templates =None 

def set_templates (tmpl ):
    global templates 
    templates =tmpl


def ensure_admin_html (request :Request )->Optional [RedirectResponse ]:
    if not request .session .get ("is_authenticated"):
        return RedirectResponse (url =f"/auth/login?next={request .url }",status_code =303 )
    if request .session .get ("role")!="Admin":
        return ("access_denied",)

    return None 


def ensure_admin_api (request :Request )->Optional [RedirectResponse ]:
    if not request .session .get ("is_authenticated"):
        raise HTTPException (status_code =401 ,detail ="Not authenticated")

    if request .session .get ("role")!="Admin":
        raise HTTPException (status_code =403 ,detail ="Admin access required")

    return None 


@router.get("/admin/admin/system/status",response_class =JSONResponse )
def admin_system_status (request :Request ,db :Session =Depends (get_db )):
    ensure_admin_api (request )

    from sqlalchemy import text 

    project_count =db .execute (text ("SELECT COUNT(1) FROM projects")).scalar_one ()
    task_count =db .execute (text ("SELECT COUNT(1) FROM tasks")).scalar_one ()

    uploads_dir =BASE_DIR /"uploads"
    total_files =0 
    total_bytes =0 
    if uploads_dir .exists ():
        for p in uploads_dir .rglob ("*"):
            if p .is_file ():
                total_files +=1 
                try :
                    total_bytes +=p .stat ().st_size 
                except OSError :
                    continue 

    return {
    "project_count":project_count ,
    "task_count":task_count ,
    "uploads_files":total_files ,
    "uploads_bytes":total_bytes ,
    "db_path":str (DB_PATH ),
    }


@router.get("/admin/admin",response_class =HTMLResponse )
def admin_home (request :Request ,db :Session =Depends (get_db )):
    r =ensure_admin_html (request )
    if r :
        if isinstance (r ,tuple )and r [0 ]=="access_denied":
            locale =get_locale (request )
            return templates .TemplateResponse ("shared/access_denied.html",{
            "request":request ,
            "locale":locale ,
            })
        return r 

    locale =get_locale (request )
    projects =db .execute (
    select (Project ).where (Project .active ==True ).order_by (Project .id .desc ())
    ).scalars ().all ()

    focus =request .query_params .get ("focus")
    return templates .TemplateResponse ("modules/rpmt/admin.html",{
    "request":request ,
    "projects":projects ,
    "locale":locale ,
    "visit":get_visit_token (request ),
    "focus":focus ,
    })


@router.get("/admin/admin/archive",response_class =HTMLResponse )
def admin_archive (request :Request ,db :Session =Depends (get_db )):
    r =ensure_admin_html (request )
    if r :
        if isinstance (r ,tuple )and r [0 ]=="access_denied":
            locale =get_locale (request )
            return templates .TemplateResponse ("shared/access_denied.html",{
            "request":request ,
            "locale":locale ,
            })
        return r 

    locale =get_locale (request )
    archived_projects =db .execute (
    select (Project ).where (Project .active ==False ).order_by (Project .id .desc ())
    ).scalars ().all ()

    return templates .TemplateResponse ("modules/rpmt/admin_archive.html",{
    "request":request ,
    "projects":archived_projects ,
    "locale":locale ,
    "visit":get_visit_token (request ),
    })


@router.post("/admin/admin/projects/{pid}/restore")
def admin_project_restore (pid :int ,request :Request ,db :Session =Depends (get_db )):
    ensure_admin_api (request )
    p =db .get (Project ,pid )
    if not p :
        raise HTTPException (status_code =404 ,detail ="Project not found")
    p .active =True 
    db .commit ()
    return RedirectResponse (build_redirect_url ("/rpmt/admin/archive",request ),status_code =303 )


@router.get("/admin/admin/projects/{pid}/tasks",response_class =HTMLResponse )
def admin_tasks (pid :int ,request :Request ,db :Session =Depends (get_db )):
    ensure_admin_api (request )

    p =db .get (Project ,pid )
    if not p :
        raise HTTPException (status_code =404 ,detail ="Project not found")

    active_tasks =[t for t in p .tasks if not (t .archived or False )]
    groups =build_groups_keep_order (active_tasks )
    
    pdk_dk_entries = []
    try:
        entries = db.query(PDKDKEntry).filter(PDKDKEntry.project_id == pid).all()
                                  
        category_order = [
            'DFM', 'DRC', 'EM', 'ESD', 'ETC', 'Fill', 'FLT', 'LVS', 
            'MODEL', 'PDKLib', 'PEX', 'PnR', 
            'Standard Cell', 'Memory', 'CDM ESD', 'GPIO', 'HSIO', 'Power ESD', 'CDM B2B'
        ]
                                                     
        order_map = {cat: idx for idx, cat in enumerate(category_order)}
                                                                      
        def sort_key(entry):
            type_order = 0 if entry.type == 'PDK' else (1 if entry.type == 'DK' else 2)
            category_order_idx = order_map.get(entry.category, 999)
            return (type_order, category_order_idx)
        pdk_dk_entries = sorted(entries, key=sort_key)
    except:
        pass                           

    return templates .TemplateResponse ("modules/rpmt/_includes/admin_tasks_table.html",{
    "request":request ,
    "p":p ,
    "groups":groups ,
    "StatusEnum":StatusEnum ,
    "visit":get_visit_token (request ) ,
    "pdk_dk_entries":pdk_dk_entries
    })


@router.post("/admin/admin/projects/create")
def admin_project_create (
request :Request ,
code :str =Form (...),
process :str =Form (""),
metal_option :str =Form (""),
ip_code :str =Form (""),
pdk_ver :str =Form (""),
template :bool =Form (False ),
db :Session =Depends (get_db )
):
    ensure_admin_api (request )

    p =Project (
    code =code ,
    process =process ,
    metal_option =metal_option ,
    ip_code =ip_code ,
    pdk_ver =pdk_ver 
    )
    db .add (p )
    db .flush ()

    if template :
        counters ={}
        for cat1 ,cat2 ,frm ,to in DEFAULT_TASK_TEMPLATE :
            k =cat1 or ""
            counters [k ]=counters .get (k ,0 )+1 
            db .add (Task (
            project_id =p .id ,
            cat1 =cat1 ,
            cat2 =cat2 ,
            dept_from =frm ,
            dept_to =to ,
            due_date =None ,
            status =StatusEnum .NOT_STARTED ,
            reason =None ,
            ord =counters [k ]
            ))

    db .commit ()
    return RedirectResponse (url =build_redirect_url (f"/rpmt/admin?focus={p .id }",request ),status_code =303 )

@router.post("/admin/admin/projects/{pid}/update")
def admin_project_update (
request :Request ,
pid :int ,
code :str =Form (...),
process :str =Form (""),
metal_option :str =Form (""),
ip_code :str =Form (""),
pdk_ver :str =Form (""),
db :Session =Depends (get_db )
):
    ensure_admin_api (request )
    p =db .get (Project ,pid )
    if not p :raise HTTPException (404 )
    p .code =code 
    p .process =process 
    p .metal_option =metal_option 
    p .ip_code =ip_code 
    p .pdk_ver =pdk_ver 
    db .commit ()
    return RedirectResponse (build_redirect_url (f"/rpmt/admin?focus={pid }",request ),status_code =303 )


@router.post("/admin/admin/projects/{pid}/archive")
def admin_project_archive (
pid :int ,
request :Request ,
db :Session =Depends (get_db ),
):
    ensure_admin_api (request )
    p =db .get (Project ,pid )
    if not p :
        raise HTTPException (status_code =404 ,detail ="Project not found")
    p .active =False 
    db .commit ()
    return RedirectResponse (build_redirect_url ("/rpmt/admin",request ),status_code =303 )

@router.post("/admin/admin/projects/{pid}/delete")
def admin_project_delete (pid :int ,request :Request ,db :Session =Depends (get_db )):
    ensure_admin_api (request )
    p =db .get (Project ,pid )
    if p :
        db .delete (p );db .commit ()
    return RedirectResponse (build_redirect_url ("/rpmt/admin",request ),status_code =303 )

@router.post("/admin/admin/tasks/create")
def admin_task_create (
request :Request ,
project_id :int =Form (...),
cat1 :str =Form (""),
cat2 :str =Form (""),
dept_from :str =Form (""),
dept_to :str =Form (""),
due_date :str =Form (None ),
status :str =Form ("Not Started"),
reason :str =Form (""),
below_tid :Optional [int ]=Form (None ),
db :Session =Depends (get_db ),
):
    ensure_admin_api (request )

    due =date .fromisoformat (due_date )if due_date else None 

    ord_val =None 
    if below_tid :
        base =db .get (Task ,below_tid )
        if base :
            base_ord =base .ord or 0 
            siblings =db .execute (
            select (Task ).where (
            Task .project_id ==base .project_id ,
            Task .cat1 ==(base .cat1 or "")
            ).order_by (Task .ord .asc (),Task .id .asc ())
            ).scalars ().all ()
            for s in siblings :
                if (s .ord or 0 )>base_ord :
                    s .ord =(s .ord or 0 )+1 
            ord_val =base_ord +1 

    member =StatusEnum ._value2member_map_ .get (status ,StatusEnum .NOT_STARTED )
    t =Task (
    project_id =project_id ,
    cat1 =cat1 ,cat2 =cat2 ,dept_from =dept_from ,dept_to =dept_to ,
    due_date =due ,status =member ,reason =reason ,
    ord =ord_val if ord_val is not None else next_ord (db ,project_id ,cat1 or "")
    )
    db .add (t );db .commit ()
    return RedirectResponse (build_redirect_url (f"/rpmt/admin?focus={project_id }",request ),status_code =303 )

@router.post("/admin/admin/tasks/{tid}/update")
def admin_task_update (
request :Request ,tid :int ,
cat1 :str =Form (None ),
cat2 :str =Form (None ),
dept_from :str =Form (None ),
dept_to :str =Form (None ),
due_date :str =Form (None ),
status :str =Form (None ),
reason :str =Form (None ),
ord_val :int =Form (None ),
db :Session =Depends (get_db ),
):
    ensure_admin_api (request )
    t =db .get (Task ,tid )
    if not t :raise HTTPException (404 )
    pid_for_focus =t .project_id 

    old_cat1 =t .cat1 or ""

    if cat1 is not None :t .cat1 =cat1 or ""
    if cat2 is not None :t .cat2 =cat2 or ""
    if dept_from is not None :t .dept_from =dept_from or ""
    if dept_to is not None :t .dept_to =dept_to or ""
    if due_date is not None :
        t .due_date =date .fromisoformat (due_date )if due_date else None 
    if status is not None and status in StatusEnum ._value2member_map_ :
        t .status =StatusEnum (status )
    if reason is not None :t .reason =reason 

    if ord_val is not None and str (ord_val ).strip ()!="":
        try :
            t .ord =int (ord_val )
        except ValueError :
            pass 
    else :
        new_cat1 =t .cat1 or ""
        if new_cat1 !=old_cat1 :
            t .ord =next_ord (db ,t .project_id ,new_cat1 )

    db .commit ()
    return RedirectResponse (build_redirect_url (f"/rpmt/admin?focus={pid_for_focus }",request ),status_code =303 )

@router.post("/admin/admin/tasks/{tid}/delete")
def admin_task_delete (tid :int ,request :Request ,db :Session =Depends (get_db )):
    ensure_admin_api (request )
    t =db .get (Task ,tid )
    pid_for_focus =t .project_id if t else None 
    if t :
        db .delete (t );db .commit ()
    url ="/rpmt/admin"if not pid_for_focus else f"/rpmt/admin?focus={pid_for_focus }"
    return RedirectResponse (build_redirect_url (url ,request ),status_code =303 )

@router.post("/admin/admin/tasks/{tid}/insert-below")
def admin_task_insert_below (
request :Request ,
tid :int ,
db :Session =Depends (get_db ),
):
    ensure_admin_api (request )

    base =db .get (Task ,tid )
    if not base :
        raise HTTPException (status_code =404 ,detail ="Base task not found")

    pid =base .project_id 
    cat1 =base .cat1 or ""

    siblings =db .execute (
    select (Task ).where (
    Task .project_id ==pid ,
    Task .cat1 ==cat1 
    ).order_by (Task .ord .asc (),Task .id .asc ())
    ).scalars ().all ()

    base_ord =base .ord or 0 
    for s in siblings :
        if (s .ord or 0 )>base_ord :
            s .ord =(s .ord or 0 )+1 

    new_task =Task (
    project_id =pid ,
    cat1 =cat1 ,
    cat2 ="",
    dept_from ="",
    dept_to ="",
    due_date =None ,
    status =StatusEnum .NOT_STARTED ,
    reason ="",
    ord =base_ord +1 
    )
    db .add (new_task )
    db .commit ()

    focus_url =f"/rpmt/admin?focus={pid }"
    return RedirectResponse (build_redirect_url (focus_url ,request ),status_code =303 )

@router.get("/admin/admin/backup")
def admin_backup (request :Request ):
    ensure_admin_api (request )
    if not DB_PATH .exists ():
        raise HTTPException (404 ,"DB 파일을 찾을 수 없습니다.")
    ts =datetime .now ().strftime ("%Y%m%d_%H%M%S")
    out =DB_PATH .parent /f"rpmt_backup_{ts }.db"
    shutil .copyfile (DB_PATH ,out )
    return FileResponse (path =str (out ),filename =out .name ,media_type ="application/octet-stream")

@router.post("/admin/admin/restore")
def admin_restore (request :Request ,file :UploadFile ):
    ensure_admin_api (request )
    if not file :
        raise HTTPException (400 ,"파일이 첨부되지 않았습니다.")
    tmp =DB_PATH .parent /"_upload_restore.db"
    tmp .write_bytes (file .file .read ())

    try :
        import sqlite3 as _sq 
        _sq .connect (tmp ).close ()
    except Exception :
        tmp .unlink (missing_ok =True )
        raise HTTPException (400 ,"유효한 SQLite 파일이 아닙니다.")

    try :
        engine .dispose ()
        backup_before =DB_PATH .parent /f"rpmt_before_restore_{datetime .now ().strftime ('%Y%m%d_%H%M%S')}.db"
        if DB_PATH .exists ():
            shutil .copyfile (DB_PATH ,backup_before )
            DB_PATH .unlink (missing_ok =True )
        shutil .move (tmp ,DB_PATH )
    finally :
        pass
    return RedirectResponse (build_redirect_url ("/rpmt/admin",request ),status_code =303 )


@router.post("/admin/test/simple-post")
async def test_simple_post(request: Request):
    """Ultra simple test - no auth, no validation"""
    logger.info("[TEST-SIMPLE] POST called!")
    try:
        data = await request.json()
        logger.debug("[TEST-SIMPLE] Got data: %s", data)
        return {"ok": True, "data": data}
    except Exception as e:
        logger.exception("[TEST-SIMPLE] Error processing request")
        return {"ok": False, "error": str(e)}



@router.post("/admin/test-simple-post", response_class=JSONResponse)
def test_simple(project_id: int = None, category: str = None):
    if not project_id or not category:
        return {"ok": False, "error": "Missing parameters"}
    return {"ok": True, "message": "테스트 성공", "received": {"project_id": project_id, "category": category}}


@router.post("/admin/api/pdkdk/save", response_class=JSONResponse)
async def save_pdkdk(request: Request, db: Session = Depends(get_db)):
    """새로운 PDKDK 항목 생성"""
    try:
        params = dict(request.query_params)
        project_id = params.get('project_id')
        category = params.get('category')
        type_val = params.get('type')
        
        logger.info("[PDKDK-SAVE] Params received: project_id=%s, category=%s, type=%s", project_id, category, type_val)
        
        if not project_id or not category:
            return {"ok": False, "error": "파라미터 누락"}
        
        project = db.get(Project, int(project_id))
        if not project:
            return {"ok": False, "error": "프로젝트를 찾을 수 없습니다"}
        
        new_entry = PDKDKEntry(
            project_id=int(project_id),
            type=type_val,
            category=category
        )
        db.add(new_entry)
        db.commit()
        db.refresh(new_entry)
        
        return {"ok": True, "id": new_entry.id, "message": "저장 완료"}
    except Exception as e:
        db.rollback()
        return {"ok": False, "error": str(e)}



@router.post("/admin/admin/pdkdk/{entry_id}",response_class =JSONResponse )
async def update_pdkdk_entry (entry_id :int ,request :Request ,db :Session =Depends (get_db )):
    ensure_admin_api (request )
    
    data =await request .json ()
    
    try :
        entry =db .get (PDKDKEntry ,entry_id )
        if not entry :
            raise HTTPException (status_code =404 ,detail ="PDK/DK entry not found")
        
                     
        def parse_date (date_str ):
            if not date_str :
                return None 
            try :
                return datetime .strptime (date_str ,"%Y-%m-%d").date ()
            except :
                return None 
        
                                 
        if "type" in data:
            entry.type = data.get("type") or None
        
                                
        entry .engineer_version_kickoff =data .get ("engineer_version_kickoff") or None 
        entry .qa_version_kickoff =data .get ("qa_version_kickoff") or None 
        entry .engineer_matching_kickoff =data .get ("engineer_matching_kickoff") or None 
        entry .qa_matching_kickoff =data .get ("qa_matching_kickoff") or None 
        entry .engineer_b2b_date_kickoff =parse_date (data .get ("engineer_b2b_date_kickoff"))
        entry .qa_b2b_date_kickoff =parse_date (data .get ("qa_b2b_date_kickoff"))
        entry .engineer_check_date_kickoff =parse_date (data .get ("engineer_check_date_kickoff"))
        entry .qa_check_date_kickoff =parse_date (data .get ("qa_check_date_kickoff"))
        entry .qa_unmatched_reason_kickoff =data .get ("qa_unmatched_reason_kickoff") or None 
        
                             
        entry .engineer_version_tweek =data .get ("engineer_version_tweek") or None 
        entry .qa_version_tweek =data .get ("qa_version_tweek") or None 
        entry .engineer_matching_tweek =data .get ("engineer_matching_tweek") or None 
        entry .qa_matching_tweek =data .get ("qa_matching_tweek") or None 
        entry .engineer_b2b_date_tweek =parse_date (data .get ("engineer_b2b_date_tweek"))
        entry .qa_b2b_date_tweek =parse_date (data .get ("qa_b2b_date_tweek"))
        entry .engineer_check_date_tweek =parse_date (data .get ("engineer_check_date_tweek"))
        entry .qa_check_date_tweek =parse_date (data .get ("qa_check_date_tweek"))
        entry .qa_unmatched_reason_tweek =data .get ("qa_unmatched_reason_tweek") or None 
        
        entry .updated_at =datetime .utcnow ()
        
        db .commit ()
        
        return {"ok":True }
    
    except Exception as e :
        db .rollback ()
        logger.exception("Error updating PDK/DK entry")
        return {"ok":False ,"error":str (e )},400



@router.post("/admin/admin/pdkdk/create", response_class=JSONResponse)
async def create_pdkdk_entry(request: Request, db: Session = Depends(get_db)):
    """Create a new PDK/DK entry"""
    logger.debug("create_pdkdk_entry called")
    try:
        body = await request.json()
        logger.debug("Request body: %s", body)
        
        project_id = body.get("project_id")
        category = body.get("category")
        
        logger.debug("project_id: %s, category: %s", project_id, category)
        
        if not project_id or not category:
            return {"ok": False, "error": "Missing project_id or category"}
        
                          
        entry = PDKDKEntry(
            project_id=project_id,
            category=category,
            created_at=datetime.utcnow(),
            updated_at=datetime.utcnow()
        )
        db.add(entry)
        db.commit()
        db.refresh(entry)
        logger.info("Entry created with id=%s", entry.id)
        
        return {"ok": True, "id": entry.id, "message": "Entry created"}
    
    except Exception as e:
        db.rollback()
        logger.exception("Error creating PDK/DK entry")
        return {"ok": False, "error": str(e)}


@router.delete("/rpmt/admin/pdkdk/{entry_id}", response_class=JSONResponse)
def delete_pdkdk_entry(entry_id: int, request: Request, db: Session = Depends(get_db)):
    """Delete a PDK/DK entry"""
    ensure_admin_api(request)
    
    try:
        entry = db.get(PDKDKEntry, entry_id)
        if not entry:
            return {"ok": False, "error": "Entry not found"}, 404
        
        db.delete(entry)
        db.commit()
        
        return {"ok": True}
    
    except Exception as e:
        db.rollback()
        logger.exception('Error deleting PDK/DK entry')
        return {"ok": False, "error": str(e)}, 400
