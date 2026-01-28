import sqlite3, logging, pprint
logger = logging.getLogger(__name__)

conn = sqlite3.connect('rpmt.db')
cur = conn.cursor()
logger.info('IP_MATRIX schema:')
try:
    cols = cur.execute('PRAGMA table_info(IP_MATRIX)').fetchall()
    logger.debug('PRAGMA table_info: %s', pprint.pformat(cols))
except Exception as e:
    logger.error('PRAGMA error', exc_info=True)

logger.info('Does IP_MATRIX table exist?')
cur.execute("SELECT name FROM sqlite_master WHERE type='table' AND name='IP_MATRIX'")
logger.info('Table present: %s', cur.fetchone())

logger.info('Sample row or error:')
try:
    logger.debug('Sample row: %s', cur.execute('SELECT * FROM IP_MATRIX LIMIT 1').fetchone())
except Exception:
    logger.exception('Error selecting sample row')

logger.info('IP_MATRIX rows count:')
try:
    logger.info('Rows count: %s', cur.execute('SELECT count(*) FROM IP_MATRIX').fetchone())
except Exception:
    logger.exception('Error counting rows')
