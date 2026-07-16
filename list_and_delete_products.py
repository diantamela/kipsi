import os
import sys

sys.path.append(r'c:\odoo\odoo18\server')
import odoo
odoo.tools.config.parse_config(['-c', r'c:\odoo\odoo18\server\odoo.conf'])

registry = odoo.registry('diansukses')
with registry.cursor() as cr:
    env = odoo.api.Environment(cr, odoo.SUPERUSER_ID, {})
    
    xml_ids = [
        'coconut_receiving.product_kelapa_bulat',
        'coconut_receiving.product_kelapa_layak',
        'coconut_receiving.product_kelapa_reject',
        'coconut_receiving.product_kelapa_sheller',
        'coconut_receiving.product_kelapa_parer',
    ]
    
    keep_ids = []
    for xml_id in xml_ids:
        try:
            model, res_id = env['ir.model.data']._xmlid_to_res_model_res_id(xml_id)
            if res_id:
                keep_ids.append(res_id)
        except Exception:
            pass
            
    print(f"XML template IDs to keep: {keep_ids}")
    
    all_templates = env['product.template'].search([])
    for t in all_templates:
        if t.id in keep_ids:
            continue
        
        # Check if it's one of the main product names or unused historical ones
        if t.name in ['Kelapa Bulat', 'Kelapa Layak Produksi', 'Kelapa Reject', 'Kelapa Sheller', 'Kelapa Parer', 
                      'Daging Kelapa Hasil Cungkil', 'Daging Kelapa Bersih', 'Kulit Ari Kelapa', 'Tempurung Kelapa',
                      'White Meat (Kelapa Putih)', 'White Meat Berkulit Ari', 'Kelapa Tempurung', 'Kulit Ari']:
            print(f"Processing product template: ID: {t.id} | Name: {t.name}")
            
            # Try unlinking using a savepoint
            try:
                with cr.savepoint():
                    t.unlink()
                    print(f"--> Successfully deleted ID: {t.id}")
            except Exception as e:
                # If deletion fails, archive it
                print(f"--> Could not delete ID {t.id} due to constraints. Archiving instead.")
                try:
                    with cr.savepoint():
                        t.active = False
                        print(f"--> Successfully archived ID: {t.id}")
                except Exception as ae:
                    print(f"--> Failed to archive ID {t.id}: {ae}")
                
    cr.commit()
    print("\n--- PRODUCTS AFTER CLEANUP ---")
    templates = env['product.template'].search([])
    for t in templates:
        print(f"ID: {t.id} | Name: {t.name} | Active: {t.active}")
