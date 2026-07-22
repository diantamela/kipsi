import os
for root, dirs, files in os.walk("c:\\odoo"):
    for d in dirs:
        if d in ['coconut_receiving', 'coconut_payroll']:
            print(f"Found module {d} in: {os.path.join(root, d)}")


