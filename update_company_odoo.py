import base64

def run_update(env):
    try:
        # Load the logo image
        logo_path = r"C:\Users\Lenovo\.gemini\antigravity-ide\brain\3201d54d-43ea-4579-a1e2-b087654169d0\media__1784711271282.png"
        with open(logo_path, 'rb') as f:
            logo_data = base64.b64encode(f.read())
            
        company = env['res.company'].browse(1)
        company.write({
            'name': 'PT Coco Murni Prima Jaya',
            'logo': logo_data,
        })
        
        # Update partner address info
        partner = company.partner_id
        partner.write({
            'name': 'PT Coco Murni Prima Jaya',
            'street': 'V983+26X Jalan Raya Batang Serangan',
            'street2': 'Lingkungan I Bukit Tua, Kel. Tanjung Selamat',
            'city': 'Kec. Padang Tualang',
            'zip': '20852',
            'state_id': 649, # Sumatra Utara
            'country_id': 100, # Indonesia
        })
        
        env.cr.commit()
        print("Company data updated successfully in Odoo!")
    except Exception as e:
        env.cr.rollback()
        print(f"Error updating company data: {e}")

if __name__ == '__main__':
    shell_env = locals().get('env')
    if shell_env:
        run_update(shell_env)
