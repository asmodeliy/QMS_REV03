from typing import Dict, List, Tuple
import sqlite3
import re
from urllib.parse import unquote

from fastapi import APIRouter, Body, HTTPException, Request
from fastapi.responses import HTMLResponse, JSONResponse, RedirectResponse

from core.config import PRODUCT_INFO_DB_PATH
from core.i18n import get_locale
import logging
try:
    from core.logger import app_logger
except Exception:
    class _FallbackAppLogger:
        def __init__(self, l):
            self._l = l
        def info(self, msg, data=None):
            self._l.info(f"{msg} {data}")
        def warning(self, msg, data=None):
            self._l.warning(f"{msg} {data}")
        def debug(self, msg, data=None):
            self._l.debug(f"{msg} {data}")
    app_logger = _FallbackAppLogger(logging.getLogger('app'))

router = APIRouter()

templates = None
EXCLUDED_COLUMNS = {"delivery", "calibre", "version", "drc_version", "lane_configuration", "tech"}


def get_matrix_data():
                                                                     
    canonical_nodes = ["SF28nm", "SF14nm", "SF8nm", "SF5nm", "SF4nm"]

    canonical_rows = [
        {"ip": "MIPI D/C PHY Combo", "statuses": {"SF28nm": None, "SF14nm": "mass", "SF8nm": "proven", "SF5nm": None, "SF4nm": None}},
        {"ip": "MIPI D-PHY", "statuses": {"SF28nm": "mass", "SF14nm": "mass", "SF8nm": "proven", "SF5nm": "proven", "SF4nm": None}},
        {"ip": "MIPI A-PHY", "statuses": {"SF28nm": None, "SF14nm": "dev", "SF8nm": None, "SF5nm": None, "SF4nm": None}},
        {"ip": "ARM HSSTP TX PHY", "statuses": {"SF28nm": None, "SF14nm": "proven", "SF8nm": "proven", "SF5nm": "plan", "SF4nm": None}},
        {"ip": "USB DP TX PHY", "statuses": {"SF28nm": None, "SF14nm": None, "SF8nm": "proven", "SF5nm": None, "SF4nm": None}},
        {"ip": "HDMI TX PHY", "statuses": {"SF28nm": None, "SF14nm": None, "SF8nm": "proven", "SF5nm": None, "SF4nm": None}},
        {"ip": "PCIe PHY", "statuses": {"SF28nm": None, "SF14nm": None, "SF8nm": None, "SF5nm": "plan", "SF4nm": None}},
        {"ip": "UCIe PHY", "statuses": {"SF28nm": None, "SF14nm": None, "SF8nm": None, "SF5nm": "plan", "SF4nm": None}},
        {"ip": "Intra Panel Display TX", "statuses": {"SF28nm": None, "SF14nm": None, "SF8nm": None, "SF5nm": None, "SF4nm": "dev"}},
        {"ip": "Ethernet PHY", "statuses": {"SF28nm": "mass", "SF14nm": "mass", "SF8nm": "proven", "SF5nm": "plan", "SF4nm": None}},
        {"ip": "Multi Protocol PHY (PCIe / USB / SATA)", "statuses": {"SF28nm": None, "SF14nm": None, "SF8nm": None, "SF5nm": "dev", "SF4nm": None}},
        {"ip": "High-speed ADC (8Gsps, 12bit)", "statuses": {"SF28nm": None, "SF14nm": "dev", "SF8nm": None, "SF5nm": None, "SF4nm": None}},
        {"ip": "Low-jitter PLL (100MHz – 4GHz)", "statuses": {"SF28nm": None, "SF14nm": "dev", "SF8nm": None, "SF5nm": None, "SF4nm": None}},
    ]

    try:
        with open_conn() as conn:
            cursor = conn.cursor()
            cursor.execute("SELECT name FROM sqlite_master WHERE type='table' AND name='IP_MATRIX'")
            if cursor.fetchone():
                try:
                    cursor.execute("SELECT ip_name, node, status FROM IP_MATRIX")
                    rows = cursor.fetchall()
                except Exception as exc:
                    import traceback
                    app_logger.warning("Failed to query IP_MATRIX: %s", exc)
                    app_logger.warning(traceback.format_exc())
                    rows = []

                if not rows:
                    app_logger.info("IP_MATRIX table exists but empty; using canonical defaults")
                else:
                    db_map = {}
                    for ip_name, node, status in rows:
                        db_map.setdefault(ip_name, {})[node] = status

                    matrix_rows = []
                    for cr in canonical_rows:
                        ip = cr['ip']
                        statuses = {}
                        for node in canonical_nodes:
                            statuses[node] = db_map.get(ip, {}).get(node, cr['statuses'].get(node))
                        matrix_rows.append({"ip": ip, "statuses": statuses})

                                                                                                                
                    extra_ips = [ip for ip in db_map.keys() if ip not in {r['ip'] for r in canonical_rows}]
                    for ip in extra_ips:
                        statuses = {}
                        for node in canonical_nodes:
                            statuses[node] = db_map.get(ip, {}).get(node)
                        matrix_rows.append({"ip": ip, "statuses": statuses})

                                                
                    cursor.execute("SELECT name FROM sqlite_master WHERE type='table' AND name='IP_MATRIX_DELETED'")
                    if cursor.fetchone():
                        cursor.execute("SELECT ip_name FROM IP_MATRIX_DELETED")
                        deleted = {r[0] for r in cursor.fetchall()}
                    else:
                        deleted = set()

                    matrix_rows = [r for r in matrix_rows if r['ip'] not in deleted]

                    return canonical_nodes, matrix_rows
    except Exception as e:
        app_logger.warning(f"Failed to load matrix from database: {e}")

                                    
                                                    
    try:
        with open_conn() as conn:
            cursor = conn.cursor()
            cursor.execute("SELECT name FROM sqlite_master WHERE type='table' AND name='IP_MATRIX_DELETED'")
            if cursor.fetchone():
                cursor.execute("SELECT ip_name FROM IP_MATRIX_DELETED")
                deleted = {r[0] for r in cursor.fetchall()}
            else:
                deleted = set()
            if deleted:
                filtered = [r for r in canonical_rows if r['ip'] not in deleted]
                return canonical_nodes, filtered
    except Exception:
        pass

    return canonical_nodes, canonical_rows


def get_ip_list():
    """Get list of IP names from matrix data"""
    _, matrix_rows = get_matrix_data()
    return [row["ip"] for row in matrix_rows]


def extract_process_from_ip(ip_name: str) -> str:
    """Extract process technology from IP name using regex patterns"""
    match = re.search(r'rs_.*_([a-zA-Z0-9]+)_.*', ip_name.lower())
    if match:
        return match.group(1).upper()
    
    match = re.search(r'rs_.*_([a-zA-Z0-9]+)$', ip_name.lower())
    if match:
        return match.group(1).upper()
    
    common_processes = ['LN04LPP', 'LN05LPP', 'LN07LPP', 'LN13LPP', 'LN14LPP', 'LN28LPP']
    ip_lower = ip_name.lower()
    for process in common_processes:
        if process.lower() in ip_lower:
            return process
    return ip_name


def group_rows_by_process(rows: List[Dict]) -> Dict[str, List[Dict]]:
    """Group rows by extracted process technology"""
    grouped = {}
    for row in rows:
        ip_name = row.get('db_name') or row.get('ip_name') or ''
        process = extract_process_from_ip(ip_name)
        
        if process not in grouped:
            grouped[process] = []
        grouped[process].append(row)
    
    return grouped


def set_templates(tmpl):
    global templates
    templates = tmpl


def _ensure_templates():
    if templates is None:
        raise RuntimeError("Templates not initialized")


def ensure_authenticated(request: Request):
    if not request.session.get("is_authenticated"):
        return RedirectResponse(url="/auth/login", status_code=303)
    return None


def ensure_admin(request: Request):
                                                                                        
    is_admin_flag = request.session.get("is_admin", False)
    role = request.session.get("role")
    if not (role == "Admin" or is_admin_flag):
        app_logger.info("Admin access denied", {"role": role, "is_admin": bool(is_admin_flag), "user_email": request.session.get('user_email')})
        raise HTTPException(status_code=403, detail="Admin only")


def open_conn() -> sqlite3.Connection:
    conn = sqlite3.connect(str(PRODUCT_INFO_DB_PATH))
    conn.row_factory = sqlite3.Row
    return conn


def detect_table(conn: sqlite3.Connection) -> str | None:
    row = conn.execute(
        "SELECT name FROM sqlite_master WHERE type='table' AND lower(name) = 'ip_summary'"
    ).fetchone()
    if row:
        return row[0]
    return None


def get_columns(conn: sqlite3.Connection, table_name: str) -> List[str]:
    cols = conn.execute(f"PRAGMA table_info({table_name})").fetchall()
    return [c[1] for c in cols]


def filtered_columns(columns: List[str]) -> List[str]:
    return [c for c in columns if c.lower() not in EXCLUDED_COLUMNS and c.lower() not in ["id", "ip_name"]]


def get_display_headers() -> Dict[str, str]:
    return {
        "ip_name": "Category",
        "db_name": "IP Name",
        "tech": "Tech",
        "lane_configuration": "Lane Configuration",
        "process": "PDK",
        "drc_version": "DRC Version",
        "calibre": "Calibre",
        "metal": "Metal",
        "width_um": "Width(μm)",
        "height_um": "Height(μm)",
        "size_um2": "Size(μm²)",
        "version": "Version",
        "data_rate": "Data Rate",
        "power_m4s4": "Power(mW)",
        "customer": "Customer",
    }



def fetch_rows(conn: sqlite3.Connection, table_name: str, columns: List[str]) -> List[Dict]:
    query_cols = columns + ['ip_name']
    safe_cols = ", ".join([f'"{c}"' for c in query_cols])
    rows = conn.execute(
        f"SELECT rowid as __rowid__, {safe_cols} FROM {table_name} ORDER BY rowid DESC"
    ).fetchall()
    results: List[Dict] = []
    for row in rows:
        as_dict = {k: row[k] for k in row.keys()}
        results.append(as_dict)
    return results


def upsert_row(conn: sqlite3.Connection, table_name: str, columns: List[str], data: Dict, rowid: int | None) -> Dict:
    target_cols = [c for c in columns if c in data]
    if 'ip_name' in data:
        target_cols.append('ip_name')
    
    if not target_cols:
        raise HTTPException(status_code=400, detail="No valid columns to save")

    placeholders = ", ".join(["?" for _ in target_cols])
    col_clause = ", ".join([f'"{c}"' for c in target_cols])
    values = [data.get(c) for c in target_cols]

    if rowid:
        set_clause = ", ".join([f'"{c}" = ?' for c in target_cols])
        conn.execute(
            f"UPDATE {table_name} SET {set_clause} WHERE rowid = ?",
            values + [rowid],
        )
    else:
        conn.execute(
            f"INSERT INTO {table_name} ({col_clause}) VALUES ({placeholders})",
            values,
        )
        rowid = conn.execute("SELECT last_insert_rowid()").fetchone()[0]

    conn.commit()
    refresh_cols = columns + ['ip_name']
    refresh_clause = ", ".join([f'"{c}"' for c in refresh_cols])
    refreshed = conn.execute(
        f"SELECT rowid as __rowid__, {refresh_clause} FROM {table_name} WHERE rowid = ?",
        [rowid],
    ).fetchone()
    return {k: refreshed[k] for k in refreshed.keys()}


def delete_row(conn: sqlite3.Connection, table_name: str, rowid: int):
    conn.execute(f"DELETE FROM {table_name} WHERE rowid = ?", [rowid])
    conn.commit()


@router.get("/product-info", response_class=HTMLResponse)
def product_info_page(request: Request):
                                                                     
    session_param = request.query_params.get("session")
    if session_param:
                                          
        response = RedirectResponse(url="/product-info", status_code=303)
        response.set_cookie("rams_sess", session_param, max_age=30*60, path="/", httponly=True)
        return response

    _ensure_templates()
    auth_check = ensure_authenticated(request)
    if auth_check:
        return auth_check

    locale = get_locale(request)

    with open_conn() as conn:
        table_name = detect_table(conn)
        if not table_name:
                                                                                         
            raw_columns = []
            display_columns = []
            rows = []
            table_name = None
        else:
            raw_columns = get_columns(conn, table_name)
            display_columns = filtered_columns(raw_columns)
            rows = fetch_rows(conn, table_name, display_columns) if display_columns else []

    matrix_nodes, matrix_rows = get_matrix_data()

    app_logger.log_request("GET", "/product-info", request.session.get("user_email", "anonymous"))

    return templates.TemplateResponse(
        "modules/product_info/index.html",
        {
            "request": request,
            "locale": locale,
            "columns": display_columns,
            "rows": rows,
            "table_name": table_name,
            "is_admin": request.session.get("role") == "Admin",
            "matrix_nodes": matrix_nodes,
            "matrix_rows": matrix_rows,
        },
    )


@router.get("/product-info/ip/{ip_name:path}", response_class=HTMLResponse)
def product_info_detail(ip_name: str, request: Request):
    _ensure_templates()
    auth_check = ensure_authenticated(request)
    if auth_check:
        return auth_check

    ip_name = unquote(ip_name)
    locale = get_locale(request)
    matrix_nodes, matrix_rows = get_matrix_data()
    target = next((r for r in matrix_rows if r["ip"] == ip_name), None)
    if not target:
        raise HTTPException(status_code=404, detail="IP not found")

    with open_conn() as conn:
        table_name = detect_table(conn)
        if not table_name:
            columns: List[str] = []
            rows: List[Dict] = []
        else:
            raw_columns = get_columns(conn, table_name)
            columns = filtered_columns(raw_columns)
            rows = fetch_rows(conn, table_name, columns + ['ip_name']) if columns else []

    filtered_rows: List[Dict] = [row for row in rows if row.get('ip_name') == ip_name]

    grouped_rows = group_rows_by_process(filtered_rows)

    display_headers = get_display_headers()

    return templates.TemplateResponse(
        "modules/product_info/detail.html",
        {
            "request": request,
            "locale": locale,
            "ip_name": ip_name,
            "ip_statuses": target["statuses"],
            "grouped_rows": grouped_rows,
            "display_headers": display_headers,
            "is_admin": request.session.get("is_admin", False),
        },
    )


@router.get("/product-info/admin", response_class=HTMLResponse)
def product_info_admin_page(request: Request):
    _ensure_templates()
    auth_check = ensure_authenticated(request)
    if auth_check:
        return auth_check
    ensure_admin(request)

    locale = get_locale(request)

    with open_conn() as conn:
        table_name = detect_table(conn)
        if not table_name:
            return templates.TemplateResponse(
                "modules/product_info/missing_table.html",
                {
                    "request": request,
                    "locale": locale,
                    "table_name": "IP_SUMMARY",
                    "is_admin": request.session.get("is_admin", False),
                },
            )

        raw_columns = get_columns(conn, table_name)
        display_columns = filtered_columns(raw_columns)
        rows = fetch_rows(conn, table_name, display_columns) if display_columns else []

    display_headers = get_display_headers()
    ip_list = get_ip_list()
    matrix_nodes, matrix_rows = get_matrix_data()

    app_logger.log_request("GET", "/product-info/admin", request.session.get("user_email", "anonymous"))

    return templates.TemplateResponse(
        "modules/product_info/admin.html",
        {
            "request": request,
            "locale": locale,
            "columns": display_columns,
            "rows": rows,
            "table_name": table_name,
            "display_headers": display_headers,
            "ip_list": ip_list,
            "matrix_nodes": matrix_nodes,
            "matrix_rows": matrix_rows,
            "is_admin": request.session.get("is_admin", False),
        },
    )


@router.get("/pinf")
def product_info_short_redirect():
    return RedirectResponse(url="/product-info", status_code=303)


@router.post("/product-info/api/rows")
def upsert_product_info(request: Request, payload: Dict = Body(...)):
    auth_check = ensure_authenticated(request)
    if auth_check:
        return auth_check
    ensure_admin(request)

    rowid = payload.get("rowid")
    data = payload.get("data") or {}

    with open_conn() as conn:
        table_name = detect_table(conn)
        if not table_name:
            raise HTTPException(status_code=400, detail="IP_SUMMARY table not found")

        raw_columns = get_columns(conn, table_name)
        display_columns = filtered_columns(raw_columns)
        saved = upsert_row(conn, table_name, display_columns, data, rowid)

    return JSONResponse({"ok": True, "row": saved})


@router.delete("/product-info/api/rows/{rowid}")
def delete_product_info(request: Request, rowid: int):
    auth_check = ensure_authenticated(request)
    if auth_check:
        return auth_check
    ensure_admin(request)

    with open_conn() as conn:
        table_name = detect_table(conn)
        if not table_name:
            raise HTTPException(status_code=400, detail="IP_SUMMARY table not found")

        delete_row(conn, table_name, rowid)

    return JSONResponse({"ok": True})


@router.post("/product-info/api/matrix")
def upsert_matrix_row(request: Request, payload: Dict = Body(...)):
    auth_check = ensure_authenticated(request)
    if auth_check:
        return auth_check
    ensure_admin(request)

    ip_name = payload.get("ip_name", "").strip()
    statuses = payload.get("statuses", {})

    if not ip_name:
        raise HTTPException(status_code=400, detail="IP name is required")

    with open_conn() as conn:
                                          
        conn.execute("""
            CREATE TABLE IF NOT EXISTS IP_MATRIX (
                ip_name TEXT NOT NULL,
                node TEXT NOT NULL,
                status TEXT,
                updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                PRIMARY KEY (ip_name, node)
            )
        """)

                                      
        for node, status in statuses.items():
            conn.execute("""
                INSERT OR REPLACE INTO IP_MATRIX (ip_name, node, status, updated_at)
                VALUES (?, ?, ?, CURRENT_TIMESTAMP)
            """, (ip_name, node, status))

                                                                                   
        conn.execute("CREATE TABLE IF NOT EXISTS IP_MATRIX_DELETED (ip_name TEXT PRIMARY KEY, deleted_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP)")
        conn.execute("DELETE FROM IP_MATRIX_DELETED WHERE ip_name = ?", (ip_name,))

        conn.commit()

    app_logger.info("Matrix row updated", {
        "ip": ip_name,
        "user": request.session.get("username")
    })

    return JSONResponse({"ok": True})


@router.delete("/product-info/api/matrix/{ip_name:path}")
def delete_matrix_row(ip_name: str, request: Request):
    auth_check = ensure_authenticated(request)
    if auth_check:
        return auth_check
    ensure_admin(request)

    ip_name = unquote(ip_name)

    with open_conn() as conn:
                               
        cursor = conn.cursor()
        cursor.execute("SELECT name FROM sqlite_master WHERE type='table' AND name='IP_MATRIX'")
        if not cursor.fetchone():
            raise HTTPException(status_code=404, detail="IP_MATRIX table not found")

                                                            
        cursor.execute("DELETE FROM IP_MATRIX WHERE ip_name = ?", (ip_name,))
        deleted_count = cursor.rowcount
        conn.commit()

                                                                             
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS IP_MATRIX_DELETED (
                ip_name TEXT PRIMARY KEY,
                deleted_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        ''')
        cursor.execute("INSERT OR REPLACE INTO IP_MATRIX_DELETED (ip_name) VALUES (?)", (ip_name,))
        conn.commit()

    app_logger.info("Matrix row deleted", {
        "ip": ip_name,
        "user": request.session.get("username")
    })

    result = JSONResponse({"ok": True})

                                                                                                      
    return result


@router.get("/product-info/api/matrix")
def api_get_matrix(request: Request):
    """Return the current matrix as JSON (nodes + rows)"""
    auth_check = ensure_authenticated(request)
    if auth_check:
        return auth_check
    matrix_nodes, matrix_rows = get_matrix_data()
    return JSONResponse({"ok": True, "nodes": matrix_nodes, "rows": matrix_rows})


@router.put("/product-info/api/status/{ip_name:path}/{node}")
def update_ip_status(ip_name: str, node: str, request: Request, payload: Dict = Body(...)):
    auth_check = ensure_authenticated(request)
    if auth_check:
        return auth_check
    ensure_admin(request)

    ip_name = unquote(ip_name)
    status = payload.get("status")

                           
    valid_statuses = ["", "mass", "proven", "dev", "plan"]
    if status not in valid_statuses:
        raise HTTPException(status_code=400, detail="Invalid status value")

    try:
        with open_conn() as conn:
            cur = conn.cursor()
            cur.execute("SELECT name FROM sqlite_master WHERE type='table' AND name='IP_MATRIX'")
            if not cur.fetchone():
                                         
                cur.execute('''
                    CREATE TABLE IF NOT EXISTS IP_MATRIX (
                        ip_name TEXT NOT NULL,
                        node TEXT NOT NULL,
                        status TEXT,
                        updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                        PRIMARY KEY (ip_name, node)
                    )
                ''')

            if not status:
                             
                cur.execute("DELETE FROM IP_MATRIX WHERE ip_name = ? AND node = ?", (ip_name, node))
            else:
                cur.execute("INSERT OR REPLACE INTO IP_MATRIX (ip_name, node, status, updated_at) VALUES (?, ?, ?, CURRENT_TIMESTAMP)", (ip_name, node, status))
            conn.commit()
    except Exception as e:
        app_logger.warning(f"Failed to update IP_MATRIX: {e}")
        raise HTTPException(status_code=500, detail="Failed to update status")

    app_logger.info("IP status updated", {
        "ip": ip_name,
        "node": node,
        "status": status,
        "user": request.session.get("username")
    })

    return JSONResponse({"ok": True, "status": status})


@router.get("/help", response_class=HTMLResponse)
def help_page(request: Request):
    """Display Product Info help page"""
    locale = get_locale(request)
    return templates.TemplateResponse(
        "modules/product_info/help.html",
        {"request": request, "locale": locale}
    )

