from fastapi import APIRouter, Request, UploadFile, File, HTTPException
from fastapi.responses import JSONResponse
from pathlib import Path
from core.config import BASE_DIR
import uuid
import json
import time

router = APIRouter()
from fastapi.templating import Jinja2Templates
TEMPLATES = None

def set_templates(tmpl: Jinja2Templates):
    global TEMPLATES
    TEMPLATES = tmpl

                                        
TMP_DIR = BASE_DIR / 'uploads' / '.tmp' / 'garage'
FINAL_DIR = BASE_DIR / 'uploads' / 'garage'
TMP_DIR.mkdir(parents=True, exist_ok=True)
FINAL_DIR.mkdir(parents=True, exist_ok=True)

CHUNK_LIMIT = 1024 * 1024 * 128                                          


def _get_loggers():
    """Return (garage_logger, app_logger) with graceful fallback to standard logging if core.logger isn't importable.

    The fallback provides a minimal wrapper that implements the methods our code expects
    (info, debug, warning, log_error, log_file_operation) so code using these.
    """
    try:
        from core.logger import garage_logger, app_logger
    except Exception:
        import logging

        class _FallbackLogger:
            def __init__(self, logger):
                self._l = logger

            def info(self, msg, data=None):
                self._l.info(f"{msg} {data}")

            def debug(self, msg, data=None):
                self._l.debug(f"{msg} {data}")

            def warning(self, msg, data=None):
                self._l.warning(f"{msg} {data}")

            def log_error(self, error_type: str, message: str, details: dict = None):
                self._l.error(f"{error_type} - {message} - {details}")

            def log_file_operation(self, op: str, path: str, size: int = None):
                self._l.info(f"{op} {path} size={size}")

        return _FallbackLogger(logging.getLogger('garage')), _FallbackLogger(logging.getLogger('app'))
    return garage_logger, app_logger


def _save_meta(upload_id: str, meta: dict):
    d = TMP_DIR / upload_id
    d.mkdir(parents=True, exist_ok=True)
    (d / 'meta.json').write_text(json.dumps(meta))


def _load_meta(upload_id: str):
    d = TMP_DIR / upload_id
    mf = d / 'meta.json'
    if not mf.exists():
        return None
    return json.loads(mf.read_text())


def _require_auth(request: Request):
                                                            
    sess = getattr(request, 'session', None)
    if not sess or not sess.get('is_authenticated'):
        raise HTTPException(status_code=401, detail='Authentication required')


@router.post('/init')
async def init_upload(request: Request):
    _require_auth(request)
    payload = await request.json()
    filename = payload.get('filename')
    total_chunks = payload.get('total_chunks')
    chunk_size = payload.get('chunk_size', 10 * 1024 * 1024)                
    total_size = payload.get('total_size')

    if not filename:
        raise HTTPException(status_code=400, detail='filename required')

                                  
    from core.config import GARAGE_MAX_UPLOAD_SIZE, GARAGE_ALLOWED_EXTENSIONS
    if GARAGE_MAX_UPLOAD_SIZE and total_size and int(total_size) > GARAGE_MAX_UPLOAD_SIZE:
        raise HTTPException(status_code=413, detail='Total upload size exceeds server limit')

    ext = Path(filename).suffix.lower()
    if GARAGE_ALLOWED_EXTENSIONS and ext not in GARAGE_ALLOWED_EXTENSIONS:
        raise HTTPException(status_code=400, detail='File type not allowed')

    upload_id = str(uuid.uuid4())
    meta = {
        'upload_id': upload_id,
        'filename': filename,
        'chunk_size': int(chunk_size),
        'total_chunks': int(total_chunks) if total_chunks else None,
        'total_size': int(total_size) if total_size else None,
        'created_at': time.time(),
        'uploaded_chunks': []
    }
    _save_meta(upload_id, meta)
    garage_logger, _ = _get_loggers()
    garage_logger.info('Init upload', {'upload_id': upload_id, 'filename': filename, 'total_size': total_size})
    return JSONResponse({'upload_id': upload_id, 'chunk_size': meta['chunk_size']})


@router.put('/upload/{upload_id}/{chunk_index}')
async def upload_chunk(request: Request, upload_id: str, chunk_index: int, file: UploadFile = File(...)):
    _require_auth(request)
    meta = _load_meta(upload_id)
    if not meta:
        raise HTTPException(status_code=404, detail='Upload session not found')

                            
    garage_logger, _ = _get_loggers()
    garage_logger.debug(f'Uploading chunk {chunk_index} for {upload_id}')

                                                                        
    spool_max = getattr(file, 'spool_max_size', None)
    if spool_max is not None and spool_max > CHUNK_LIMIT:
        raise HTTPException(status_code=400, detail='Chunk too large')

    d = TMP_DIR / upload_id
    chunk_path = d / f'chunk_{chunk_index:08d}'
    try:
        with chunk_path.open('wb') as out:
            while True:
                chunk = await file.read(1024 * 1024)
                if not chunk:
                    break
                out.write(chunk)
    except Exception as e:
        garage_logger, _ = _get_loggers()
        garage_logger.log_error('chunk_save_failed', 'Failed to save chunk', {'upload_id': upload_id, 'chunk': chunk_index, 'error': str(e)})
        raise HTTPException(status_code=500, detail='Failed to save chunk')

                  
    meta['uploaded_chunks'] = meta.get('uploaded_chunks', [])
    if chunk_index not in meta['uploaded_chunks']:
        meta['uploaded_chunks'].append(chunk_index)
    _save_meta(upload_id, meta)
    garage_logger, _ = _get_loggers()
    garage_logger.info('chunk_received', {'upload_id': upload_id, 'chunk_index': chunk_index})
    return JSONResponse({'ok': True, 'chunk_index': chunk_index})


@router.get('/status/{upload_id}')
async def status(request: Request, upload_id: str):
    _require_auth(request)
    meta = _load_meta(upload_id)
    if not meta:
        raise HTTPException(status_code=404, detail='Upload session not found')
    return JSONResponse({'upload_id': upload_id, 'uploaded_chunks': meta.get('uploaded_chunks', [])})


@router.post('/complete/{upload_id}')
async def complete(request: Request, upload_id: str):
    _require_auth(request)
    meta = _load_meta(upload_id)
    if not meta:
        raise HTTPException(status_code=404, detail='Upload session not found')

    d = TMP_DIR / upload_id
                           
    safe_name = f"{int(time.time())}-{uuid.uuid4().hex[:8]}-{meta['filename']}"
    final_path = FINAL_DIR / safe_name

                              
    uploaded = sorted(meta.get('uploaded_chunks', []))
    if meta.get('total_chunks') and len(uploaded) != meta['total_chunks']:
        raise HTTPException(status_code=400, detail='Not all chunks uploaded')

    garage_logger, _ = _get_loggers()
    garage_logger.info('assembling_upload', {'upload_id': upload_id, 'chunks': len(uploaded)})
    try:
        with final_path.open('wb') as out:
            for idx in uploaded:
                chunk_file = d / f'chunk_{idx:08d}'
                if not chunk_file.exists():
                    raise HTTPException(status_code=400, detail=f'missing chunk {idx}')
                out.write(chunk_file.read_bytes())
    except Exception as e:
        garage_logger.log_error('assemble_failed', 'Failed to assemble chunks', {'upload_id': upload_id, 'error': str(e)})
        raise HTTPException(status_code=500, detail='Failed to assemble file')

             
                     
    for p in d.iterdir():
        try:
            p.unlink()
        except Exception:
            pass
    try:
        d.rmdir()
    except Exception:
        pass

                                           
    rel = final_path.relative_to(BASE_DIR)
    garage_logger, _ = _get_loggers()
    garage_logger.log_file_operation('upload_complete', str(final_path), size=final_path.stat().st_size)
    return JSONResponse({'ok': True, 'path': str(rel), 'filename': safe_name})


@router.get('/upload')
async def upload_page(request: Request):
    _require_auth(request)
    garage_logger, app_logger = _get_loggers()
    try:
        garage_logger.debug('upload_page called', {'session': getattr(request, 'session', {})})
        from core.config import GARAGE_MAX_UPLOAD_SIZE
        max_size = GARAGE_MAX_UPLOAD_SIZE or (1024 * 1024 * 1024)
        max_size_str = f"{round(max_size / (1024*1024), 1)} MB"
        server_url = str(request.base_url).rstrip('/')

                                                                                  
        templ = TEMPLATES
        if templ is None:
            garage_logger.warning('Templates not configured for garage_routes; falling back to default templates')
            from fastapi.templating import Jinja2Templates
            templ = Jinja2Templates(directory=str(BASE_DIR / 'templates'))
                                                                                           
            try:
                from services import compute_derived
            except Exception:
                def compute_derived(x):
                    return x
            from core.i18n import t as i18n_t, get_locale
            templ.env.globals['compute'] = compute_derived
            templ.env.globals['img'] = lambda path: f"/img/{path}"
            def t_with_request_locale(key, locale=None):
                if locale is None:
                    locale = get_locale(request)
                return i18n_t(key, locale)
            templ.env.globals['t'] = t_with_request_locale

                                                         
        tpl_path = BASE_DIR / 'templates' / 'garage' / 'upload.html'
        garage_logger.debug('Checking template path', {'path': str(tpl_path), 'exists': tpl_path.exists()})

        return templ.TemplateResponse('garage/upload.html', {'request': request, 'max_size': max_size, 'max_size_str': max_size_str, 'server_url': server_url})
    except HTTPException:
        raise
    except Exception as e:
                                                                                     
        try:
            garage_logger.log_error('upload_page_error', 'Failed to render upload page', {'error': str(e)})
        except Exception:
            pass
        try:
            app_logger.log_error('upload_page_error', 'Failed to render upload page (fallback)', {'error': str(e)})
        except Exception:
            pass
        raise HTTPException(status_code=500, detail='Failed to render upload page')


# New endpoints: list files and download
@router.get('/list')
async def list_page(request: Request):
    """Render a simple page listing garage uploads."""
    _require_auth(request)
    garage_logger, _ = _get_loggers()
    try:
        templ = TEMPLATES
        if templ is None:
            from fastapi.templating import Jinja2Templates
            templ = Jinja2Templates(directory=str(BASE_DIR / 'templates'))
        server_url = str(request.base_url).rstrip('/')
        tpl_path = BASE_DIR / 'templates' / 'garage' / 'list.html'
        garage_logger.debug('Rendering garage list page', {'path': str(tpl_path), 'exists': tpl_path.exists()})
        return templ.TemplateResponse('garage/list.html', {'request': request, 'server_url': server_url})
    except Exception as e:
        garage_logger.log_error('list_page_error', 'Failed to render list page', {'error': str(e)})
        raise HTTPException(status_code=500, detail='Failed to render garage list page')


@router.post('/download-zip')
async def download_zip(request: Request):
    """Create a ZIP of selected garage files and return it as a download.

    Request JSON: {"safe_names": ["<safe_name>", ...]}
    """
    _require_auth(request)
    garage_logger, _ = _get_loggers()
    try:
        data = await request.json()
        safe_names = data.get('safe_names', []) if isinstance(data, dict) else []
        if not safe_names:
            raise HTTPException(status_code=400, detail='safe_names required')

        files = []
        for sn in safe_names:
            target = FINAL_DIR / sn
            if not target.exists() or not target.is_file():
                raise HTTPException(status_code=404, detail=f'File not found: {sn}')
            files.append((sn, target))

        import zipfile
        import tempfile
        tmp_zip = TMP_DIR / f"garage_zip_{int(time.time())}_{uuid.uuid4().hex[:8]}.zip"
        try:
            with zipfile.ZipFile(tmp_zip, 'w', compression=zipfile.ZIP_DEFLATED) as zf:
                for sn, p in files:
                    arcname = '-'.join(p.name.split('-')[2:]) if len(p.name.split('-')) >= 3 else p.name
                    zf.write(p, arcname=arcname)
        except Exception as e:
            garage_logger.log_error('zip_failed', 'Failed to create zip', {'error': str(e)})
            raise HTTPException(status_code=500, detail='Failed to create zip')

        garage_logger.info('zip_created', {'zip': str(tmp_zip), 'files': len(files)})
        return FileResponse(str(tmp_zip), filename='garage_files.zip', media_type='application/zip')
    except HTTPException:
        raise
    except Exception as e:
        garage_logger.log_error('download_zip_error', 'Failed to process download-zip', {'error': str(e)})
        raise HTTPException(status_code=500, detail='Failed to create zip')
    """Download a previously uploaded garage file by its safe name."""
    _require_auth(request)
    garage_logger, _ = _get_loggers()
    try:
        target = FINAL_DIR / safe_name
        # prevent path traversal
        if not target.exists() or not target.is_file():
            raise HTTPException(status_code=404, detail='File not found')
        # serve file
        garage_logger.info('download', {'file': str(target), 'user': getattr(request, 'session', {}).get('email')})
        return FileResponse(str(target), filename=safe_name, media_type='application/octet-stream')
    except HTTPException:
        raise
    except Exception as e:
        garage_logger.log_error('download_error', 'Failed to download file', {'error': str(e)})
        raise HTTPException(status_code=500, detail='Failed to download file')