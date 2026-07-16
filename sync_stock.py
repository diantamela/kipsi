import xmlrpc.client
import sys

def sync_existing():
    try:
        from odoo import api, SUPERUSER_ID
        env = api.Environment(env.cr, SUPERUSER_ID, {})
        receipts = env['coconut.receipt'].search([('state', '=', 'done')])
        count = 0
        for receipt in receipts:
            env['coconut.daily.stock']._sync_from_receipt(receipt)
            count += 1
        env.cr.commit()
        print(f"Successfully synced {count} receipts to Daily Stock.")
    except Exception as e:
        print(f"Error: {e}")

if __name__ == '__main__':
    sync_existing()
