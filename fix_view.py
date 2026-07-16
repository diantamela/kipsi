import psycopg2
import json

conn = psycopg2.connect('dbname=diansukses user=openpg host=localhost port=5432 password=openpgpwd')
cur=conn.cursor()

# Get the current arch_db
cur.execute('''SELECT arch_db::text FROM ir_ui_view WHERE key = 'coco_theme.coco_login_layout' ''')
arch_db_json = cur.fetchone()[0]
arch_db = json.loads(arch_db_json)

# Replace the logo path
new_xml = arch_db['en_US']
new_xml = new_xml.replace('/coco_theme/static/img/logo.png', '/web_theme_pt_coco/static/src/img/logo.png')

# Add a hidden FontAwesome icon to fix the preload warning
# We will add it right after the image
new_xml = new_xml.replace('alt="PT Coco Murni Prima Jaya" style="max-height: 80px; margin-bottom: 1rem;"/>',
                           'alt="PT Coco Murni Prima Jaya" style="max-height: 80px; margin-bottom: 1rem;"/>\n                            <i class="fa fa-database d-none"></i>')

arch_db['en_US'] = new_xml

# Update the view
cur.execute('''UPDATE ir_ui_view SET arch_db = %s WHERE key = 'coco_theme.coco_login_layout' ''', (json.dumps(arch_db),))
conn.commit()

print("View updated successfully.")
