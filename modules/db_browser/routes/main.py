from fastapi import APIRouter, Request, HTTPException, Depends, Query
from fastapi.responses import HTMLResponse
from fastapi.templating import Jinja2Templates
from sqlalchemy import inspect, text
from sqlalchemy.orm import Session
from pathlib import Path
from core.config import BASE_DIR
from modules.spec_center.db import SessionLocal as SpecSessionLocal
from modules.svit.db import SessionLocal as SvitSessionLocal
from modules.rpmt.db import RPMTSessionLocal as RpmtSessionLocal
from modules.cits.db import SessionLocal as CustomerSessionLocal
import json

router = APIRouter(prefix="/db-browser", tags=["db_browser"])

TEMPLATES = Jinja2Templates(directory=str(Path(BASE_DIR) / "templates"))

DATABASES = {
    "spec_center": {
        "name": "spec_center",
        "display_name": "Spec Center",
        "path": "spec_center.db",
        "session_factory": SpecSessionLocal,
        "description": "洹쒓꺽 愿由??곗씠?곕쿋?댁뒪"
    },
    "svit": {
        "name": "svit",
        "display_name": "SVIT",
        "path": "svit.db",
        "session_factory": SvitSessionLocal,
        "description": "SVIT 臾몄젣 異붿쟻 ?곗씠?곕쿋?댁뒪"
    },
    "rpmt": {
        "name": "rpmt",
        "display_name": "RPMT",
        "path": "rpmt.db",
        "session_factory": RpmtSessionLocal,
        "description": "RPMT ?꾨줈?앺듃 愿由??곗씠?곕쿋?댁뒪"
    },
    "customer_issue": {
        "name": "customer_issue",
        "display_name": "Customer Issue",
        "path": "customer_issue.db",
        "session_factory": CustomerSessionLocal,
        "description": "怨좉컼 臾몄젣 異붿쟻 ?곗씠?곕쿋?댁뒪"
    }
}


def get_db_for_name(db_name: str):
    """Get database session based on database name"""
    if db_name not in DATABASES:
        raise HTTPException(status_code=400, detail=f"Database '{db_name}' not found")
    
    return DATABASES[db_name]["session_factory"]()


@router.get("/", response_class=HTMLResponse)
def db_browser_page(request: Request):
    """Main DB Browser page"""
    return TEMPLATES.TemplateResponse("db_browser/index.html", {"request": request})


@router.get("/api/databases")
def list_databases():
    """List available databases"""
    return {
        "databases": [
            {
                "name": db["name"],
                "display_name": db["display_name"],
                "path": db["path"],
                "description": db["description"]
            }
            for db in DATABASES.values()
        ]
    }


@router.get("/api/tables")
def list_tables(db_name: str = Query("spec_center")):
    """List all tables in the database"""
    db = get_db_for_name(db_name)
    try:
        inspector = inspect(db.get_bind())
        tables = inspector.get_table_names()
        
        table_info = []
        for table_name in tables:
            columns = inspector.get_columns(table_name)
            row_count = db.execute(text(f"SELECT COUNT(*) FROM {table_name}")).scalar()
            
            table_info.append({
                "name": table_name,
                "columns": [col["name"] for col in columns],
                "row_count": row_count,
                "column_details": [
                    {
                        "name": col["name"],
                        "type": str(col["type"]),
                        "nullable": col["nullable"],
                        "default": str(col["default"]) if col["default"] else None
                    }
                    for col in columns
                ]
            })
        
        return {"tables": table_info}
    finally:
        db.close()


@router.get("/api/table/{table_name}")
def get_table_data(
    table_name: str,
    db_name: str = Query("spec_center"),
    page: int = Query(1, ge=1),
    limit: int = Query(50, ge=1, le=1000)
):
    """Get paginated table data"""
    db = get_db_for_name(db_name)
    try:
        inspector = inspect(db.get_bind())
        tables = inspector.get_table_names()
        
        if table_name not in tables:
            raise HTTPException(status_code=404, detail=f"Table '{table_name}' not found")
        
        total = db.execute(text(f"SELECT COUNT(*) FROM {table_name}")).scalar()
        
        columns = inspector.get_columns(table_name)
        col_names = [col["name"] for col in columns]
        
        offset = (page - 1) * limit
        query = f"SELECT * FROM {table_name} LIMIT {limit} OFFSET {offset}"
        result = db.execute(text(query))
        rows = result.fetchall()
        
        data = []
        for row in rows:
            data.append(dict(row._mapping))
        
        return {
            "table": table_name,
            "total": total,
            "page": page,
            "limit": limit,
            "pages": (total + limit - 1) // limit,
            "columns": col_names,
            "data": data
        }
    finally:
        db.close()


@router.get("/api/table/{table_name}/search")
def search_table(
    table_name: str,
    q: str = Query(""),
    column: str = Query(""),
    db_name: str = Query("spec_center"),
    page: int = Query(1, ge=1),
    limit: int = Query(50, ge=1, le=1000)
):
    """Search table data"""
    db = get_db_for_name(db_name)
    try:
        inspector = inspect(db.get_bind())
        tables = inspector.get_table_names()
        
        if table_name not in tables:
            raise HTTPException(status_code=404, detail=f"Table '{table_name}' not found")
        
        columns = inspector.get_columns(table_name)
        col_names = [col["name"] for col in columns]
        
        if column and column not in col_names:
            raise HTTPException(status_code=400, detail=f"Column '{column}' not found")
        
        if column:
            where_clause = f"WHERE {column} LIKE '%{q}%'"
        else:
            text_cols = [col["name"] for col in columns if "VARCHAR" in str(col["type"]) or "TEXT" in str(col["type"])]
            if not text_cols:
                where_clause = ""
            else:
                conditions = " OR ".join([f"{col} LIKE '%{q}%'" for col in text_cols])
                where_clause = f"WHERE {conditions}"
        
        count_query = f"SELECT COUNT(*) FROM {table_name} {where_clause}"
        total = db.execute(text(count_query)).scalar()
        
        offset = (page - 1) * limit
        query = f"SELECT * FROM {table_name} {where_clause} LIMIT {limit} OFFSET {offset}"
        result = db.execute(text(query))
        rows = result.fetchall()
        
        data = []
        for row in rows:
            data.append(dict(row._mapping))
        
        return {
            "table": table_name,
            "search_query": q,
            "total": total,
            "page": page,
            "limit": limit,
            "pages": (total + limit - 1) // limit,
            "columns": col_names,
            "data": data
        }
    finally:
        db.close()


@router.delete("/api/table/{table_name}/{row_id}")
def delete_row(
    table_name: str,
    row_id: int,
    db_name: str = Query("spec_center")
):
    """Delete a row from table"""
    db = get_db_for_name(db_name)
    try:
        inspector = inspect(db.get_bind())
        tables = inspector.get_table_names()
        
        if table_name not in tables:
            raise HTTPException(status_code=404, detail=f"Table '{table_name}' not found")
        
        pk_cols = inspector.get_pk_constraint(table_name)["constrained_columns"]
        if not pk_cols:
            raise HTTPException(status_code=400, detail="Table has no primary key")
        
        pk_col = pk_cols[0]
        
        db.execute(text(f"DELETE FROM {table_name} WHERE {pk_col} = {row_id}"))
        db.commit()
        return {"ok": True, "message": f"Row {row_id} deleted"}
    except Exception as e:
        db.rollback()
        raise HTTPException(status_code=500, detail=str(e))
    finally:
        db.close()


@router.post("/api/table/{table_name}")
def insert_row(
    table_name: str,
    data: dict,
    db_name: str = Query("spec_center")
):
    """Insert a new row"""
    db = get_db_for_name(db_name)
    try:
        inspector = inspect(db.get_bind())
        tables = inspector.get_table_names()
        
        if table_name not in tables:
            raise HTTPException(status_code=404, detail=f"Table '{table_name}' not found")
        
        columns = ", ".join(data.keys())
        values = ", ".join([f"'{v}'" if isinstance(v, str) else str(v) for v in data.values()])
        query = f"INSERT INTO {table_name} ({columns}) VALUES ({values})"
        db.execute(text(query))
        db.commit()
        return {"ok": True, "message": "Row inserted"}
    except Exception as e:
        db.rollback()
        raise HTTPException(status_code=500, detail=str(e))
    finally:
        db.close()


@router.put("/api/table/{table_name}/{row_id}")
def update_row(
    table_name: str,
    row_id: int,
    data: dict,
    db_name: str = Query("spec_center")
):
    """Update a row"""
    db = get_db_for_name(db_name)
    try:
        inspector = inspect(db.get_bind())
        tables = inspector.get_table_names()
        
        if table_name not in tables:
            raise HTTPException(status_code=404, detail=f"Table '{table_name}' not found")
        
        pk_cols = inspector.get_pk_constraint(table_name)["constrained_columns"]
        if not pk_cols:
            raise HTTPException(status_code=400, detail="Table has no primary key")
        
        pk_col = pk_cols[0]
        
        set_clause = ", ".join([f"{k} = '{v}'" if isinstance(v, str) else f"{k} = {v}" for k, v in data.items()])
        query = f"UPDATE {table_name} SET {set_clause} WHERE {pk_col} = {row_id}"
        db.execute(text(query))
        db.commit()
        return {"ok": True, "message": "Row updated"}
    except Exception as e:
        db.rollback()
        raise HTTPException(status_code=500, detail=str(e))
    finally:
        db.close()


                          
@router.get("/api/common-info")
def get_common_data_info():
    """Get common data summary for display"""
    try:
        from core.db import SessionLocal
        session = SessionLocal()
        
        from core.common_data_schema import Product, ProductVariant, ProductConfig
        
        total_products = session.query(Product).count()
        total_variants = session.query(ProductVariant).count()
        total_configs = session.query(ProductConfig).count()
        
        session.close()
        
        return {
            "success": True,
            "data": {
                "total_products": total_products,
                "total_variants": total_variants,
                "total_configs": total_configs
            }
        }
    except Exception as e:
        return {"success": False, "error": str(e)}


@router.get("/api/data")
def get_table_data(db_name: str = Query("spec_center"), table: str = Query(None)):
    """Get all data from a table"""
    if not table:
        raise HTTPException(status_code=400, detail="Table name required")
    
    db = get_db_for_name(db_name)
    try:
        result = db.execute(text(f"SELECT * FROM {table}"))
        rows = result.fetchall()
        
                                      
        data = []
        if rows:
            columns = [desc[0] for desc in result.description]
            for row in rows:
                data.append(dict(zip(columns, row)))
        
        db.close()
        return {"success": True, "data": data, "count": len(data)}
    except Exception as e:
        db.close()
        raise HTTPException(status_code=500, detail=str(e))

