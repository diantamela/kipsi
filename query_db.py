import psycopg2
try:
    conn = psycopg2.connect("dbname=diansukses user=openpg password=openpgpwd host=localhost")
    cur = conn.cursor()
    # Query specific menus
    for xml_id in ['mrp.menu_mrp_unbuild', 'coconut_receiving.menu_coconut_hasil_kerja_harian']:
        module, name = xml_id.split('.')
        cur.execute("""
            select m.id, m.name::text, m.active, m.action, m.parent_id 
            from ir_ui_menu m
            join ir_model_data d on d.res_id = m.id and d.model = 'ir.ui.menu'
            where d.module = %s and d.name = %s;
        """, (module, name))
        row = cur.fetchone()
        if row:
            print(f"XML_ID: {xml_id}, ID: {row[0]}, Name: {row[1]}, Active: {row[2]}, Action: {row[3]}, Parent: {row[4]}")
        else:
            print(f"XML_ID: {xml_id} not found")
    conn.close()
except Exception as e:
    print("Error:", e)
