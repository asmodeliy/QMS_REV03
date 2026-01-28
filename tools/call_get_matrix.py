import sys, os, logging
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))
from modules.product_info.routes import get_matrix_data
logger = logging.getLogger(__name__)

try:
    nodes, rows = get_matrix_data()
    logger.info('nodes: %s', nodes)
    logger.info('rows count: %d', len(rows))
    logger.debug('rows sample: %s', rows[:5])
except Exception:
    logger.exception('Failed to get matrix data')
