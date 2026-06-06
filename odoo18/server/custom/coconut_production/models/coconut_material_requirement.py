from odoo import models, fields, api


class MrpBomExtension(models.Model):
    """Extend BoM for coconut products with yield tracking"""
    _name = 'coconut.bom'
    _description = 'Coconut Bill of Materials Extension'
    _inherit = 'mrp.bom'

    # Coconut-specific BoM data
    coconut_processed_per_unit = fields.Float(string='Coconuts per Unit', 
                                              related='product_tmpl_id.coconut_count_per_unit',
                                              readonly=True)
    expected_yield_percentage = fields.Float(string='Expected Yield %', 
                                             related='product_tmpl_id.yield_percentage',
                                             readonly=True)
    
    # Processing loss tracking
    processing_loss_percentage = fields.Float(string='Processing Loss %', default=10.0,
                                             help='Expected loss during processing')
    copra_ratio = fields.Float(string='Copra Ratio', 
                              help='Copra output per coconut (if applicable)')
    oil_extraction_rate = fields.Float(string='Oil Extraction Rate %', 
                                       help='Oil extraction percentage')
    
    # Quality requirements for input materials
    min_coconut_quality = fields.Selection([
        ('grade_a', 'Grade A'),
        ('grade_b', 'Grade B'),
        ('grade_c', 'Grade C'),
    ], string='Minimum Coconut Quality', default='grade_b')
    max_moisture_allowed = fields.Float(string='Max Moisture %', default=6.0)
    
    notes = fields.Text(string='BoM Notes')


class MrpProductionExtension(models.Model):
    """Extend mrp.production to link with coconut batch"""
    _name = 'coconut.production.batch'
    _description = 'Coconut Production Batch Link'
    _inherit = 'mrp.production'

    batch_id = fields.Many2one('coconut.batch', string='Coconut Batch Reference',
                              help='Primary coconut batch used for this production')
    batch_ids = fields.Many2many('coconut.batch', string='All Coconut Batches Used',
                                compute='_compute_batches', store=True)
    coconut_type = fields.Selection(related='product_id.coconut_type', store=True)
    
    @api.depends('move_raw_ids', 'move_raw_ids.batch_ids')
    def _compute_batches(self):
        for production in self:
            batches = production.move_raw_ids.mapped('batch_ids')
            production.batch_ids = [(6, 0, batches.ids)]
