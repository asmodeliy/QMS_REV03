from pathlib import Path
import sys
import sqlite3
import logging

logger = logging.getLogger(__name__)

DB_PATH = Path(__file__).resolve().parent.parent.parent / "customer_issue.db"
logger.info('Using DB: %s', DB_PATH)
if not DB_PATH.exists():
    logger.error('DB not found, exiting: %s', DB_PATH)
    sys.exit(1)

conn = sqlite3.connect(str(DB_PATH))
cur = conn.cursor()
cur.execute("PRAGMA table_info('customer_issues')")
cols = [r[1] for r in cur.fetchall()]
logger.debug('Existing columns: %s', cols)
changes = []
if 'customer' not in cols:
    try:
        cur.execute("ALTER TABLE customer_issues ADD COLUMN customer TEXT")
        changes.append('customer')
    except Exception as e:
        logger.exception('Failed to add customer column')
if 'ip_ic' not in cols:
    try:
        cur.execute("ALTER TABLE customer_issues ADD COLUMN ip_ic TEXT")
        changes.append('ip_ic')
    except Exception as e:
        logger.exception('Failed to add ip_ic column')

if changes:
    conn.commit()
    logger.info('Added columns: %s', changes)
else:
    logger.info('No changes needed.')

conn.close()

