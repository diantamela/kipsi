from odoo import models, fields, api, _
from odoo.exceptions import ValidationError


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
