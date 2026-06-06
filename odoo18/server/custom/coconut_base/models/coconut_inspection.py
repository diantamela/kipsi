from odoo import models, fields, api, _
from odoo.exceptions import ValidationError


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
