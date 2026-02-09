"""
Add countermeasure_attach column to modules/svit/issues table if missing.
Run from project root:
    python scripts/migrate_add_countermeasure_attach.py
"""
from pathlib import Path
import sqlite3

DB = Path(__file__).parent.parent / 'svit.db'
print('Using DB:', DB)
if not DB.exists():
    print('DB not found - nothing to do.')
    raise SystemExit(1)

conn = sqlite3.connect(str(DB))
cur = conn.cursor()
cur.execute("PRAGMA table_info(issues)")
cols = [r[1] for r in cur.fetchall()]
if 'countermeasure_attach' in cols:
    print('Column already present - nothing to do')
else:
    print('Adding countermeasure_attach column')
    cur.execute("ALTER TABLE issues ADD COLUMN countermeasure_attach TEXT")
    conn.commit()
    print('Column added')
conn.close()
