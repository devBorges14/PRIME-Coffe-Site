import sqlite3

conn = sqlite3.connect("database/site.db")
cursor = conn.cursor()

cursor.execute("SELECT * FROM leads")

for lead in cursor.fetchall():
    print(lead)

conn.close()    