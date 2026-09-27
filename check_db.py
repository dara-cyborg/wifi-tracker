import os
import sqlite3
p='wifi_tracker.db'
print('path', os.path.abspath(p))
print('exists', os.path.exists(p))
if os.path.exists(p):
    st=os.stat(p)
    print('size', st.st_size)
    with open(p,'rb') as f:
        head=f.read(64)
    print('head', head[:16])
    try:
        con=sqlite3.connect(p)
        cur=con.cursor()
        cur.execute('PRAGMA integrity_check;')
        print('integrity', cur.fetchone())
        cur.execute('SELECT name FROM sqlite_master WHERE type="table";')
        print('tables', cur.fetchall())
        con.close()
    except Exception as e:
        print('sqlite error', type(e).__name__, e)
