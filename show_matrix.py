import sqlite3, pprint, logging
logger = logging.getLogger(__name__)
conn = sqlite3.connect('rpmt.db')
cur = conn.cursor()
cur.execute("SELECT name FROM sqlite_master WHERE type='table' AND name='IP_MATRIX'")
r = cur.fetchone()
if not r:
    logger.warning('IP_MATRIX table not found')
else:
    cur.execute('SELECT ip_name,node,status FROM IP_MATRIX ORDER BY ip_name,node')
    rows = cur.fetchall()
    logger.info('IP_MATRIX rows count: %d', len(rows))
    logger.debug('IP_MATRIX rows:\n%s', pprint.pformat(rows))
