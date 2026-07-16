import psycopg2
conn = psycopg2.connect('dbname=diansukses user=openpg host=localhost port=5432 password=openpgpwd')
cur=conn.cursor()
cur.execute('''SELECT name, state FROM ir_module_module WHERE name = 'coco_theme' OR name = 'web_theme_pt_coco' ''')
results = cur.fetchall()
for row in results:
    print(row)
