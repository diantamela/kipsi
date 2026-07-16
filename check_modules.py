import psycopg2
conn = psycopg2.connect('dbname=diansukses user=openpg host=localhost port=5432 password=openpgpwd')
cur=conn.cursor()
cur.execute('''
    WITH RECURSIVE menu_tree AS (
        SELECT id, name, parent_id, 1 AS depth
        FROM ir_ui_menu
        WHERE id = (SELECT res_id FROM ir_model_data WHERE model = 'ir.ui.menu' AND module = 'purchase' AND name = 'menu_purchase_root')
        UNION ALL
        SELECT m.id, m.name, m.parent_id, t.depth + 1
        FROM ir_ui_menu m
        JOIN menu_tree t ON m.parent_id = t.id
    )
    SELECT t.id, t.name, t.depth, d.module, d.name
    FROM menu_tree t
    LEFT JOIN ir_model_data d ON d.res_id = t.id AND d.model = 'ir.ui.menu'
    ORDER BY t.depth, t.id
''')
results = cur.fetchall()
for row in results:
    print(row)
