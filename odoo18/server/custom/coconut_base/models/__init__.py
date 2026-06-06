from odoo import models, fields, api, _
from odoo.exceptions import ValidationError


class CoconutProductTemplate(models.Model):
    """Extended product template for coconut-specific tracking"""
    _name = 'coconut.product.template'
    _description = 'Coconut Product Template'
    _inherit = 'product.template'
    _rec_name = 'name'

    # Coconut-specific fields
    coconut_type = fields.Selection([
        ('raw', 'Raw Coconut'),
        ('husked', 'Husked Coconut'),
        ('desiccated', 'Desiccated Coconut'),
        ('coconut_oil', 'Coconut Oil'),
        ('coconut_milk', 'Coconut Milk'),
        ('copra', 'Copra'),
        ('coconut_water', 'Coconut Water'),
    ], string='Coconut Product Type', required=True, default='raw')

    is_coconut_product = fields.Boolean(string='Is Coconut Product', default=True)
    
    # Conversion factors (for BoM)
    coconut_count_per_unit = fields.Float(string='Coconuts per Unit', 
                                          help='Number of coconuts needed per unit of finished product')
    yield_percentage = fields.Float(string='Yield %', 
                                   help='Expected yield percentage (0-100)',
                                   default=100.0)
    
    # Quality parameters
    quality_grade = fields.Selection([
        ('grade_a', 'Grade A - Premium'),
        ('grade_b', 'Grade B - Standard'),
        ('grade_c', 'Grade C - Economy'),
    ], string='Quality Grade', default='grade_a')
    
    shelf_life_days = fields.Integer(string='Shelf Life (Days)', default=30)
    
    # Weight specifications (grams)
    avg_weight_raw = fields.Float(string='Avg Raw Weight (g)', 
                                 help='Average weight of raw coconut in grams')
    avg_weight_processed = fields.Float(string='Avg Processed Weight (g)',
                                       help='Average weight after processing')
    
    storage_requirements = fields.Selection([
        ('cool_dry', 'Cool & Dry'),
        ('refrigerated', 'Refrigerated (2-8°C)'),
        ('frozen', 'Frozen (-18°C)'),
        ('ambient', 'Ambient Temperature'),
    ], string='Storage Requirements', default='cool_dry')


class CoconutProduct(models.Model):
    """Stockable product coconut variant tracking"""
    _name = 'coconut.product'
    _description = 'Coconut Product Variant'
    _inherit = 'product.product'

    coconut_batch_id = fields.Many2one('coconut.batch', string='Batch Reference')
    coconut_origin = fields.Char(string='Origin (Region/Village)')
    harvest_date = fields.Date(string='Harvest Date')
    received_date = fields.Datetime(string='Received Date', readonly=True)
    
    # Quality inspection
    quality_state = fields.Selection([
        ('pending', 'Pending Inspection'),
        ('approved', 'Approved'),
        ('rejected', 'Rejected'),
        ('quarantine', 'In Quarantine'),
    ], string='Quality Status', default='pending')
    
    # Physical characteristics
    size = fields.Selection([
        ('small', 'Small (300-500g)'),
        ('medium', 'Medium (500-800g)'),
        ('large', 'Large (800-1200g)'),
        ('extra_large', 'Extra Large (>1200g)'),
    ], string='Size Category')
    
    color_score = fields.Integer(string='Color Score (1-10)',
                                 help='Color quality score, 10 being best')
    damage_score = fields.Integer(string='Damage Score (0-10)',
                                  help='0 = no damage, 10 = severe damage')
    
    # Inspector
    inspected_by = fields.Many2one('res.users', string='Inspector')
    inspection_date = fields.Datetime(string='Inspection Date')
    
    notes = fields.Text(string='Inspection Notes')


class CoconutBatch(models.Model):
    """Batch tracking for coconut products"""
    _name = 'coconut.batch'
    _description = 'Coconut Batch / Lot Tracking'
    _inherit = 'stock.lot'
    _order = 'create_date desc'

    # Enhanced batch tracking
    batch_code = fields.Char(string='Batch Code', required=True, copy=False, 
                           default=lambda self: _('New'))
    supplier_batch_ref = fields.Char(string='Supplier Batch Reference')
    
    # Source information
    supplier_id = fields.Many2one('res.partner', string='Supplier',
                                 domain=[('supplier_rank', '>', 0)])
    purchase_order_id = fields.Many2one('purchase.order', string='Source PO')
    purchase_line_id = fields.Many2one('purchase.order.line', string='PO Line')
    
    # Receiving information
    received_date = fields.Datetime(string='Received Date', readonly=True)
    received_by = fields.Many2one('res.users', string='Received By', readonly=True)
    quantity_received = fields.Float(string='Quantity Received',
                                    digits='Product Unit of Measure')
    
    # Quality inspection tracking
    inspection_required = fields.Boolean(string='Inspection Required', default=True)
    inspection_completed = fields.Boolean(string='Inspection Completed', default=False)
    inspection_id = fields.Many2one('coconut.inspection', string='Inspection Record')
    
    # Current status
    current_location = fields.Char(string='Current Location')
    current_stock = fields.Float(string='Current Stock', compute='_compute_current_stock')
    
    # Production linkage
    consumed_by_production = fields.One2many('mrp.production', 'batch_id', 
                                             string='Used in Productions')
    
    @api.model_create_multi
    def create(self, vals_list):
        for vals in vals_list:
            if vals.get('batch_code', _('New')) == _('New'):
                vals['batch_code'] = self.env['ir.sequence'].next_by_code('coconut.batch') or _('New')
        return super().create(vals_list)
    
    @api.depends('product_qty')
    def _compute_current_stock(self):
        for batch in self:
            # Get all stock quants for this batch
            quants = self.env['stock.quant'].search([
                ('lot_id', '=', batch.id),
                ('location_id.usage', 'in', ['internal', 'transit'])
            ])
            batch.current_stock = sum(quants.mapped('quantity'))


class CoconutInspection(models.Model):
    """Quality inspection records for coconut batches"""
    _name = 'coconut.inspection'
    _description = 'Coconut Quality Inspection'
    _order = 'inspection_date desc'

    name = fields.Char(string='Inspection Reference', required=True, 
                      default=lambda self: _('New'), copy=False)
    batch_id = fields.Many2one('coconut.batch', string='Batch', required=True)
    product_id = fields.Many2one('product.product', string='Product',
                                related='batch_id.product_id', store=True)
    
    inspector_id = fields.Many2one('res.users', string='Inspector', 
                                   required=True, default=lambda self: self.env.user)
    inspection_date = fields.Datetime(string='Inspection Date', 
                                     default=fields.Datetime.now, required=True)
    
    # Quality parameters
    overall_quality = fields.Selection([
        ('excellent', 'Excellent'),
        ('good', 'Good'),
        ('acceptable', 'Acceptable'),
        ('poor', 'Poor'),
        ('rejected', 'Rejected'),
    ], string='Overall Quality', required=True)
    
    # Physical checks
    visual_score = fields.Integer(string='Visual Score (1-10)')
    odor_score = fields.Integer(string='Odor Score (1-10)')
    moisture_content = fields.Float(string='Moisture Content (%)')
    oil_content = fields.Float(string='Oil Content (%)')
    
    # Defect tracking
    defects = fields.Text(string='Defects Found')
    
    # Decision
    approved = fields.Boolean(string='Approved', default=False)
    approved_qty = fields.Float(string='Approved Quantity')
    rejected_qty = fields.Float(string='Rejected Quantity')
    
    notes = fields.Text(string='Inspection Notes')
    
    @api.model_create_multi
    def create(self, vals_list):
        for vals in vals_list:
            if vals.get('name', _('New')) == _('New'):
                vals['name'] = self.env['ir.sequence'].next_by_code('coconut.inspection') or _('New')
        records = super().create(vals_list)
        # Update batch status
        for record in records:
            record.batch_id.write({
                'quality_state': 'approved' if record.approved else 'rejected',
                'inspected_by': record.inspector_id.id,
                'inspection_date': record.inspection_date,
                'inspection_completed': True,
            })
        return records
