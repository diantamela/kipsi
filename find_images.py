import psycopg2
conn = psycopg2.connect('dbname=diansukses user=openpg host=localhost port=5432 password=openpgpwd')
cur = conn.cursor()

# Find all images in ir_attachment
cur.execute("SELECT id, name, mimetype, res_model, res_id, OCTET_LENGTH(db_datas) FROM ir_attachment WHERE mimetype LIKE 'image/%' ORDER BY create_date DESC")
print("All Image Attachments:")
for row in cur.fetchall():
    print(row)

# Find all partner images
cur.execute("SELECT id, name, is_company, OCTET_LENGTH(image_1920) FROM res_partner WHERE image_1920 IS NOT NULL")
print("Partner Images:")
for row in cur.fetchall():
    print(row)
