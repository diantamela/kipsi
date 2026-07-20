import sys
import os
sys.path.append(r'c:\odoo\odoo18\server')
import odoo
odoo.tools.config.parse_config(['-c', r'c:\odoo\odoo18\server\odoo.conf'])
odoo.cli.server.report_configuration()
registry = odoo.modules.registry.Registry('diantamela_kipsi')
with registry.cursor() as cr:
    env = odoo.api.Environment(cr, 1, {})
    menu = env.ref('stock.menu_product_variant_config_stock')
    action = env.ref('stock.product_template_action_product')
    print('Current menu action:', menu.action.name, menu.action.id)
    if menu.action.id != action.id:
        print('Updating menu action to:', action.name, action.id)
        menu.action = action
    else:
        print('Menu action is already correct in database.')
