# Coconut Factory ERP - Comprehensive Installation Guide

## System Overview

This custom Odoo 18 ERP system is specifically designed for coconut processing factories. It provides end-to-end integration from raw material procurement through production to delivery, with full batch tracking and quality management.

## Core Modules

### 1. Coconut Base (coconut_base)
**Dependencies:** product, stock, mrp

**Features:**
- Coconut product templates with type classification
- Batch/lot tracking (coconut.batch)
- Quality inspection records (coconut.inspection)
- Coconut-specific attributes (size, quality grade, origin)
- Storage requirements and shelf-life tracking

**Key Models:**
- `coconut.product.template` - Enhanced product template for coconut items
- `coconut.batch` - Batch tracking with supplier linkage
- `coconut.inspection` - Quality inspection records

**Data File:** Loads sample coconut products:
- Raw Coconut
- Desiccated Coconut
- Coconut Oil
- Copra

**Sequences Provided:**
- BATCH/{year}/{seq}
- INSP/{year}/{seq}

---

### 2. Coconut Supplier (coconut_supplier)
**Dependencies:** coconut_base, contacts

**Features:**
- Enhanced supplier profiles (coconut.supplier) extending res.partner
- Supplier performance tracking with KPI scoring (1-10 scale)
- Transaction history and evaluation
- Geographic tracking (village, district, province)
- Farm size and coconut variety tracking
- Certification management (organic, fair trade)

**Key Models:**
- `coconut.supplier` - Extended partner record
- `coconut.supplier.performance` - Performance evaluations
- `coconut.supplier.history` - Transaction logs

**UI Integration:**
- Extends partner form to show coconut supplier info
- Supplier performance dashboard

---

### 3. Coconut Purchase (coconut_purchase)
**Dependencies:** coconut_base, coconut_supplier, purchase, stock

**Features:**
- Purchase requisition workflow (coconut.purchase.requisition)
- Approval process (Draft → Submitted → Approved → PO Created)
- Automatic supplier suggestion based on performance
- Quality grade requirements
- Direct PO generation from approved requisitions

**Key Workflow:**
1. User creates requisition specifying product, quantity, quality
2. System suggests top suppliers based on performance
3. Manager reviews and approves
4. System auto-creates Purchase Order
5. PO linked back to requisition

**Sequences Provided:**
- REQ/{year}/{seq}

---

### 4. Coconut Inventory (coconut_inventory)
**Dependencies:** coconut_base, stock

**Features:**
- Enhanced batch tracking across warehouse
- Stock location types specific to coconut (receiving, quarantine, storage, buffer, finished goods)
- Real-time stock monitoring
- Low stock alerts and warnings
- Quality check integration with stock moves
- Overstock detection

**Key Models:**
- `coconut.stock.alert` - Stock level monitoring thresholds
- `coconut.inventory.line` - Extended tracking
- Stock location extensions for coconut

**Integrated With:**
- Stock Picking - Added batch selection and quality checks
- Stock Quant - Batch tracking by location

---

### 5. Coconut Production (coconut_production)
**Dependencies:** coconut_base, coconut_inventory, mrp

**Features:**
- Coconut-specific production orders (coconut.production.order)
- BoM integration with coconut conversion rates
- Work order management with labor tracking
- Material requirement planning from BoM
- Production efficiency and yield tracking
- Batch consumption tracking

**Key Models:**
- `coconut.production.order` - Main production planning
- `coconut.material.requirement` - Material needs per order
- `coconut.work.order` - Shop floor work tasks

**HR Integration:**
- Labor tracking by employee
- Work hours linked to timesheets (when hr integration enabled)
- Labor cost calculation

**BoM Features:**
- Track coconut count per finished product
- Expected yield percentages
- Processing loss tracking (typically 10-15%)
- Copra ratio and oil extraction rates

---

### 6. Coconut Dashboard (coconut_dashboard)
**Dependencies:** All above modules + web

**Features:**
- Comprehensive KPI dashboard
- Real-time inventory graphs
- Production trend analysis
- Supplier performance charts
- Quality approval rates
- Quick action buttons

**Metrics Tracked:**
- Total stock by location
- Daily/weekly production volumes
- Quality approval rates
- Supplier performance scores
- Pending approvals/requisitions

---

### 7. Coconut Notifications (coconut_notification)
**Dependencies:** coconut_base, coconut_inventory, coconut_purchase, coconut_production, mail

**Features:**
- Low stock alerts (minimum threshold warnings)
- Production delay notifications
- Quality issue alerts
- Automated daily/weekly summaries
- Email notifications with batch processing

**Key Models:**
- `coconut.stock.alert` - Individual product stock monitoring
- `coconut.notification.queue` - Notification batch processing
- `coconut.notification.settings` - Global notification configuration

**Scheduled Jobs:**
- Stock level check (every hour) - Creates alerts when below minimum
- Production monitoring (daily)
- Summary emails (configurable frequency)

---

### 8. Coconut Integration (coconut_integration)
**Dependencies:** ALL coconut modules + hr_payroll (optional)

**Features:**
- Factory-wide configuration (coconut.factory.config)
- Auto-generation of production orders from requisitions
- HR timesheet synchronization from work orders
- Payroll integration (optional)
- Daily summary generation

**Key Integration Points:**
1. Purchase → Inventory (receipt creates batch records)
2. Inventory → Production (stock moves consume batches)
3. Production → HR (work orders log labor hours)
4. HR → Payroll (hours sync to payroll runs)

---

## Data Flow Integration (Research Core)

### Flow 1: Raw Material Procurement
```
Supplier → PO → Receipt → Batch Creation → Quality Inspection → Storage
                                                    ↓
                                           Inventory Update
```

### Flow 2: Production Planning
```
Requisition → Approval → BoM Selection → Production Order
                                      ↓
                               Material Requirements Check
                                      ↓
                               Batch Selection from Stock
```

### Flow 3: Production Execution
```
Production Order → Work Order Assignment → Material Issue → Processing
                                                              ↓
                                                Production Output
                                                              ↓
                                                Quality Check
                                                              ↓
                                                Finished Goods
```

### Flow 4: Labor Tracking
```
Work Order → Employee Assignment → Hours Logged → Timesheet → Payroll
```

### Flow 5: Reporting & Alerts
```
All Modules → Dashboard Aggregation ← Real-time Metrics
                                   ↓
                           Stock Alerts Triggered
                                   ↓
                        Notification Queue → Email
```

---

## Installation Instructions

### 1. Prepare Environment

```bash
cd C:\odoo\odoo18\server
```

### 2. Configure Odoo to Load Custom Modules

Edit `odoo.conf`:

```ini
[options]
addons_path = c:\odoo\odoo18\server\odoo\addons,c:\odoo\odoo18\server\custom
```

Restart Odoo service:
```bash
# On Windows
net stop odoo18
net start odoo18

# Or using Odoo bin
python odoo-bin -c odoo.conf --stop
python odoo-bin -c odoo.conf
```

### 3. Update Module List

1. Open Odoo in browser: http://localhost:8069
2. Login as admin
3. Go to Apps → Update Apps List
4. Click "Update"

### 4. Install Modules (Order Matters)

Install in this sequence:

1. **Coconut Base** (coconut_base)
   - Loads product templates, batch models, inspection
   - Must be installed first

2. **Coconut Supplier** (coconut_supplier)
   - Adds supplier tracking capabilities

3. **Coconut Purchase** (coconut_purchase)
   - Purchase requisition workflow

4. **Coconut Inventory** (coconut_inventory)
   - Stock tracking and batch management

5. **Coconut Production** (coconut_production)
   - BoM and production management

6. **Coconut Notification** (coconut_notification)
   - Alerts and monitoring

7. **Coconut Dashboard** (coconut_dashboard)
   - Reporting and analytics

8. **Coconut Integration** (coconut_integration)
   - Final integration glue

---

## Initial Configuration

### Step 1: Configure Factory Settings

Navigate: **Coconut Factory → Configuration → Factory Settings**

Set up:
- Default work centers (select from list)
- Receiving location → "Coconut Receiving"
- Storage location → "Coconut Storage"
- Buffer location → "Production Buffer"
- Finished goods location → "Coconut Finished Goods"

### Step 2: Configure Notification Settings

Navigate: **Coconut Factory → Configuration → Notification Settings**

- Enable: Low Stock Alerts
- Enable: Production Delay Alerts
- Set notification recipients (Stock Manager, Purchase Manager, Production Manager)
- Choose frequency: Immediate or Daily Summary

### Step 3: Create Supplier Records

Navigate: **Coconut Factory → Purchasing → Suppliers**

For each coconut supplier:
- Mark as "Coconut Supplier"
- Enter geographic location
- Set quality grade
- Enter payment terms

### Step 4: Set Up Warehouse Locations

Verify stock locations created by base module:
- Coconut Receiving
- Coconut Quarantine
- Coconut Storage
- Production Buffer
- Coconut Finished Goods

### Step 5: Configure Stock Alerts

Navigate: **Coconut Factory → Inventory → Stock Alerts**

For each coconut product, set minimum stock thresholds.

---

## Usage Workflows

### Workflow A: Receiving Raw Coconuts

1. Create Purchase Order (standard Odoo PO)
2. Receive goods in **Receiving** location
3. System auto-creates coconut.batch records
4. Quality inspection triggered
5. Approved batches move to **Storage**
6. Stock levels auto-updated

### Workflow B: Creating Production Order

#### Method 1: From Requisition
1. Navigate: **Coconut Factory → Purchasing → Requisitions**
2. Create requisition for product (e.g., Desiccated Coconut 1000kg)
3. Manager approves
4. System creates PO automatically
5. After receipt, production order auto-created

#### Method 2: Direct
1. Navigate: **Coconut Factory → Production → Production Orders**
2. Click Create
3. Select product, quantity, BoM auto-selected
4. Select batches to consume
5. Plan → Start → Finish

### Workflow C: Stock Alerts

System runs hourly:
1. Checks all coconut product stock levels
2. If below minimum → creates alert
3. Email sent to configured recipients
4. Alert shown on dashboard

---

## Key Concepts (For Thesis)

### 1. Batch Traceability
Every coconut batch gets unique ID tracking from:
- Supplier → Receipt → Quality → Storage → Production → Output

This enables:
- Supplier accountability
- Quality issue root cause
- Yield analysis by batch

### 2. Yield Tracking
For each production batch:
- Raw coconut input (kg) tracked
- Finished product output (kg) measured
- Yield % calculated
- Variance from BoM standard tracked

Example: 
- BoM says 3.5 coconuts = 1kg desiccated
- Actual yield variance triggers process review

### 3. Supplier Performance Scorecard
Multi-dimensional evaluation:
- Delivery timeliness (1-10)
- Quality score (1-10)
- Quantity accuracy (1-10)
- Price competitiveness (1-10)
- Service & communication (1-10)

Roll-up: Overall grade (A-F)

### 4. Integration Architecture
```
coconut_base
    ↓ provides
coconut_supplier → coconut_purchase → coconut_inventory
                                         ↓
                                   coconut_production
                                         ↓
                                   coconut_notification
                                   coconut_dashboard
                              coconut_integration (ties all)
```

---

## Custom Reports Available

### 1. Batch Traceability Report
- Shows full history of any batch
- From supplier to current location
- All production usage

### 2. Production Efficiency Report
- Planned vs Actual quantities
- Yield analysis by product
- Efficiency by work center

### 3. Supplier Performance Report
- Historical scores
- Rejection rates
- Delivery performance

### 4. Inventory Valuation Report
- Coconut stock by location
- Age analysis (days in storage)
- Quality grading breakdown

---

## Extending the System

### Adding New Coconut Product

1. Go to **Products** (standard Odoo product form)
2. Check box: "Is Coconut Product"
3. Select "Coconut Product Type"
4. Set:
   - Coconuts per unit (for BoM conversion)
   - Yield percentage
   - Quality grade
   - Minimum stock level
   - Maximum stock level

### Adding New Supplier

1. Create partner with "Supplier" checkmark
2. Navigate to **Coconut → Suppliers**
3. Link partner to coconut.supplier
4. Fill coconut-specific fields

### Creating BoM for New Product

1. Go to **Manufacturing → Products → Bill of Materials**
2. Create new BoM
3. Add raw coconut ingredients
4. System calculates expected yield from product template

---

## Troubleshooting

### Issue: Batch records not created on receipt
**Solution:** Ensure product has "Is Coconut Product" checked

### Issue: Inspection not auto-triggered
**Solution:** Check notification settings → "Auto-inspection required" enabled

### Issue: Production orders cannot start without batches
**Solution:** Must assign coconut batches before starting production

### Issue: Dashboard shows zero values
**Solution:** Install all modules in correct order, refresh cache

---

## Thesis Integration Points

This ERP demonstrates:

1. **Data Integration** (Core Research):
   - Purchase data automatically flows to inventory
   - Inventory data flows to production planning
   - Production labor flows to HR
   - All data aggregated in reporting

2. **Real-time Tracking**:
   - Each coconut batch tracked from farm to final product
   - Inventory levels updated automatically
   - Alerts triggered by threshold breaches

3. **Automated Workflow**:
   - Purchase requisition → PO auto-generation
   - Receipt → batch creation → auto-inspection
   - Production scheduling enabled by stock availability
   - Notifications sent without manual intervention

4. **Decision Support**:
   - Dashboard shows key metrics
   - Supplier scorecards inform sourcing
   - Production efficiency tracked
   - Quality trends identified

---

## Contact & Support

For issues with this custom module set, refer to:
- Odoo documentation: https://www.odoo.com/documentation/18.0/
- Custom module README in each module folder

---

*Last updated: 2026-05-09 | Odoo 18.0 Compatible*
