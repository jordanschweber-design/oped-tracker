import sqlite3
from datetime import datetime, timezone, timedelta
from email.utils import parsedate_to_datetime

conn = sqlite3.connect('oped_data.db')
cutoff = datetime.now(timezone.utc) - timedelta(days=180)

articles = conn.execute('SELECT id, published FROM articles').fetchall()
to_delete = []
for a in articles:
    if not a[1]:
        continue
    try:
        dt = parsedate_to_datetime(a[1])
        if dt.tzinfo is None:
            dt = dt.replace(tzinfo=timezone.utc)
        if dt > cutoff:
            to_delete.append(a[0])
    except Exception:
        pass

print(f'Deleting {len(to_delete)} recent articles')
if to_delete:
    placeholders = ",".join("?" * len(to_delete))
    conn.execute(f'DELETE FROM predictions WHERE article_id IN ({placeholders})', to_delete)
    conn.execute(f'DELETE FROM articles WHERE id IN ({placeholders})', to_delete)
    conn.commit()
print('Done')
