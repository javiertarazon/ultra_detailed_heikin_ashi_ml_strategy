import sqlite3

conn = sqlite3.connect('data/data.db')
cursor = conn.cursor()
cursor.execute('SELECT name FROM sqlite_master WHERE type="table" AND name LIKE "%BNB%"')
tables = cursor.fetchall()
print('Tablas disponibles para BNB:')
for table in tables:
    print(f'  - {table[0]}')
conn.close()