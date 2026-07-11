import sqlite3
import json

conn = sqlite3.connect('zepp_life.db')
c = conn.cursor()
c.execute("SELECT * FROM body_measurements ORDER BY date DESC LIMIT 5")
rows = c.fetchall()
col_names = [description[0] for description in c.description]
for row in rows:
    data = dict(zip(col_names, row))
    # Parse the raw_data JSON if it exists
    if 'raw_data' in data:
        data['raw_data'] = json.loads(data['raw_data'])
    print(json.dumps(data, indent=2, ensure_ascii=False))
conn.close()
