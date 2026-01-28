import sqlite3
from pathlib import Path
from datetime import datetime
import logging

logger = logging.getLogger(__name__)

SVIT_DB_PATH = Path(__file__).parent.parent.parent / "svit.db"

def is_valid_datetime(value):
    """Check if value is a valid datetime string"""
    if not value or not isinstance(value, str):
        return True
    
    stripped = value.strip()
    if not stripped or len(stripped) <= 1:
        return False
    
    try:
        datetime.fromisoformat(stripped.replace('Z', '+00:00'))
        return True
    except (ValueError, TypeError):
        return False

def clean_database():
    """Clean corrupted datetime values in SVIT database"""
    if not SVIT_DB_PATH.exists():
        logger.warning("SVIT DB not found: %s", SVIT_DB_PATH)
        return False
    
    logger.info("Starting SVIT DB clean: %s", SVIT_DB_PATH)
    logger.info("DB path: %s", SVIT_DB_PATH)
    
    try:
        conn = sqlite3.connect(SVIT_DB_PATH)
        conn.row_factory = sqlite3.Row
        cursor = conn.cursor()
        
        now_iso = datetime.utcnow().isoformat()
        
        datetime_columns = [
            'report_date',
            'created_at',
            'updated_at',
            'resolved_at'
        ]
        
        cursor.execute("SELECT name FROM sqlite_master WHERE type='table' AND name='issues'")
        if not cursor.fetchone():
            logger.warning("'issues' table not found in SVIT DB")
            conn.close()
            return False
        
        cursor.execute("PRAGMA table_info(issues)")
        columns = {row[1]: row[2] for row in cursor.fetchall()}
        
        total_fixed = 0
        
        for col in datetime_columns:
            if col not in columns:
                continue
            
            cursor.execute(f"SELECT id, {col} FROM issues WHERE {col} IS NOT NULL")
            
            bad_rows = []
            for row in cursor.fetchall():
                row_id = row[0]
                value = row[1]
                
                if not is_valid_datetime(value):
                    bad_rows.append(row_id)
            
            if bad_rows:
                logger.info("Fixing %d bad rows for column %s", len(bad_rows), col)
                placeholders = ','.join('?' * len(bad_rows))
                cursor.execute(f"""
                    UPDATE issues SET {col} = ? WHERE id IN ({placeholders})
                """, [now_iso] + bad_rows)
                total_fixed += len(bad_rows)
                logger.debug("Column %s fixed %d rows to %s", col, len(bad_rows), now_iso)
        
        conn.commit()
        
        cursor.execute("SELECT COUNT(*) as total FROM issues")
        total_records = cursor.fetchone()[0]
        
        logger.info("Clean summary: total=%d, fixed=%d", total_records, total_fixed)
        
        conn.close()
        
        if total_fixed > 0:
            logger.info("SVIT DB clean complete: %d rows fixed", total_fixed)
        else:
            logger.info("SVIT DB clean complete: no changes needed")
        
        return True
        
    except Exception:
        logger.exception("Error during SVIT DB clean")
        return False

if __name__ == "__main__":
    clean_database()

