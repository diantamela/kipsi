# Coconut Factory ERP - Research Integration Document

## Research Focus: Module Integration for Coconut Processing ERP

### Core Research Question Addressed

**How can ERP module integration improve operational efficiency in coconut processing factories?**

This implementation demonstrates data flow across:
1. **Purchasing** → 2. **Inventory** → 3. **Manufacturing** → 4. **HR/Payroll** → 5. **Reporting**

---

## Integration Architecture (Thesis Core)

### Data Flow Diagram

```
┌─────────────────┐
│  coconut_supplier │  (Supplier data, performance scores)
└────────┬────────┘
         │ partner_id, quality grade
         ▼
┌─────────────────┐
│ coconut_purchase │  (Requisition → PO) 
│  - requisition   │    PO links to supplier
│  - approval      │    PO creates stock moves
└────────┬────────┘
         │ purchase_order_id
         ▼
┌─────────────────┐
│ coconut_inventory │ (Batch creation, stock tracking)
│  - batch records   │    Batches linked to PO
│  - stock alerts    │    Stock consumed by MRP
└────────┬────────┘
         │ batch_ids, stock_qty
         ▼
┌─────────────────┐
│ coconut_production│ (Production orders)
│  - bom usage       │    Consumes batches
│  - work orders     │    Tracks labor
│  - yield analysis  │    Updates stock (finished goods)
└────────┬────────┘
         │ work_order.employee_ids
         ▼
┌─────────────────┐
│ coconut_notification │ (Alerts based on all data)
└────────┬────────┘
         │
         └──────────────┐
                        ▼
             ┌─────────────────┐
             │ coconut_dashboard │  (Aggregated metrics)
             │  - Real-time KPI   │
             └──────────────────┘
```

---

## Key Integration Points (Research Value)

### 1. Supplier → Purchase → Inventory Integration

**Problem addressed:** How does supplier quality affect downstream inventory?

**Implementation:**
- coconut.supplier linked to res.partner
- PO auto-suggests suppliers based on performance scores
- Receipt creates coconut.batch with supplier reference
- Quality inspection updates supplier performance record

**Research metric:** Supplier score vs batch rejection rate

```python
# In coconut_inventory/models/stock_models.py
batch_id.supplier_id.avg_quality_score  # Updated on each inspection
```

**Benefit:** Factory can identify which suppliers consistently deliver quality coconuts and adjust ordering.

---

### 2. Purchase → Inventory → Production Planning

**Problem addressed:** How to ensure raw material availability before production scheduling?

**Implementation:**
- coconut.material.requirement computes from BoM
- Production order validates batch availability
- System prevents order start if insufficient stock
- Buffer stock maintained in production_buffer location

**Research metric:** Production delay rate due to material shortage

```python
# In coconut_production/models/coconut_production.py
if not self.batch_ids:
    raise UserError(_('Must assign coconut batches before starting production.'))
```

**Benefit:** Eliminates production stoppages from missing raw materials.

---

### 3. Production → HR/Payroll Integration

**Problem addressed:** How to link production output with labor costs?

**Implementation:**
- coconut.work.order tracks employee hours
- Labor hours pushed to hr.timesheet
- Payroll module can read labor costs per production order
- Work center cost rates + employee hours = true production cost

**Research metric:** Labor cost per kg produced

```python
# In coconut_integration/models/coconut_integration.py
def sync_work_hours_to_payroll(self, date_from, date_to):
    """Sync work hours to payroll for payroll calculation"""
    # Links production efficiency to payroll expenses
```

**Benefit:** Accurate cost accounting by product line.

---

### 4. Batch Traceability Across All Modules

**Problem addressed:** How to track a specific batch of coconuts from purchase to final product?

**Implementation:**
- coconut.batch has unique batch_code
- Linked to: purchase_order, quality_inspection, stock_moves, production_orders
- Full traceability query possible

**Research metric:** Time to trace batch from receipt to finished goods

```python
# SQL example for traceability
SELECT 
    b.batch_code,
    po.name as po_number,
    insp.overall_quality,
    mo.name as production_order,
    mo.state as prod_status
FROM coconut_batch b
LEFT JOIN purchase_order po ON b.purchase_order_id = po.id
LEFT JOIN coconut_inspection insp ON b.inspection_id = insp.id
LEFT JOIN mrp_production mo ON b.consumed_by_production = mo.id
WHERE b.batch_code = 'BATCH001234'
```

**Benefit:** 
- Quality issue root cause analysis
- Supplier accountability
- Regulatory compliance (food safety traceability)

---

### 5. Real-time Dashboard Integration

**Problem addressed:** How to provide management visibility across all operations?

**Implementation:**
- coconut.dashboard aggregates data from 5 modules
- Real-time KPI from live database
- One-click access to underlying transactions

**Research metric:** Decision latency reduction

**Dashboard metrics:**
1. Total stock (coconut_inventory)
2. Weekly production (coconut_production)
3. Approval rate (coconut_inspection)
4. Supplier score (coconut_supplier)
5. Pending requisitions (coconut_purchase)

**Benefit:** Single pane of glass for factory management.

---

## Research Hypotheses Tested

### H1: Automated purchase requisition reduces procurement cycle time
**Method:** Compare requisition approval time before vs after system
**Data:** `coconut.purchase.requisition` create_date → approved_date

### H2: Batch tracking improves quality issue resolution time
**Method:** Time to identify problematic batch when quality issue occurs
**Data:** Investigation completion time from defect report to batch identification

### H3: Integrated production planning increases yield percentage
**Method:** Yield comparison before vs after integrated BoM + batch tracking
**Data:** `coconut.production.order` yield_rate field

### H4: Supplier performance scores predict batch quality
**Method:** Correlation between supplier score and inspection approval rate
**Data:** `coconut.supplier.avg_quality_score` vs `coconut.inspection.overall_quality`

---

## Database Schema (ER Diagram Context)

### Main Tables Created

**Core Entities:**
- `coconut_product_template` (extends product.template)
- `coconut_batch` (extends stock.lot)
- `coconut_inspection`
- `coconut_supplier` (extends res.partner)
- `coconut_supplier_performance`
- `coconut_purchase_requisition`
- `coconut_stock_alert`
- `coconut_production_order`
- `coconut_material_requirement`
- `coconut_work_order`
- `coconut_production_report` (materialized view)

**Integration Foreign Keys:**
```
coconut_batch.supplier_id → res.partner
coconut_batch.purchase_order_id → purchase.order
coconut_inspection.batch_id → coconut.batch
coconut_purchase_requisition.product_id → product.product
coconut_stock_alert.product_id → product.product
coconut_production_order.batch_ids → coconut.batch
coconut_production_order.production_id → mrp.production
coconut_work_order.production_order_id → coconut.production.order
coconut_work_order.employee_ids → hr.employee
```

---

## Configuration Parameters (For Research Setup)

### System Parameters Set

```python
# Stock monitoring interval
ir.config_parameter.set_param('coconut.stock.check_interval_hours', '1')

# Default minimum stock (days of inventory * avg daily consumption)
ir.config_parameter.set_param('coconut.default.min.stock.days', '3')

# Quality rejection threshold
ir.config_parameter.set_param('coconut.quality.rejection.threshold', '10.0')

# Auto-inspection toggle
ir.config_parameter.set_param('coconut.auto.inspection', 'True')
```

---

## Sample Queries for Thesis Analysis

### Query 1: End-to-End Batch Traceability
```sql
SELECT 
    b.batch_code,
    s.name as supplier,
    b.quantity_received,
    insp.overall_quality,
    COUNT(DISTINCT po.id) as productions_used_in,
    SUM(po.actual_qty) as total_output,
    b.current_stock
FROM coconut_batch b
JOIN res_partner s ON b.supplier_id = s.id
LEFT JOIN coconut_inspection insp ON b.inspection_id = insp.id
LEFT JOIN coconut_production_order po ON b.id = ANY(po.batch_ids)
WHERE b.create_date > '2025-01-01'
GROUP BY b.id, s.name, insp.overall_quality
ORDER BY b.create_date DESC;
```

### Query 2: Supplier Performance vs Quality Correlation
```sql
SELECT 
    s.quality_grade,
    s.avg_quality_score,
    COUNT(b.id) as batches_received,
    COUNT(insp.id) as inspections_done,
    COUNT(CASE WHEN insp.approved THEN 1 END) as approved_batches,
    ROUND(AVG(insp.overall_quality::numeric), 2) as avg_inspection_score
FROM coconut_supplier s
LEFT JOIN coconut_batch b ON s.id = b.supplier_id
LEFT JOIN coconut_inspection insp ON b.id = insp.batch_id
GROUP BY s.id, s.quality_grade, s.avg_quality_score
ORDER BY s.avg_quality_score DESC;
```

### Query 3: Production Yield Analysis
```sql
SELECT 
    p.product_id,
    p.product_tmpl_id,
    p.planned_qty,
    p.actual_qty,
    p.rejected_qty,
    p.yield_rate,
    p.efficiency,
    bo.processing_loss_percentage,
    (p.yield_rate - bo.processing_loss_percentage) as yield_variance
FROM coconut_production_order p
JOIN coconut_batch b ON b.id = ANY(p.batch_ids)
JOIN mrp_bom bo ON p.bom_id = bo.id
WHERE p.state = 'done'
ORDER BY yield_variance DESC;
```

---

## Academic Value Proposition

### 1. **Integration Depth**
Unlike off-the-shelf Odoo, this implementation shows:
- Cross-module data consistency
- Custom field propagation (supplier quality → production planning)
- Automated decision-making (supplier suggestion)

### 2. **Industry-Specific Customization**
Coconut processing requires:
- Batch-level traceability (not typical in generic ERP)
- Quality grading by size/color
- Conversion factors (coconuts → desiccated)
- Storage temperature control

### 3. **Real-Time Alerting**
Immediate notifications when:
- Stock drops below minimum
- Quality inspection fails
- Production efficiency drops
- Supplier delivery delayed

### 4. **Comprehensive Audit Trail**
Every coconut batch tracked from:
Farm → Supplier → Receipt → Quality → Storage → Production → Output

This full traceability is critical for:
- Food safety recalls
- Quality certification (HACCP, ISO 22000)
- Supplier accountability contracts

---

## Installation Verification Checklist

**For thesis defense demo:**

- [ ] Odoo running on port 8069
- [ ] All 8 modules installed
- [ ] Sample data loaded (coconut products, work centers, locations)
- [ ] Stock levels showing in dashboard
- [ ] Can create purchase requisition → approve → PO generated
- [ ] Can receive PO → batch created → quality inspection completed
- [ ] Can create production order → link batches → record work order
- [ ] Dashboard graphs populate with data
- [ ] Low stock alert triggered manually

---

## Data Collection for Research

### Metrics to Capture During Test Period

| Metric | Source Model | Measurement |
|--------|--------------|-------------|
| Requisition approval time | coconut.purchase.requisition | createdate → approvedate |
| Batch inspection time | coconut.inspection | received_date → inspection_date |
| Production yield | coconut.production.order | (actual+rejected)/consumed × 100 |
| Supplier batch quality | coconut.supplier.performance | avg_quality_score |
| Stock turnover rate | stock.quant | avg inventory / COGS |
| Alert response time | coconut.notification.queue | create_date → sent_date |

### Data Export Commands

```python
# Export all traces for analysis
import csv

# Batch traceability export
with open('batch_traceability.csv', 'w', newline='') as f:
    writer = csv.writer(f)
    writer.writerow(['Batch', 'Supplier', 'Received', 'Quality', 'Production', 'CurrentStock'])
    for batch in env['coconut.batch'].search([]):
        writer.writerow([
            batch.batch_code,
            batch.supplier_id.name,
            batch.received_date,
            batch.quality_state,
            ', '.join(batch.consumed_by_production.mapped('name')),
            batch.current_stock
        ])
```

---

## Thesis Chapter Mapping

**Chapter 1 - Introduction:** Coconut industry problems (inefficiency, lack of traceability)

**Chapter 2 - Literature Review:** ERP in food processing, batch tracking systems

**Chapter 3 - Methodology:** This implementation (custom Odoo modules)

**Chapter 4 - System Design:** Architecture diagrams, module descriptions

**Chapter 5 - Implementation:** Code walkthrough, integration points

**Chapter 6 - Results & Analysis:** Data collected from test runs

**Chapter 7 - Conclusion:** Research contributions, future work

---

## Future Enhancements (For Future Research)

1. **Mobile App** for field data entry (supplier registration, delivery notes)
2. **IoT Sensors** for temperature monitoring in storage
3. **Computer Vision** for automatic coconut quality grading
4. **Predictive Analytics** for yield forecasting
5. **Blockchain** for immutable batch records (food safety certification)
6. **Mobile RFID/Barcode scanning** for faster inventory operations

---

## Contact

For questions about implementation:
- Review module code in `custom/` directory
- Odoo documentation: https://www.odoo.com/documentation/18.0/
- Community forums: https://www.odoo.com/forum/

---

**Document Version:** 1.0  
**Odoo Version:** 18.0  
**Implementation Date:** 2026-05-09
