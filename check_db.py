import mysql.connector

try:
    conn = mysql.connector.connect(host='localhost', user='root', password='', database='library_db', use_pure=True)  # use_pure avoids segfault on Python 3.14
    cur = conn.cursor()
    cur.execute('SELECT COUNT(*) FROM books')
    print('COUNT', cur.fetchone())
    cur.execute('SELECT title,author,category,available_copies FROM books LIMIT 5')
    print('ROWS', cur.fetchall())
    conn.close()
except Exception as e:
    import traceback
    print('ERROR', type(e).__name__, e)
    traceback.print_exc()
