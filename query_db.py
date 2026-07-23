import psycopg2
conn = psycopg2.connect('dbname=diansukses user=openpg host=localhost port=5432 password=openpgpwd')
cur=conn.cursor()
cur.execute('''
    SELECT e.id, e.name, d.name, e.active, e.payroll_active, e.payroll_job_type
    FROM hr_employee e
    LEFT JOIN hr_department d ON e.department_id = d.id
    WHERE d.name->>'en_US' LIKE '%RMP%' OR d.name->>'id_ID' LIKE '%RMP%'
''')
results = cur.fetchall()
for row in results:
    print(row)



