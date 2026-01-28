"""
Migration script to add tag column and create issue_conversations table
Run: python -m modules.cits.migrate_conversations
"""
from pathlib import Path
from sqlalchemy import create_engine, text

DB_PATH = Path(__file__).parent.parent.parent / "customer_issue.db"

def migrate():
    engine = create_engine(f'sqlite:///{DB_PATH}')
    
    with engine.connect() as conn:
        import logging
        logger = logging.getLogger(__name__)
        try:
            conn.execute(text("ALTER TABLE customer_issues ADD COLUMN tag VARCHAR(50)"))
            conn.commit()
            logger.info("Added 'tag' column to customer_issues")
        except Exception as e:
            if 'duplicate column' in str(e).lower():
                logger.info("'tag' column already exists")
            else:
                logger.exception("Error adding tag column")
        
        try:
            conn.execute(text("""
                CREATE TABLE IF NOT EXISTS issue_conversations (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    issue_id INTEGER NOT NULL,
                    type VARCHAR(20) NOT NULL,
                    content TEXT NOT NULL,
                    created_by VARCHAR(128),
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    FOREIGN KEY (issue_id) REFERENCES customer_issues(id) ON DELETE CASCADE
                )
            """))
            conn.execute(text("CREATE INDEX IF NOT EXISTS ix_conversations_issue_id ON issue_conversations(issue_id)"))
            conn.commit()
            logger.info("Created issue_conversations table")
        except Exception:
            logger.exception("Error creating conversations table")
    
    logger.info("\nMigration complete!")

if __name__ == '__main__':
    migrate()

