from fastapi import APIRouter, Request, Form, UploadFile, File, Response
from fastapi.responses import HTMLResponse, RedirectResponse, JSONResponse
from typing import List
from core.i18n import get_locale, t as i18n_t
from modules.cits.db import get_customer_db_sync
from modules.cits.models import CustomerIssue, Customer, IP, IssueConversation, ContactPerson
from core.auth.db import get_auth_db_sync
from core.auth.models import User as AuthUser
from pathlib import Path
from core.config import BASE_DIR
from datetime import datetime
import os
import re

def sanitize_filename(filename: str) -> str:
    filename = re.sub(r'[#?&=%;]', '_', filename)
    filename = re.sub(r'\s+', '_', filename)
    return filename

router = APIRouter(tags=["cits"])
templates = None


def set_templates(tmpl):
    global templates
    templates = tmpl


def ensure_authenticated(request: Request):
    if not request.session.get("is_authenticated"):
        return RedirectResponse(url="/auth/login", status_code=303)
    return None


@router.get("/", response_class=HTMLResponse)
def customer_main(request: Request, status: str = None):
                                                                     
    session_param = request.query_params.get("session")
    if session_param:
                                          
        response = RedirectResponse(url="/cits/", status_code=303)
        response.set_cookie("rams_sess", session_param, max_age=30*60, path="/", httponly=True)
        return response

    auth_check = ensure_authenticated(request)
    if auth_check:
        return auth_check

    if templates is None:
        return HTMLResponse("<h1>Error: Templates not initialized</h1>")

    locale = get_locale(request)
    db = get_customer_db_sync()
    try:
        issues = db.query(CustomerIssue).order_by(CustomerIssue.created_at.desc()).all()

        for it in issues:
            disp = []
            if it.attachments:
                parts = [p for p in it.attachments.split(',') if p]
                non_prefixed = [p for p in parts if not (p.split('/')[-1].startswith('cits_'))]
                if non_prefixed:
                    disp = non_prefixed
                else:
                    disp = parts
            it.display_attachments = disp

        total = len(issues)
        open_count = len([i for i in issues if i.status == 'OPEN'])
        pending_count = len([i for i in issues if i.status == 'PENDING'])
        close_count = len([i for i in issues if i.status == 'CLOSE'])
        status_counts = {
            'OPEN': open_count,
            'PENDING': pending_count,
            'CLOSE': close_count,
        }

        auth_db = get_auth_db_sync()
        try:
            users = auth_db.query(AuthUser).filter(AuthUser.is_active == True).order_by(AuthUser.english_name).all()
        finally:
            auth_db.close()

        customers = db.query(Customer).filter(Customer.is_active == True).order_by(Customer.name).all()

        def t(key: str, *args, **kwargs):
            return i18n_t(key, locale, **kwargs)
        return templates.TemplateResponse("modules/cits/main.html", {
            "request": request,
            "locale": locale,
            "t": t,
            "issues": issues,
            "users": users,
            "customers": customers,
            "total_issues": total,
            "open_issues": open_count,
            "status_counts": status_counts,
            "status_list": ['OPEN','PENDING','CLOSE'],
            "filter_status": status or "",
        })
    finally:
        db.close()


@router.get('/issue/{issue_id}', response_class=HTMLResponse)
def customer_issue_detail(request: Request, issue_id: int):
    auth_check = ensure_authenticated(request)
    if auth_check:
        return auth_check

    if templates is None:
        return HTMLResponse("<h1>Error: Templates not initialized</h1>")

    db = get_customer_db_sync()
    try:
        issue = db.query(CustomerIssue).filter(CustomerIssue.id == issue_id).first()
        if not issue:
            return HTMLResponse('<h1>Issue not found</h1>', status_code=404)

        disp = []
        if issue.attachments:
            parts = [p for p in issue.attachments.split(',') if p]
            non_prefixed = [p for p in parts if not (p.split('/')[-1].startswith('cits_'))]
            disp = non_prefixed if non_prefixed else parts
        issue.display_attachments = disp

        auth_db = get_auth_db_sync()
        try:
            users_raw = auth_db.query(AuthUser).filter(AuthUser.is_active == True).order_by(AuthUser.english_name).all()
            users = [{'english_name': u.english_name, 'korean_name': getattr(u, 'korean_name', '')} for u in users_raw]
        finally:
            auth_db.close()

        customers = db.query(Customer).filter(Customer.is_active == True).order_by(Customer.name).all()
        
        customer_ips = {}
        for cust in customers:
            ips = db.query(IP).filter(IP.customer_id == cust.id, IP.is_active == True).all()
            customer_ips[cust.id] = ips

        locale = get_locale(request)

        def t(key: str, *args, **kwargs):
            return i18n_t(key, locale, **kwargs)

        return templates.TemplateResponse('modules/cits/issue_detail.html', {
            'request': request,
            'locale': locale,
            't': t,
            'issue': issue,
            'users': users,
            'customers': customers,
            'customer_ips': customer_ips,
        })
    finally:
        db.close()


@router.post('/issue/update/{issue_id}')
def update_issue(request: Request,
                 issue_id: int,
                 status: str = Form(None),
                 title: str = Form(None),
                 description: str = Form(None),
                 customer: str = Form(None),
                 ip_ic: str = Form(None),
                 tag: str = Form(None),
                 reporter: str = Form(None),
                 assignee: str = Form(None),
                 attachments: List[UploadFile] = File(None)):

    auth_check = ensure_authenticated(request)
    if auth_check:
        return auth_check

    db = get_customer_db_sync()
    try:
        issue = db.query(CustomerIssue).filter(CustomerIssue.id == issue_id).first()
        if not issue:
            return Response(content='Not found', status_code=404)

        changed = False
        if status is not None:
            issue.status = status
            changed = True
        if title is not None:
            issue.title = title
            changed = True
        if description is not None:
            issue.description = description
            changed = True
        if customer is not None:
            issue.customer = customer
            changed = True
        if ip_ic is not None:
            issue.ip_ic = ip_ic
            changed = True
        if tag is not None:
            issue.tag = tag
            changed = True
        if reporter is not None:
            issue.reporter = reporter
            changed = True
        if assignee is not None:
            issue.assignee = assignee
            changed = True

        saved_paths = []
        if attachments:
            upload_dir = BASE_DIR / 'uploads' / 'cits'
            upload_dir.mkdir(parents=True, exist_ok=True)
            for up in attachments:
                if not up or not up.filename:
                    continue
                timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
                safe_name = sanitize_filename(Path(up.filename).name)
                unique_filename = f'cits_{issue.id}_{timestamp}_{safe_name}'
                file_path = upload_dir / unique_filename
                contents = up.file.read()
                with open(file_path, 'wb') as f:
                    f.write(contents)
                saved_paths.append((Path('uploads') / 'cits' / unique_filename).as_posix())

        if saved_paths:
            existing = issue.attachments or ''
            parts = [p for p in existing.split(',') if p]
            parts.extend(saved_paths)
            issue.attachments = ','.join(parts)
            changed = True

        if changed:
            db.add(issue)
            db.commit()

        return Response(content='OK', status_code=200)
    finally:
        db.close()


@router.post('/issue/delete/{issue_id}')
def delete_issue(request: Request, issue_id: int):
    auth_check = ensure_authenticated(request)
    if auth_check:
        return auth_check

    db = get_customer_db_sync()
    try:
        issue = db.query(CustomerIssue).filter(CustomerIssue.id == issue_id).first()
        if not issue:
            return Response(content='Not found', status_code=404)

        if issue.attachments:
            parts = [p for p in issue.attachments.split(',') if p]
            for p in parts:
                fp = BASE_DIR / Path(p)
                try:
                    if fp.exists():
                        fp.unlink()
                except Exception:
                    pass

        db.delete(issue)
        db.commit()
        return RedirectResponse(url='/cits/', status_code=303)
    finally:
        db.close()


@router.post('/issue/attachment/delete/{issue_id}')
def delete_attachment(request: Request, issue_id: int, filepath: str = Form(...)):
    auth_check = ensure_authenticated(request)
    if auth_check:
        return auth_check

    db = get_customer_db_sync()
    try:
        issue = db.query(CustomerIssue).filter(CustomerIssue.id == issue_id).first()
        if not issue:
            return Response(content='Not found', status_code=404)

        existing = [p for p in (issue.attachments or '').split(',') if p]
        norm = filepath.replace('\\', '/').lstrip('/')
        to_remove = None
        for p in existing:
            if p.endswith(norm) or p == norm:
                to_remove = p
                break
        if to_remove:
            try:
                fp = BASE_DIR / Path(to_remove)
                if fp.exists():
                    fp.unlink()
            except Exception:
                pass
            existing = [p for p in existing if p != to_remove]
            issue.attachments = ','.join(existing) if existing else None
            db.add(issue)
            db.commit()
            return Response(content='OK', status_code=200)
        return Response(content='Not found', status_code=404)
    finally:
        db.close()


@router.post("/issue/create")
def create_issue(request: Request,
                 title: str = Form(...),
                 customer: str = Form(""),
                 ip_ic: str = Form(""),
                 tag: str = Form("")):

    auth_check = ensure_authenticated(request)
    if auth_check:
        return auth_check

    db = get_customer_db_sync()
    try:
        def build_customer_prefix(name: str) -> str:
            if not name:
                return 'CITS'
            import re
            code = re.sub(r'[^A-Za-z0-9]', '', name.upper())
            if not code:
                return 'CITS'
            return code[:8]

        prefix = build_customer_prefix(customer)

        existing = db.query(CustomerIssue).filter(CustomerIssue.ticket_no.like(f"{prefix}-%")).all()
        max_seq = 0
        for it in existing:
            try:
                tail = it.ticket_no.split('-', 1)[-1]
                seq = int(tail)
                if seq > max_seq:
                    max_seq = seq
            except Exception:
                continue
        next_seq = max_seq + 1
        ticket_no = f"{prefix}-{next_seq:04d}"

        issue = CustomerIssue(
            ticket_no=ticket_no,
            title=title,
            description="",
            status="OPEN",
            customer=customer,
            ip_ic=ip_ic,
            reporter="",
            assignee="",
            tag=tag if tag else None,
        )
        db.add(issue)
        db.commit()
        db.refresh(issue)

        return RedirectResponse(url=f"/cits/issue/{issue.id}", status_code=303)
    finally:
        db.close()


@router.get('/customers', response_class=HTMLResponse)
def customers_list(request: Request):
    auth_check = ensure_authenticated(request)
    if auth_check:
        return auth_check

    if templates is None:
        return HTMLResponse("<h1>Error: Templates not initialized</h1>")

    locale = get_locale(request)
    db = get_customer_db_sync()
    try:
        customers = db.query(Customer).filter(Customer.is_active == True).order_by(Customer.name).all()

        def t(key: str, *args, **kwargs):
            return i18n_t(key, locale, **kwargs)

        return templates.TemplateResponse("modules/cits/customers.html", {
            "request": request,
            "locale": locale,
            "t": t,
            "customers": customers,
        })
    finally:
        db.close()


@router.post('/customers/create')
def create_customer(request: Request,
                    name: str = Form(...),
                    company: str = Form(""),
                    email: str = Form(""),
                    notes: str = Form("")):
    auth_check = ensure_authenticated(request)
    if auth_check:
        return auth_check

    db = get_customer_db_sync()
    try:
        customer = Customer(
            name=name,
            company=company,
            email=email,
            notes=notes,
        )
        db.add(customer)
        db.commit()
        return RedirectResponse(url="/cits?customer_added=true", status_code=303)
    finally:
        db.close()


@router.post('/customers/update/{customer_id}')
def update_customer(request: Request,
                    customer_id: int,
                    name: str = Form(...),
                    company: str = Form(""),
                    email: str = Form(""),
                    notes: str = Form("")):
    auth_check = ensure_authenticated(request)
    if auth_check:
        return auth_check

    db = get_customer_db_sync()
    try:
        customer = db.query(Customer).filter(Customer.id == customer_id).first()
        if not customer:
            return HTMLResponse("<h1>Customer not found</h1>", status_code=404)

        customer.name = name
        customer.company = company
        customer.email = email
        customer.notes = notes
        db.commit()

        return RedirectResponse(url="/cits?customer_updated=true", status_code=303)
    finally:
        db.close()


@router.post('/customers/delete/{customer_id}')
def delete_customer(request: Request, customer_id: int):
    auth_check = ensure_authenticated(request)
    if auth_check:
        return auth_check

    db = get_customer_db_sync()
    try:
        customer = db.query(Customer).filter(Customer.id == customer_id).first()
        if not customer:
            return HTMLResponse("<h1>Customer not found</h1>", status_code=404)

        customer.is_active = False
        db.commit()

        return RedirectResponse(url="/cits?customer_deleted=true", status_code=303)
    finally:
        db.close()


@router.get('/api/customers/{customer_id}/ips')
def get_customer_ips(request: Request, customer_id: int):
    from fastapi.responses import JSONResponse
    
    auth_check = ensure_authenticated(request)
    if auth_check:
        return auth_check

    db = get_customer_db_sync()
    try:
        ips = db.query(IP).filter(IP.customer_id == customer_id, IP.is_active == True).all()
        return JSONResponse([{"id": ip.id, "name": ip.name, "description": ip.description} for ip in ips])
    finally:
        db.close()


@router.post('/ips/create')
def create_ip(request: Request,
              customer_id: int = Form(...),
              name: str = Form(...),
              description: str = Form("")):
    auth_check = ensure_authenticated(request)
    if auth_check:
        return auth_check

    db = get_customer_db_sync()
    try:
        ip = IP(
            customer_id=customer_id,
            name=name,
            description=description,
        )
        db.add(ip)
        db.commit()
        return RedirectResponse(url="/cits?ip_added=true", status_code=303)
    finally:
        db.close()


@router.post('/ips/delete/{ip_id}')
def delete_ip(request: Request, ip_id: int):
    auth_check = ensure_authenticated(request)
    if auth_check:
        return auth_check

    db = get_customer_db_sync()
    try:
        ip = db.query(IP).filter(IP.id == ip_id).first()
        if ip:
            db.delete(ip)
            db.commit()
        return Response(status_code=200)
    finally:
        db.close()


@router.get('/issue/conversations/{issue_id}')
def get_conversations(request: Request, issue_id: int):
    """Get all conversations for an issue, grouped by Inquiry-Reply pairs"""
    auth_check = ensure_authenticated(request)
    if auth_check:
        return auth_check
    
    db = get_customer_db_sync()
    try:
        convs = db.query(IssueConversation).filter(IssueConversation.issue_id == issue_id).order_by(IssueConversation.created_at).all()
        
        grouped = []
        inquiries_map = {}                                       
        
                                           
        for c in convs:
            if c.type.lower() == 'inquiry':
                inquiries_map[c.id] = c
        
                                                                             
        for inquiry_id, inquiry in inquiries_map.items():
            replies = [
                {
                    'id': r.id,
                    'type': r.type,
                    'content': r.content,
                    'created_by': r.created_by,
                    'created_at': r.created_at.isoformat() if r.created_at else None
                }
                for r in convs 
                if r.type.lower() == 'reply' and r.inquiry_id == inquiry_id
            ]
            
            grouped.append({
                'inquiry': {
                    'id': inquiry.id,
                    'type': inquiry.type,
                    'content': inquiry.content,
                    'created_by': inquiry.created_by,
                    'created_at': inquiry.created_at.isoformat() if inquiry.created_at else None
                },
                'replies': replies
            })
        
        return JSONResponse(grouped)
    finally:
        db.close()


@router.post('/issue/conversations/{issue_id}/add')
def add_conversation(request: Request, issue_id: int, content: str = Form(...), type: str = Form('Inquiry'), date: str = Form(None), created_by: str = Form(None), inquiry_id: int = Form(None)):
    """Add a new conversation entry (auto-creates as Inquiry type, unless type is specified)"""
    auth_check = ensure_authenticated(request)
    if auth_check:
        return auth_check
    
    db = get_customer_db_sync()
    try:
        author = created_by if created_by else request.session.get('english_name', 'Unknown')
        
        created_at = None
        if date:
            from datetime import datetime
            try:
                created_at = datetime.strptime(date, '%Y-%m-%d')
            except:
                pass
        
        conv = IssueConversation(
            issue_id=issue_id,
            inquiry_id=inquiry_id,
            type=type if type in ['Inquiry', 'Reply'] else 'Inquiry',
            content=content,
            created_by=author,
            created_at=created_at
        )
        db.add(conv)
        db.commit()
        return JSONResponse({'ok': True})
    except Exception as e:
        db.rollback()
        return JSONResponse({'ok': False, 'error': str(e)}, status_code=400)
    finally:
        db.close()


@router.post('/issue/conversations/{conv_id}/delete')
def delete_conversation(request: Request, conv_id: int):
    """Delete a conversation entry"""
    auth_check = ensure_authenticated(request)
    if auth_check:
        return auth_check
    
    db = get_customer_db_sync()
    try:
        conv = db.query(IssueConversation).filter(IssueConversation.id == conv_id).first()
        if conv:
            db.delete(conv)
            db.commit()
        return JSONResponse({'ok': True})
    except Exception as e:
        db.rollback()
        return JSONResponse({'ok': False, 'error': str(e)}, status_code=400)
    finally:
        db.close()


@router.post('/issue/conversations/{conv_id}/update-date')
def update_conversation_date(request: Request, conv_id: int, created_at: str = Form(...)):
    """Update conversation created_at date"""
    auth_check = ensure_authenticated(request)
    if auth_check:
        return auth_check
    
    db = get_customer_db_sync()
    try:
        from datetime import datetime
        conv = db.query(IssueConversation).filter(IssueConversation.id == conv_id).first()
        if not conv:
            return JSONResponse({'success': False, 'error': 'Conversation not found'}, status_code=404)
        
                                          
        conv.created_at = datetime.fromisoformat(created_at.replace('Z', '+00:00'))
        db.commit()
        return JSONResponse({'success': True})
    except Exception as e:
        db.rollback()
        return JSONResponse({'success': False, 'error': str(e)}, status_code=400)
    finally:
        db.close()


@router.post('/issue/conversations/{conv_id}/update')
def update_conversation(request: Request, conv_id: int, content: str = Form(...)):
    """Update conversation content"""
    auth_check = ensure_authenticated(request)
    if auth_check:
        return auth_check
    
    db = get_customer_db_sync()
    try:
        conv = db.query(IssueConversation).filter(IssueConversation.id == conv_id).first()
        if not conv:
            return JSONResponse({'ok': False, 'error': 'Not found'}, status_code=404)
        
        conv.content = content
        db.commit()
        return JSONResponse({'ok': True})
    except Exception as e:
        db.rollback()
        return JSONResponse({'ok': False, 'error': str(e)}, status_code=400)
    finally:
        db.close()


@router.get('/help', response_class=HTMLResponse)
def cits_help(request: Request):
    auth_check = ensure_authenticated(request)
    if auth_check:
        return auth_check

    if templates is None:
        return HTMLResponse("<h1>Error: Templates not initialized</h1>")

    locale = get_locale(request)

    def t(key: str, *args, **kwargs):
        return i18n_t(key, locale, **kwargs)

    return templates.TemplateResponse('modules/cits/help.html', {
        'request': request,
        'locale': locale,
        't': t,
    })
