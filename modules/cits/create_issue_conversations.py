"""
Create issue_conversations table from scratch
"""
import sqlite3
from datetime import datetime

DB_PATH = "modules/cits/cits.db"

def create_issue_conversations_table():
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    
    try:
                                          
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS issue_conversations (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                issue_id INTEGER NOT NULL,
                inquiry_id INTEGER,
                type VARCHAR(50) NOT NULL,
                content TEXT,
                created_by VARCHAR(128),
                created_at DATETIME DEFAULT CURRENT_TIMESTAMP
            )
        """)
        
        cursor.execute("CREATE INDEX IF NOT EXISTS ix_conversations_issue_id ON issue_conversations(issue_id)")
        cursor.execute("CREATE INDEX IF NOT EXISTS ix_conversations_inquiry_id ON issue_conversations(inquiry_id)")
        
        conn.commit()
        import logging
        logger = logging.getLogger(__name__)
        logger.info("issue_conversations table created successfully")
            
    except Exception as e:
        logger.exception("Error creating issue_conversations table")
        conn.rollback()
    finally:
        conn.close()

if __name__ == "__main__":
    create_issue_conversations_table()
