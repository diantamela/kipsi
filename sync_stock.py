def sync_existing(env):
    try:
        receipts = env['coconut.receipt'].search([('state', '=', 'done')])
        count = 0
        for receipt in receipts:
            env['coconut.daily.stock']._sync_from_receipt(receipt)
            count += 1
        env.cr.commit()
        print(f"Successfully synced {count} receipts to Daily Stock.")
    except Exception as e:
        print(f"Error: {e}")
        env.cr.rollback()

if __name__ == '__main__':
    # This script is meant to be run via odoo-bin shell:
    # python odoo-bin shell -c odoo.conf -d <your_database> < c:\odoo\sync_stock.py
    shell_env = locals().get('env')
    if shell_env:
        sync_existing(shell_env)
