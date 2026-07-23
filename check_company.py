import psycopg2
conn = psycopg2.connect('dbname=diansukses user=openpg host=localhost port=5432 password=openpgpwd')
cur = conn.cursor()

# Search for recently created attachments of image type
cur.execute("SELECT id, name, mimetype, res_model, res_id, create_date FROM ir_attachment WHERE mimetype IN ('image/png', 'image/jpeg', 'image/jpg') ORDER BY create_date DESC LIMIT 10")
print("Image Attachments:")
for row in cur.fetchall():
    print(row)

# Let's check res_company logo or logo_web size/presence
cur.execute("SELECT id, name, uses_default_logo, logo_web IS NOT NULL, OCTET_LENGTH(logo_web) FROM res_company")
print("Company Logos:")
for row in cur.fetchall():
    print(row)

# Let's check res_partner logo
cur.execute("SELECT id, name, image_1920 IS NOT NULL, OCTET_LENGTH(image_1920) FROM res_partner WHERE id = 1")
print("Company Partner Logo:")
print(cur.fetchone())
