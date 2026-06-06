from odoo import models, fields, api, _
from odoo.exceptions import ValidationError, UserError


class CoconutStockAlert(models.Model):
    """Stock level monitoring and alerts"""
    _name = 'coconut.stock.alert'
    _description = 'Coconut Stock Alert'
    _order = 'create_date desc'

    name = fields.Char(string='Alert Reference', readonly=True, default='New')
    product_id = fields.Many2one('product.product', string='Product', required=True,
                                domain="[('coconut_product_ids', '!=', False)]")
    location_id = fields.Many2one('stock.location', string='Location', required=True)
    
    # Thresholds
    minimum_stock = fields.Float(string='Minimum Stock (kg)', required=True)
    maximum_stock = fields.Float(string='Maximum Stock (kg)', required=True)
    current_stock = fields.Float(string='Current Stock (kg)', compute='_compute_current_stock')
    
    # Alert status
    alert_type = fields.Selection([
        ('low', 'Low Stock'),
        ('high', 'Over Stock'),
        ('normal', 'Normal'),
    ], string='Alert Type', compute='_compute_alert_type', store=True)
    
    is_active = fields.Boolean(string='Active', default=True)
    last_alert_date = fields.Datetime(string='Last Alert Sent')
    alert_count = fields.Integer(string='Alert Count', default=0)
    
    # Notification settings
    notify_users = fields.Many2many('res.users', string='Notify Users')
    notification_frequency = fields.Selection([
        ('immediate', 'Immediate'),
        ('daily', 'Daily Summary'),
        ('weekly', 'Weekly Summary'),
    ], string='Notification Frequency', default='immediate')
    
    notes = fields.Text(string='Notes')

    @api.depends('product_id', 'location_id')
    def _compute_current_stock(self):
        for alert in self:
            quants = self.env['stock.quant'].search([
                ('product_id', '=', alert.product_id.id),
                ('location_id', '=', alert.location_id.id),
            ])
            alert.current_stock = sum(quants.mapped('quantity'))
    
    @api.depends('current_stock', 'minimum_stock', 'maximum_stock')
    def _compute_alert_type(self):
        for alert in self:
            if alert.current_stock <= alert.minimum_stock:
                alert.alert_type = 'low'
            elif alert.current_stock >= alert.maximum_stock:
                alert.alert_type = 'high'
            else:
                alert.alert_type = 'normal'

    def action_send_alert(self):
        """Send stock alert notification"""
        self.ensure_one()
        if self.alert_type != 'normal':
            # Send email notification
            template = self.env.ref('coconut_notification.email_template_stock_alert')
            if template:
                template.send_mail(self.id, force_send=True)
            
            self.write({
                'last_alert_date': fields.Datetime.now(),
                'alert_count': self.alert_count + 1,
            })
            
            # Create activity for assigned users
            for user in self.notify_users:
                self.env['mail.activity'].create({
                    'activity_type_id': self.env.ref('mail.mail_activity_data_todo').id,
                    'note': f'Stock alert: {self.product_id.name} is {self.alert_type} at {self.location_id.name}',
                    'res_id': self.id,
                    'res_model_id': self.env['ir.model'].search([('model', '=', 'coconut.stock.alert')]).id,
                    'user_id': user.id,
                })


class CoconutInventoryLine(models.Model):
    """Extended inventory line with coconut-specific tracking"""
    _name = 'coconut.inventory.line'
    _description = 'Coconut Inventory Line'
    _inherit = 'stock.valuation.layer'

    batch_id = fields.Many2one('coconut.batch', string='Batch Reference')
    coconut_type = fields.Selection(related='product_id.coconut_type', store=True)
    quality_grade = fields.Selection(related='product_id.quality_grade', store=True)
    source_location = fields.Many2one('stock.location', string='Source Location')
    destination_location = fields.Many2one('stock.location', string='Destination Location')


class StockMoveExtended(models.Model):
    """Extend stock moves for coconut tracking"""
    _name = 'coconut.stock.move'
    _description = 'Extended Stock Move for Coconut Tracking'
    _inherit = 'stock.move'

    batch_ids = fields.Many2many('coconut.batch', string='Coconut Batches')
    coconut_type = fields.Selection(related='product_id.coconut_type', store=True)
    quality_grade = fields.Selection(related='product_id.quality_grade', store=True)


class StockPickingExtended(models.Model):
    """Extend stock picking for coconut operations"""
    _name = 'coconut.stock.picking'
    _description = 'Extended Stock Picking for Coconut Processing'
    _inherit = 'stock.picking'

    picking_type_coconut = fields.Selection([
        ('receipt', 'Raw Material Receipt'),
        ('issue_to_production', 'Issue to Production'),
        ('finished_goods', 'Finished Goods Receipt'),
        (' scrap', 'Scrap/Reject'),
        ('transfer', 'Internal Transfer'),
    ], string='Coconut Operation Type')
    
    batch_ids = fields.Many2many('coconut.batch', string='Coconut Batches')
    inspection_required = fields.Boolean(string='Inspection Required', default=False)
    inspection_completed = fields.Boolean(string='Inspection Completed', default=False)
    
    # Quality check
    quality_check_ids = fields.One2many('coconut.quality.check', 'picking_id', string='Quality Checks')
    quality_score = fields.Float(string='Quality Score', digits=(5,2))
    
    # Supplier reference
    supplier_certificate_number = fields.Char(string='Supplier Certificate No.')
    supplier_batch_reference = fields.Char(string='Supplier Batch Ref')


class CoconutQualityCheck(models.Model):
    """Quality checks during stock operations"""
    _name = 'coconut.quality.check'
    _description = 'Coconut Quality Check'

    picking_id = fields.Many2one('stock.picking', string='Picking')
    batch_id = fields.Many2one('coconut.batch', string='Batch')
    checker_id = fields.Many2one('res.users', string='Checked By', 
                                default=lambda self: self.env.user)
    check_date = fields.Datetime(string='Check Date', default=fields.Datetime.now)
    
    # Checks
    moisture_check = fields.Float(string='Moisture %')
    oil_check = fields.Float(string='Oil Content %')
    foreign_matter = fields.Float(string='Foreign Matter %')
    broken_ratio = fields.Float(string='Broken/Damaged %')
    
    # Overall
    passed = fields.Boolean(string='Passed', default=False)
    notes = fields.Text(string='Notes')


class StockLocationExtended(models.Model):
    """Extended location for coconut-specific zones"""
    _name = 'coconut.stock.location'
    _description = 'Coconut Storage Location Extension'
    _inherit = 'stock.location'

    location_type_coconut = fields.Selection([
        ('receiving', 'Receiving Area'),
        ('quarantine', 'Quarantine'),
        ('cold_storage', 'Cold Storage'),
        ('dry_storage', 'Dry Storage'),
        ('production_buffer', 'Production Buffer'),
        ('finished_goods', 'Finished Goods'),
        ('rejected', 'Rejected/Scrap'),
    ], string='Coconut Location Type')
    
    temperature_controlled = fields.Boolean(string='Temperature Controlled', default=False)
    max_capacity = fields.Float(string='Maximum Capacity (kg)')
    current_utilization = fields.Float(string='Current Utilization (kg)', 
                                       compute='_compute_utilization')
    
    @api.depends('name')
    def _compute_utilization(self):
        for loc in self:
            quants = self.env['stock.quant'].search([('location_id', '=', loc.id)])
            loc.current_utilization = sum(quants.mapped('quantity'))
