import psycopg2
conn = psycopg2.connect('dbname=diansukses user=openpg host=localhost port=5432 password=openpgpwd')
cur=conn.cursor()
cur.execute('''
    SELECT table_name FROM information_schema.tables WHERE table_name LIKE '%attendance%'
''')
results = cur.fetchall()
for row in results:
    print(row)



