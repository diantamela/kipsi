# Coconut Factory ERP - Post-Installation Configuration

## Quick Setup Script

Run this in Odoo shell to verify installation: `python odoo-bin shell -c odoo.conf`

```python
# Verify all models are loaded
models_to_check = [
    'coconut.product.template',
    'coconut.batch',
    'coconut.inspection',
    'coconut.supplier',
    'coconut.purchase.requisition',
    'coconut.stock.alert',
    'coconut.production.order',
    'coconut.work.order',
    'coconut.dashboard',
]

for model in models_to_check:
    try:
        env[model].search([], limit=1)
        print(f"✓ {model} loaded successfully")
    except Exception as e:
        print(f"✗ {model} error: {e}")

# Check sequences
sequences = env['ir.sequence'].search([('code', 'like', 'coconut')])
print(f"\nSequences created: {len(sequences)}")
for seq in sequences:
    print(f"  - {seq.code}: {seq.prefix}{'0'*seq.padding}")

# Create factory config if not exists
config = env['coconut.factory.config'].search([], limit=1)
if not config:
    config = env['coconut.factory.config'].create({
        'name': 'Default Config',
        'company_id': env.company.id,
    })
    print(f"Factory config created: {config.name}")

print("\n✓ System verification complete!")
```

---

## Configure Cron Jobs

The notification module includes a cron job for stock monitoring. Ensure it's active:

```python
cron = env['ir.cron'].search([('name', 'ilike', 'Coconut Stock')], limit=1)
if cron:
    cron.write({'active': True})
    print("✓ Stock monitor cron job activated")
```

---

## Database Schema Verification

Run this to verify all tables created:

```sql
SELECT tablename FROM pg_tables WHERE tablename LIKE 'coconut_%';
```

Expected tables:
- coconut_product_template
- coconut_product
- coconut_batch
- coconut_inspection
- coconut_supplier
- coconut_supplier_performance
- coconut_supplier_history
- coconut_purchase_requisition
- coconut_stock_alert
- coconut_production_order
- coconut_material_requirement
- coconut_work_order
- coconut_dashboard

---

## Sample Data Creation

If you need demo data for testing, run:

```python
# Create sample supplier
supplier = env['coconut.supplier'].create({
    'name': 'Demo Coconut Farm',
    'coconut_supplier_type': 'farmer',
    'province': 'Central Java',
    'quality_grade': 'premium',
    'total_deliveries': 0,
    'annual_capacity': 5000,
})

# Create sample product (if base not installed)
if not env['product.product'].search([('name', '=', 'Raw Coconut')]):
    env['product.template'].create({
        'name': 'Raw Coconut',
        'coconut_type': 'raw',
        'is_coconut_product': True,
        'list_price': 2.5,
        'standard_price': 1.5,
        'type': 'product',
        'uom_id': env.ref('uom.product_uom_kg').id,
    })

print("✓ Sample data created")
```

---

## Odoo Configuration Update

**Important:** Update `odoo.conf` to include custom modules path:

```ini
[options]
addons_path = c:\odoo\odoo18\server\odoo\addons,c:\odoo\odoo18\server\custom
```

After updating, restart Odoo service.

---

## Accessing the System

After installation:

1. Login as Admin
2. Main menu: **Coconut Factory ERP**
3. Dashboard shows real-time metrics

**User Roles to Configure:**

- **Purchase Manager**: Access to Requisitions, Suppliers
- **Stock Manager**: Access to Inventory, Batches, Alerts
- **Production Manager**: Access to Production Orders, Work Orders
- **Quality Manager**: Access to Inspections

Set via: Settings → Users & Companies → Users → Access Rights

---

## Daily Operations Checklist

### Morning
- [ ] Review dashboard for low stock alerts
- [ ] Check pending requisitions
- [ ] Review yesterday's production efficiency

### Receiving
- [ ] Receive POs
- [ ] Create batch records
- [ ] Schedule inspections
- [ ] Move to storage after approval

### Production Planning
- [ ] Review material requirements
- [ ] Reserve batches from storage
- [ ] Schedule work orders
- [ ] Assign operators

### End of Day
- [ ] Complete work orders
- [ ] Log actual production
- [ ] Record rejected quantities
- [ ] Generate daily summary

---

## Maintenance Tasks

### Weekly
- Review supplier performance scores
- Analyze production efficiency trends
- Check alert fatigue (too many notifications?)
- Validate batch traceability completeness

### Monthly
- Run inventory valuation report
- Generate production yield analysis
- Review purchase price variance
- Update minimum stock levels based on consumption

### Quarterly
- Supplier grade reassessment
- BoM validation against actual yields
- Quality approval rate analysis
- Staff productivity analysis

---

## API Endpoints (for external integrations)

Custom models are accessible via Odoo's XML-RPC/JSON-RPC:

```python
# Example: Check stock levels
models.execute_kw('coconut.batch', 'search_read',
                  [[['current_stock', '>', 0]]],
                  {'fields': ['batch_code', 'product_id', 'current_stock']})

# Example: Create production order
models.execute_kw('coconut.production.order', 'create', [{
    'product_id': product_id,
    'planned_qty': 1000,
    'workcenter_id': workcenter_id,
}])
```

---

## Backup & Restore

**Always backup before major changes:**

```bash
# Backup
pg_dump -U openpg -d <database_name> > coconut_erp_backup_$(date +%Y%m%d).sql

# Restore
psql -U openpg -d <database_name> < backup_file.sql
```

---

## Next Steps

1. Configure warehouse locations
2. Set stock minimum thresholds
3. Create initial supplier records
4. Set up email templates in Odoo
5. Train users on new workflows

---

**For research documentation**, capture:
- Screenshots of integration points
- Before/after metrics
- User adoption challenges
- Performance improvements
