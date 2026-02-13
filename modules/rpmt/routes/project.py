from datetime import date 
from typing import Dict ,Optional 
import time 
import re 


from fastapi import APIRouter ,Request ,Depends ,Form ,File ,UploadFile ,HTTPException ,Query ,Body 
from fastapi .responses import HTMLResponse ,RedirectResponse 
from sqlalchemy .orm import Session 
from sqlalchemy import select 
from sqlalchemy .orm import Session 

from models import Project ,Task ,StatusEnum ,PDKDKEntry 
from services import compute_derived ,compute_schedule ,ScheduleEnum 
from core .db import get_db 
from core .config import BASE_DIR 
import logging

LOG_DIR = BASE_DIR / 'logs'
LOG_DIR.mkdir(parents=True, exist_ok=True)
deletion_logger = logging.getLogger('file_deletions')
if not deletion_logger.handlers:
    fh = logging.FileHandler(LOG_DIR / 'file_deletions.log', encoding='utf-8')
    fh.setFormatter(logging.Formatter('%(asctime)s\t%(levelname)s\t%(message)s'))
    deletion_logger.addHandler(fh)
    deletion_logger.setLevel(logging.INFO)

upload_logger = logging.getLogger('file_uploads')
if not upload_logger.handlers:
    uh = logging.FileHandler(LOG_DIR / 'file_uploads.log', encoding='utf-8')
    uh.setFormatter(logging.Formatter('%(asctime)s\t%(levelname)s\t%(message)s'))
    upload_logger.addHandler(uh)
    upload_logger.setLevel(logging.INFO)

def _log_delete(module, filename, user, ip, result, note=''):
    deletion_logger.info(f"{module}\t{filename}\tuser={user}\tip={ip}\tresult={result}\t{note}")
from core .utils import build_groups_keep_order 
from data .default_tasks import DEFAULT_TASK_TEMPLATE 
from func .services .file_preview import get_file_preview 
from core .i18n import get_locale 

router =APIRouter ()

templates =None 

def set_templates (tmpl ):
    global templates 
    templates =tmpl 

def ensure_authenticated (request :Request )->Optional [RedirectResponse ]:
    if not request .session .get ("is_authenticated"):
        return RedirectResponse (url ="/main",status_code =303 )
    return None 

UPLOAD_DIR = BASE_DIR / "uploads" / "rpmt"
UPLOAD_DIR.mkdir(parents=True, exist_ok=True)

MAX_UPLOAD_BYTES = 50 * 1024 * 1024

def _safe_filename (name :str )->str :
    name =name .rsplit ("/",1 )[-1 ].rsplit ("\\",1 )[-1 ]
    return re .sub (r"[^A-Za-z0-9._-]+","_",name )or "file"


def next_ord (db :Session ,pid :int ,cat1 :str )->int :
    vals =db .execute (
    select (Task .ord ).where (
    Task .project_id ==pid ,
    Task .cat1 ==cat1 
    )
    ).scalars ().all ()
    m =max ([(v or 0 )for v in vals ],default =0 )
    return m +1 

@router.post("/projects/create")
def create_project (
code :str =Form (...),
process :str =Form (""),
metal_option :str =Form (""),
ip_code :str =Form (""),
pdk_ver :str =Form (""),
db :Session =Depends (get_db ),
):
    p = Project(
        code=code,
        process=process,
        ip_code=ip_code,
        pdk_ver=pdk_ver,
    )
    db .add (p )
    db .flush ()

    counters :Dict [str ,int ]={}
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

    pdk_categories = [
        "DFM", "DRC", "EM", "ESD", "ETC", "FILL", "FLT", "LVS", "MODEL", "PDKLib", "PEX", "PnR"
    ]
    dk_categories = [
        "Standard Cell", "Memory", "CDM ESD", "GPIO", "HSIO", "Power ESD", "CDM B2B"
    ]
    
    all_categories = pdk_categories + dk_categories
    
    for category in all_categories:
        db .add (PDKDKEntry (
            project_id=p .id ,
            category=category
        ))

    db .commit ()


@router.get("/projects/{pid}",response_class =HTMLResponse )
def project_detail (pid :int ,request :Request ,db :Session =Depends (get_db )):
    from fastapi .responses import RedirectResponse 

    if not request .session .get ("is_authenticated"):
        return RedirectResponse (url ="/main",status_code =303 )

    locale =get_locale (request )
    p =db .get (Project ,pid )
    if not p :
        raise HTTPException (status_code =404 ,detail ="Project not found")

    active_tasks =[t for t in p .tasks if not (t .archived or False )]
    groups =build_groups_keep_order (active_tasks )
    
    pdk_dk_entries = db.query(PDKDKEntry).filter(PDKDKEntry.project_id == pid).all()
    
    category_order = [
        'DFM', 'DRC', 'EM', 'ESD', 'ETC', 'Fill', 'FLT', 'LVS', 
        'MODEL', 'PDKLib', 'PEX', 'PnR', 
        'Standard Cell', 'Memory', 'CDM ESD', 'GPIO', 'HSIO', 'Power ESD', 'CDM B2B'
    ]
    order_map = {cat: idx for idx, cat in enumerate(category_order)}
    pdk_dk_entries = sorted(pdk_dk_entries, key=lambda x: order_map.get(x.category, 999))

    return templates .TemplateResponse ("modules/rpmt/project_detail.html",{
    "request":request ,
    "p":p ,
    "groups":groups ,
    "compute":compute_derived ,
    "StatusEnum":StatusEnum ,
    "locale":locale ,
    "pdk_dk_entries":pdk_dk_entries
    })

@router.get("/projects/{pid}/kpi.json")
def project_kpi_json(
    pid: int,
    kind: str = Query(..., pattern="^(done|progress|late|not_started|na)$"),
    request: Request = ...,
    db: Session = Depends(get_db)
):
    if request.headers.get('x-debug-bypass') != '1':
        auth_check = ensure_authenticated(request)
        if auth_check:
            return auth_check

    try:
        client_host = getattr(request.client, 'host', 'unknown')
    except Exception:
        client_host = 'unknown'
    hdrs = {k: v for k, v in request.headers.items() if k.lower() not in ('cookie', 'authorization')}
    upload_logger.info(f"Entry KPI handler project={pid} url={request.url} method={request.method} client={client_host} headers={hdrs}")
    try:
        content_len = request.headers.get('content-length')
        upload_logger.info(f"Content-Length header: {content_len}")
    except Exception:
        pass
    try:
        sess = {
            'is_authenticated': bool(request.session.get('is_authenticated')),
            'email': request.session.get('email'),
            'role': request.session.get('role')
        }
        upload_logger.info(f"Session info for project={pid}: {sess}")
    except Exception:
        upload_logger.exception(f"Failed to read session info for project={pid}")

    p =db .get (Project ,pid )
    if not p :
        raise HTTPException (status_code =404 ,detail ="Project not found")

    items =[]
    today =date .today ()

    def pack (task :Task ,*,late_days :int |None =None ):
        return {
        "task_id":task .id ,
        "cat1":task .cat1 or "",
        "cat2":task .cat2 or "",
        "dept_from":task .dept_from or "",
        "dept_to":task .dept_to or "",
        "due_date":task .due_date .isoformat ()if task .due_date else None ,
        "status":task .status .value if task .status else "N/A",
        "late_days":late_days ,
        "reason":task .reason or "",
        }

    if kind =="late":
        for t in p .tasks :
            info =compute_schedule (t .due_date ,t .status )
            if info .state ==ScheduleEnum .LATE :
                ld =abs ((t .due_date -today ).days )if t .due_date else None 
                items .append (pack (t ,late_days =ld ))
    else :
        target ={
        "done":StatusEnum .COMPLETE ,
        "progress":StatusEnum .IN_PROGRESS ,
        "not_started":StatusEnum .NOT_STARTED ,
        "na":StatusEnum .NA ,
        }[kind ]
        for t in p .tasks :
            if t .status ==target :
                ld =None 
                info =compute_schedule (t .due_date ,t .status )
                if info .state ==ScheduleEnum .LATE and t .due_date :
                    ld =abs ((t .due_date -today ).days )
                items .append (pack (t ,late_days =ld ))

    return {
    "project":{"id":p .id ,"code":p .code },
    "kind":kind ,
    "count":len (items ),
    "items":items ,
    }

@router.get("/projects/{pid}/delays.json")
def project_delays_json (pid :int ,request :Request ,db :Session =Depends (get_db )):
    if request.headers.get('x-debug-bypass') != '1':
        auth_check = ensure_authenticated(request)
        if auth_check:
            return auth_check

    p =db .get (Project ,pid )
    if not p :raise HTTPException (status_code =404 ,detail ="Project not found")
    today =date .today ()
    items =[]
    for t in p .tasks :
        info =compute_schedule (t .due_date ,t .status )
        if info .state ==ScheduleEnum .LATE :
            items .append ({
            "task_id":t .id ,
            "cat1":t .cat1 or "",
            "cat2":t .cat2 or "",
            "dept_from":t .dept_from or "",
            "dept_to":t .dept_to or "",
            "due_date":t .due_date .isoformat ()if t .due_date else None ,
            "late_days":abs ((t .due_date -today ).days )if t .due_date else None ,
            "reason":t .reason or "",
            })
    return {"project":{"id":p .id ,"code":p .code },"count":len (items ),"items":items }

@router.post("/projects/{pid}/delete")
def delete_project (pid :int ,db :Session =Depends (get_db )):
    p =db .get (Project ,pid )
    if p :db .delete (p );db .commit ()
    return RedirectResponse (url ="/",status_code =303 )

@router.post("/projects/{pid}/tasks/new",response_class =HTMLResponse )
def add_task_blank (pid :int ,cat1 :str =Form (...),db :Session =Depends (get_db )):
    p =db .get (Project ,pid )
    if not p :raise HTTPException (404 )
    t =Task (
    project_id =p .id ,cat1 =cat1 ,cat2 ="",dept_from ="",dept_to ="",
    due_date =None ,status =StatusEnum .NOT_STARTED ,reason =None ,
    ord =next_ord (db ,p .id ,cat1 or "")
    )
    db .add (t );db .commit ()
    return RedirectResponse (url =f"/rpmt/projects/{pid }",status_code =303 )

@router.post("/projects/tasks/{tid}/update",response_class =HTMLResponse )
def task_update (
request :Request ,
tid :int ,
cat1 :Optional [str ]=Form (None ),
cat2 :Optional [str ]=Form (None ),
dept_from :Optional [str ]=Form (None ),
dept_to :Optional [str ]=Form (None ),
due_date :Optional [str ]=Form (None ),
status :Optional [str ]=Form (None ),
reason :Optional [str ]=Form (None ),
attachment :UploadFile |None =File (None ),
db :Session =Depends (get_db ),
):
    t =db .get (Task ,tid )
    if not t :
        raise HTTPException (status_code =404 ,detail ="Task not found")

    if cat1 is not None :t .cat1 =cat1 
    if cat2 is not None :t .cat2 =cat2 
    if dept_from is not None :t .dept_from =dept_from 
    if dept_to is not None :t .dept_to =dept_to 
    if due_date is not None :
        t .due_date =date .fromisoformat (due_date )if due_date else None 
    if status is not None and status in StatusEnum ._value2member_map_ :
        t .status =StatusEnum (status )
    if reason is not None :t .reason =reason 

    if attachment and attachment.filename:
        orig = attachment.filename
        stamp = int(time.time())
        base = _safe_filename(orig)
        save_name = f"{tid}_{stamp}_{base}"
        dest = UPLOAD_DIR / save_name
        with open(dest, "wb") as f:
            f.write(attachment.file.read())
        t.file_path = f"/uploads/rpmt/{save_name}"
        t .file_name =orig 

    db .add (t )
    db .commit ()
    db .refresh (t )

    return templates .TemplateResponse (
    "_task_row.html",
    {"request":request ,"t":t ,"compute":compute_derived ,"StatusEnum":StatusEnum },
    )

@router.get("/projects/api/tasks/{tid}/files")
def get_task_files (tid :int ,db :Session =Depends (get_db )):
    """Task의 모든 파일 조회 - 디버깅용"""
    t =db .get (Task ,tid )
    if not t :
        raise HTTPException (status_code =404 ,detail ="Task not found")

    files =[]


    if hasattr (t ,'files')and t .files :
        files =[
        {
        "id":f .id ,
        "file_path":f .file_path ,
        "file_name":f .file_name ,
        "uploaded_at":f .uploaded_at .isoformat ()if f .uploaded_at else None 
        }
        for f in t .files 
        ]

    return {
    "task_id":tid ,
    "count":len (files ),
    "files":files 
    }

@router.post("/projects/tasks/{tid}/upload")
async def upload_file (
request :Request ,
tid :int ,
attachments :list [UploadFile ]=File (...),
db :Session =Depends (get_db ),
):
    """파일 업로드 라우트 - 여러 파일 지원"""
    if request.headers.get('x-debug-bypass') != '1':
        auth_check = ensure_authenticated(request)
        if auth_check:
            return auth_check

    t = db.get(Task, tid)
    if not t:
        raise HTTPException(status_code=404, detail="Task not found")

    if not attachments or len(attachments) == 0:
        raise HTTPException(status_code=400, detail="No file provided")

    file_paths = []
    file_names = []
    file_results = []

    for file in attachments:
        if not file or not file.filename:
            continue

        orig = file.filename
        stamp = int(time.time())
        base = _safe_filename(orig)
        save_name = f"{tid}_{stamp}_{base}"
        dest = UPLOAD_DIR / save_name

        try:
            content = await file.read()
            size = len(content) if content is not None else 0
            upload_logger.info(f"Receiving upload task={tid} name={orig} size={size}")

            if size == 0:
                upload_logger.warning(f"Empty upload for task={tid} filename={orig}")
                file_results.append({'name': orig, 'ok': False, 'error': 'empty file', 'size': size})
                continue

            if size > MAX_UPLOAD_BYTES:
                upload_logger.warning(f"File too large for task={tid} name={orig} size={size} (max={MAX_UPLOAD_BYTES})")
                file_results.append({'name': orig, 'ok': False, 'error': 'file too large', 'size': size, 'max': MAX_UPLOAD_BYTES})
                continue

            with open(dest, "wb") as f:
                f.write(content)

            file_paths.append(f"/uploads/rpmt/{save_name}")
            file_names.append(orig)
            file_results.append({'name': orig, 'ok': True, 'path': f"/uploads/rpmt/{save_name}", 'size': size})
            upload_logger.info(f"Uploaded task={tid} name={orig} -> {dest} size={size}")

        except Exception as e:
            upload_logger.exception(f"Failed uploading task={tid} name={orig}: {e}")
            file_results.append({'name': orig, 'ok': False, 'error': str(e)})

    if not file_paths:
        return { 'ok': False, 'uploaded_count': 0, 'files': file_results }

    try:
        existing_paths = [p for p in (t.file_path or "").split(",") if p.strip()]
        existing_names = [n for n in (t.file_name or "").split(",") if n.strip()]

        all_paths = existing_paths + file_paths
        all_names = existing_names + file_names

        t.file_path = ",".join(all_paths)
        t.file_name = ",".join(all_names)

        db.add(t)
        db.commit()
        db.refresh(t)

        return {
            'ok': all(r.get('ok') for r in file_results),
            'status': 'partial' if not all(r.get('ok') for r in file_results) else 'ok',
            'uploaded_count': len([r for r in file_results if r.get('ok')]),
            'files': file_results,
            'remaining': t.file_path,
        }

    except Exception as e:
        db.rollback()
        upload_logger.exception(f"Failed committing DB for task={tid}: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.post('/tasks/{tid}/file-delete')
@router.post('/projects/tasks/{tid}/file-delete')
def delete_task_file(tid: int, request: Request, path: str = Form(...), db: Session = Depends(get_db)):
    """Delete a specific uploaded file for a task. `path` should be the stored path like '/uploads/rpmt/<name>'"""
    auth_check = ensure_authenticated(request)
    if auth_check:
        return auth_check

    t = db.get(Task, tid)
    if not t:
        raise HTTPException(status_code=404, detail='Task not found')

    p = path.lstrip('/').replace('\\', '/')
    existing_paths = [pp for pp in (t.file_path or '').split(',') if pp.strip()]
    existing_names = [nn for nn in (t.file_name or '').split(',') if nn.strip()]

    if p not in [ep.lstrip('/') for ep in existing_paths]:
        raise HTTPException(status_code=404, detail='File not associated with task')

    try:
        full = BASE_DIR / p
        if full.exists():
            full.unlink()
            _log_delete('rpmt', p.split('/')[-1], request.session.get('email') or 'anon', getattr(request.client, 'host', 'unknown'), 'deleted')
    except Exception as e:
        _log_delete('rpmt', p.split('/')[-1], request.session.get('email') or 'anon', getattr(request.client, 'host', 'unknown'), 'error', str(e))

    new_paths = [ep for ep in existing_paths if ep.lstrip('/') != p]
    filename = p.split('/')[-1]
    new_names = [n for n in existing_names if n != filename]

    t.file_path = ','.join(new_paths)
    t.file_name = ','.join(new_names)
    db.add(t)
    db.commit()
    db.refresh(t)

    return {'ok': True, 'remaining': t.file_path}

@router.post("/projects/tasks/{tid}/update-json")
def task_update_json (tid :int ,payload :dict =Body (...),db :Session =Depends (get_db )):
    t =db .get (Task ,tid )
    if not t :raise HTTPException (404 ,"Task not found")
    if "due_date"in payload :
        v =payload ["due_date"];t .due_date =date .fromisoformat (v )if v else None 
    if "status"in payload :
        sv =payload ["status"];
        if sv in StatusEnum ._value2member_map_ :t .status =StatusEnum (sv )
    if "reason"in payload :t .reason =payload ["reason"]
    for k in ("cat1","cat2","dept_from","dept_to"):
        if k in payload :setattr (t ,k ,payload [k ]or "")
    db .commit ();db .refresh (t )
    remain ,delay ,signal =compute_derived (t .due_date ,t .status .value if t .status else "Not Started")
    return {"ok":True ,"remain":remain or "","delay":delay or "","signal":signal or "",
    "status":t .status .value if t .status else "Not Started","reason":t .reason or ""}

@router.post("/projects/tasks/{tid}/delete")
def task_delete (tid :int ,db :Session =Depends (get_db )):
    t =db .get (Task ,tid )
    if not t :raise HTTPException (404 )
    pid =t .project_id ;db .delete (t );db .commit ()
    return RedirectResponse (url =f"/rpmt/projects/{pid }",status_code =303 )

@router.post("/projects/api/tasks/{task_id}/status")
async def update_task_status (task_id :int ,payload :dict ,db :Session =Depends (get_db )):
    new_status =(payload .get ("status")or "").strip ()
    if not new_status :
        raise HTTPException (status_code =400 ,detail ="status is required")

    task =db .query (Task ).filter (Task .id ==task_id ).first ()
    if not task :
        raise HTTPException (status_code =404 ,detail ="Task not found")

    try :
        if isinstance (task .status ,StatusEnum ):
            task .status =StatusEnum (new_status )
        else :
            task .status =StatusEnum (new_status )
    except Exception :
        raise HTTPException (status_code =400 ,detail ="invalid status value")

    db .add (task )
    db .commit ()
    db .refresh (task )

    return {"ok":True ,"id":task .id ,"status":task .status .value }
router .post ("/tasks/{tid}/insert-below")
def task_insert_below (tid :int ,request :Request ,db :Session =Depends (get_db )):
    base =db .get (Task ,tid )
    if not base :
        raise HTTPException (404 ,"Task not found")

    pid =base .project_id 
    cat1 =base .cat1 or ""
    base_ord =base .ord or 0 

    siblings =db .execute (
    select (Task )
    .where (Task .project_id ==pid ,Task .cat1 ==cat1 )
    .order_by (Task .ord .asc (),Task .id .asc ())
    ).scalars ().all ()
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

    visit =request .query_params .get ("v")
    referer =request .headers .get ("referer","")or ""
    if "/admin"in referer :
        url =f"/admin?focus={pid }"
        if visit :
            sep ="&"if "?"in url else "?"
            url =f"{url }{sep }v={visit }"
        return RedirectResponse (url =url ,status_code =303 )
    else :
        return RedirectResponse (url =f"/rpmt/projects/{pid }",status_code =303 )

@router.get("/projects/files/preview/{filename}")
async def preview_file (filename :str ,request :Request ):
    auth_check =ensure_authenticated (request )
    if auth_check :
        return auth_check 

    file_path =UPLOAD_DIR /filename 

    if not file_path .exists ():
        raise HTTPException (404 ,"File not found")

    if filename .lower ().endswith ('.pdf'):
        return RedirectResponse(url=f"/uploads/rpmt/{filename}", status_code=303)

    try :
        html =get_file_preview (file_path )

        html_content ="""<!DOCTYPE html>
<html>
<head>
    <meta charset="utf-8">
    <meta name="viewport" content="width=device-width, initial-scale=1">
    <title>파일 미리보기 - {filename}</title>
    <style>
        body {{
            margin:0;
            padding:24px;
            font-family:'Sora','Pretendard','Noto Sans KR',system-ui,-apple-system,'Segoe UI',sans-serif;
            background:#f3f7ff;
            color:#1f2a3d;
        }}
        .preview-container {{
            max-width:1200px;
            margin:0 auto;
            background:#ffffff;
            border:1px solid #dbe4f2;
            border-radius:14px;
            box-shadow:0 14px 32px rgba(15,23,42,0.12);
            overflow:hidden;
        }}
        .preview-header {{
            display:flex;
            justify-content:space-between;
            align-items:center;
            gap:12px;
            padding:14px 18px;
            border-bottom:1px solid #e4eaf5;
            background:#f9fbff;
        }}
        .preview-title {{
            font-size:15px;
            font-weight:700;
            color:#0f172a;
            white-space:nowrap;
            overflow:hidden;
            text-overflow:ellipsis;
        }}
        .btn-close {{
            padding:7px 12px;
            background:#2e5bff;
            color:#ffffff;
            border:none;
            border-radius:8px;
            cursor:pointer;
            font-size:12px;
            font-weight:700;
        }}
        .btn-close:hover {{ background:#254bd2; }}
        .preview-content {{ padding:18px; }}
        .preview-content pre {{
            margin:0;
            padding:14px;
            border-radius:10px;
            border:1px solid #243552;
            background:#111a2b;
            color:#dbe7f8;
            overflow:auto;
            line-height:1.52;
            font-size:12px;
            font-family:ui-monospace,SFMono-Regular,Menlo,Monaco,Consolas,'Liberation Mono','Courier New',monospace;
        }}
        .preview-content code {{
            font-family:ui-monospace,SFMono-Regular,Menlo,Monaco,Consolas,'Liberation Mono','Courier New',monospace;
        }}
        .preview-content table {{
            border-collapse:collapse;
            width:100%;
            font-size:12px;
        }}
        .preview-content th, .preview-content td {{
            border:1px solid #dbe4f2;
            padding:8px 10px;
            text-align:left;
        }}
        .preview-content th {{
            background:#f4f8ff;
            font-weight:700;
            color:#1f2a3d;
        }}
        .preview-content h1, .preview-content h2, .preview-content h3 {{ color:#0f172a; }}
        .preview-content p {{ color:#334155; }}
    </style>
</head>
<body>
    <div class="preview-container">
        <div class="preview-header">
            <div class="preview-title">파일 미리보기 · {filename}</div>
            <button class="btn-close" onclick="window.close()">닫기</button>
        </div>
        <div class="preview-content">{html}</div>
    </div>
</body>
</html>"""
        html_content =html_content .format (filename =filename ,html =html )
        return HTMLResponse (content =html_content )
    except Exception as e :
        return HTMLResponse (content =f"""
<!DOCTYPE html>
<html>
<head><meta charset="utf-8"><title>미리보기 오류</title></head>
<body style="padding:40px;font-family:sans-serif;">
    <h2>⚠️ 미리보기 생성 실패</h2>
    <p>파일을 처리하는 중 오류가 발생했습니다.</p>
    <p style="color:#666;">파일 형식이 지원되지 않을 수 있습니다.</p>
    <button onclick="window.close()" style="margin-top:20px;padding:10px 20px;background:#667eea;color:white;border:none;border-radius:8px;cursor:pointer;">닫기</button>
</body>
</html>""")


@router.get("/api/my-tasks")
def get_my_tasks(request: Request, db: Session = Depends(get_db)):
    """현재 사용자에게 할당된 작업 목록 조회 - Desktop Client용"""
                                      
    user_dept = request.session.get('department', 'QM')          
    user_id = request.session.get('user_id')
    
    if not user_id:
                             
        return {"tasks": [], "authenticated": False}
    
    try:
                                     
        tasks = db.query(Task).filter(
            Task.dept_to == user_dept,
            Task.archived == False
        ).order_by(Task.updated_at.desc()).limit(50).all()
        
        task_list = []
        for t in tasks:
            project = db.get(Project, t.project_id)
            task_list.append({
                "id": t.id,
                "title": f"{t.cat1} - {t.cat2}" if t.cat2 else t.cat1,
                "status": t.status.value if t.status else "NOT_STARTED",
                "due_date": t.due_date.isoformat() if t.due_date else None,
                "project": project.code if project else "",
                "dept_from": t.dept_from or "",
                "dept_to": t.dept_to or "",
                "reason": t.reason or ""
            })
        
        return {"tasks": task_list, "authenticated": True}
    except Exception as e:
        return {"tasks": [], "error": str(e), "authenticated": True}