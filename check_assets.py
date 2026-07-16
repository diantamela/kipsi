import psycopg2
conn = psycopg2.connect('dbname=diansukses user=openpg host=localhost port=5432 password=openpgpwd')
cur=conn.cursor()
cur.execute('''SELECT id, name, path FROM ir_asset WHERE path LIKE '%coco_theme%' ''')
results = cur.fetchall()
for row in results:
    print(row)
