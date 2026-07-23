import psycopg2
conn = psycopg2.connect('dbname=diansukses user=openpg host=localhost port=5432 password=openpgpwd')
cur = conn.cursor()

cur.execute("""
    SELECT m.id, m.name->>'en_US' as name_en, m.sequence, m.parent_id, m.action,
           im.module, im.name as xml_id
    FROM ir_ui_menu m
    JOIN ir_model_data im ON im.res_id = m.id AND im.model = 'ir.ui.menu'
    WHERE im.module = 'mrp' OR m.parent_id IN (
        SELECT res_id FROM ir_model_data WHERE model = 'ir.ui.menu' AND name = 'menu_mrp_root'
    ) OR m.name->>'en_US' ILIKE '%SPK%'
    ORDER BY m.parent_id, m.sequence
""")
print("MRP Menu Structure:")
for row in cur.fetchall():
    print(row)
