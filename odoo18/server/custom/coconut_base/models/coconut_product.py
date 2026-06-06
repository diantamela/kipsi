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
