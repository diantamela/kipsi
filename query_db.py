import psycopg2
try:
    conn = psycopg2.connect("dbname=diansukses user=openpg password=openpgpwd host=localhost")
    cur = conn.cursor()
    cur.execute("select id, name::text, parent_id, action from ir_ui_menu where name::text ilike '%spk%';")
    rows = cur.fetchall()
    for row in rows:
        cur.execute("select module, name from ir_model_data where model='ir.ui.menu' and res_id=%s;", (row[0],))
        xml_id = cur.fetchone()
        print(f"ID: {row[0]}, Name: {row[1]}, Parent: {row[2]}, Action: {row[3]}, XML_ID: {xml_id}")
    conn.close()
except Exception as e:
    print("Error:", e)
