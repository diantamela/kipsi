import sys
import os
sys.path.append(r'c:\odoo\odoo18\server')
import odoo
odoo.tools.config.parse_config(['-c', r'c:\odoo\odoo18\server\odoo.conf'])
registry = odoo.modules.registry.Registry('diansukses')
with registry.cursor() as cr:
    env = odoo.api.Environment(cr, 1, {})
    mod = env['ir.module.module'].search([('name', '=', 'coconut_inventory')])
    if mod:
        print('Installing coconut_inventory...')
        mod.button_immediate_install()
    else:
        print('Module not found.')
