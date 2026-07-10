import psycopg2
try:
    conn = psycopg2.connect(dbname='diansukses', user='odoo', password='odoo', host='localhost')
    cur = conn.cursor()
    cur.execute("SELECT pt.name, pu.name, pc.name FROM product_template pt JOIN uom_uom pu ON pt.uom_id = pu.id JOIN uom_category pc ON pu.category_id = pc.id WHERE pt.name::text LIKE '%Kelapa Layak Produksi%'")
    print(cur.fetchall())
except Exception as e:
    print(e)
