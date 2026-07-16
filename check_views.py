import psycopg2
conn = psycopg2.connect('dbname=diansukses user=openpg host=localhost port=5432 password=openpgpwd')
cur=conn.cursor()
cur.execute('''SELECT arch_db::text FROM ir_ui_view WHERE key = 'coco_theme.coco_login_layout' ''')
print(cur.fetchone()[0])
