import psycopg2
conn = psycopg2.connect('dbname=diansukses user=openpg host=localhost port=5432 password=openpgpwd')
cur=conn.cursor()
cur.execute('''
    SELECT module, name, res_id
    FROM ir_model_data
    WHERE model = 'stock.picking.type' AND name LIKE '%out%'
''')
results = cur.fetchall()
for row in results:
    print(row)

