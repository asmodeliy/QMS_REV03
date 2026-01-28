import sqlite3

matrix_nodes = ["SF28nm", "SF14nm", "SF8nm", "SF5nm", "SF4nm"]

matrix_rows = [
    {"ip": "MIPI D/C PHY Combo", "statuses": {"SF28nm": None, "SF14nm": "mass", "SF8nm": "proven", "SF5nm": None, "SF4nm": None}},
    {"ip": "MIPI D-PHY", "statuses": {"SF28nm": "mass", "SF14nm": "mass", "SF8nm": "proven", "SF5nm": "proven", "SF4nm": None}},
    {"ip": "MIPI A-PHY", "statuses": {"SF28nm": None, "SF14nm": "dev", "SF8nm": None, "SF5nm": None, "SF4nm": None}},
    {"ip": "ARM HSSTP TX PHY", "statuses": {"SF28nm": None, "SF14nm": "proven", "SF8nm": "proven", "SF5nm": "plan", "SF4nm": None}},
    {"ip": "USB DP TX PHY", "statuses": {"SF28nm": None, "SF14nm": None, "SF8nm": "proven", "SF5nm": None, "SF4nm": None}},
    {"ip": "HDMI TX PHY", "statuses": {"SF28nm": None, "SF14nm": None, "SF8nm": "proven", "SF5nm": None, "SF4nm": None}},
    {"ip": "PCIe PHY", "statuses": {"SF28nm": None, "SF14nm": None, "SF8nm": None, "SF5nm": "plan", "SF4nm": None}},
    {"ip": "UCIe PHY", "statuses": {"SF28nm": None, "SF14nm": None, "SF8nm": None, "SF5nm": "plan", "SF4nm": None}},
    {"ip": "DDR PHY", "statuses": {"SF28nm": "mass", "SF14nm": "mass", "SF8nm": "mass", "SF5nm": "proven", "SF4nm": "dev"}},
    {"ip": "Ethernet PHY", "statuses": {"SF28nm": "mass", "SF14nm": "mass", "SF8nm": "proven", "SF5nm": "plan", "SF4nm": None}},
    {"ip": "USB 3.0 PHY", "statuses": {"SF28nm": "mass", "SF14nm": "mass", "SF8nm": "proven", "SF5nm": "proven", "SF4nm": "plan"}},
    {"ip": "SATA PHY", "statuses": {"SF28nm": "mass", "SF14nm": "mass", "SF8nm": "proven", "SF5nm": None, "SF4nm": None}},
]

conn = sqlite3.connect('rpmt.db')
cur = conn.cursor()
cur.execute("CREATE TABLE IF NOT EXISTS IP_MATRIX (ip_name TEXT NOT NULL, node TEXT NOT NULL, status TEXT, PRIMARY KEY (ip_name, node))")
                                        
cur.execute("DELETE FROM IP_MATRIX")
count = 0
for row in matrix_rows:
    ip = row['ip']
    for node in matrix_nodes:
        status = row['statuses'].get(node)
        cur.execute("INSERT OR REPLACE INTO IP_MATRIX (ip_name, node, status) VALUES (?, ?, ?)", (ip, node, status))
        count += 1
conn.commit()
conn.close()

import logging
logger = logging.getLogger(__name__)
logger.info(f"Seeded IP_MATRIX with {count} rows")