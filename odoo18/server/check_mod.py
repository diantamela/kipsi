import sys
import os
sys.path.append(r'c:\odoo\odoo18\server')
import odoo
odoo.tools.config.parse_config(['-c', r'c:\odoo\odoo18\server\odoo.conf'])
registry = odoo.modules.registry.Registry('diansukses')
with registry.cursor() as cr:
    env = odoo.api.Environment(cr, 1, {})
    mod = env['ir.module.module'].search([('name', '=', 'coconut_inventory')])
    print('coconut_inventory module state:', mod.state if mod else 'Not Found')
    view = env.ref('coconut_inventory.product_template_inventory_kanban_view', raise_if_not_found=False)
    print('View state:', view.active if view else 'Not found')
