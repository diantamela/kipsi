from odoo import models, fields, api, _
from odoo.exceptions import ValidationError, UserError


class CoconutPurchaseRequisition(models.Model):
    """Purchase Requisition for coconut raw materials"""
    _name = 'coconut.purchase.requisition'
    _description = 'Coconut Purchase Requisition'
    _inherit = ['mail.thread', 'mail.activity.mixin']
    _order = 'create_date desc'

    name = fields.Char(string='Requisition No', required=True, copy=False,
                      default=lambda self: _('New'))
    user_id = fields.Many2one('res.users', string='Requested By', 
                             default=lambda self: self.env.user, readonly=True)
    request_date = fields.Datetime(string='Request Date', 
                                  default=fields.Datetime.now, readonly=True)
    
    # Product & quantity needed
    product_id = fields.Many2one('product.product', string='Product', required=True,
                                domain="[('coconut_product_ids', '!=', False)]")
    quantity = fields.Float(string='Quantity Required', required=True,
                           digits='Product Unit of Measure')
    uom_id = fields.Many2one('uom.uom', string='Unit', 
                            related='product_id.uom_id', readonly=True)
    required_date = fields.Date(string='Required Date', required=True,
                               default=fields.Date.today)
    
    # Justification
    purpose = fields.Selection([
        ('production', 'Production Input'),
        ('buffer_stock', 'Buffer Stock'),
        ('emergency', 'Emergency Stock'),
        ('replacement', 'Replacement'),
    ], string='Purpose', required=True, default='production')
    notes = fields.Text(string='Justification/Notes')
    
    # Approval workflow
    state = fields.Selection([
        ('draft', 'Draft'),
        ('submitted', 'Submitted'),
        ('approved', 'Approved'),
        ('rejected', 'Rejected'),
        ('cancel', 'Cancelled'),
    ], string='Status', default='draft', tracking=True)
    
    # Quality specification
    quality_grade_required = fields.Selection([
        ('grade_a', 'Grade A'),
        ('grade_b', 'Grade B'),
        ('grade_c', 'Grade C'),
    ], string='Required Quality Grade', default='grade_a')
    coconut_size_category = fields.Selection([
        ('small', 'Small'),
        ('medium', 'Medium'),
        ('large', 'Large'),
        ('any', 'Any'),
    ], string='Size Category', default='any')
    
    # Linked documents
    purchase_order_id = fields.Many2one('purchase.order', string='Generated PO')
    production_id = fields.Many2one('mrp.production', string='Related Production')
    
    # Supplier suggestion (based on historical performance)
    suggested_supplier_ids = fields.Many2many('coconut.supplier', 
                                              string='Suggested Suppliers',
                                              compute='_compute_suggested_suppliers')
    
    @api.model_create_multi
    def create(self, vals_list):
        for vals in vals_list:
            if vals.get('name', _('New')) == _('New'):
                vals['name'] = self.env['ir.sequence'].next_by_code('coconut.purchase.requisition') or _('New')
        return super().create(vals_list)
    
    @api.depends('product_id', 'quality_grade_required')
    def _compute_suggested_suppliers(self):
        for requisition in self:
            suppliers = self.env['coconut.supplier'].search([
                ('is_coconut_supplier', '=', True),
                ('quality_grade', '=', requisition.quality_grade_required),
                ('total_deliveries', '>', 0),
            ], order='on_time_delivery_rate desc', limit=5)
            requisition.suggested_supplier_ids = suppliers
    
    def action_submit(self):
        self.ensure_one()
        self.write({'state': 'submitted'})
        # Auto-suggest best supplier based on performance
        if not self.suggested_supplier_ids:
            raise UserError(_('No suitable suppliers found. Please create supplier records first.'))
    
    def action_approve(self):
        self.ensure_one()
        self.write({'state': 'approved'})
        # Generate Purchase Order
        self._create_purchase_order()
    
    def action_reject(self):
        self.ensure_one()
        self.write({'state': 'rejected'})
    
    def action_cancel(self):
        self.ensure_one()
        if self.purchase_order_id and self.purchase_order_id.state not in ['cancel', 'done']:
            raise UserError(_('Cannot cancel requisition with active PO. Cancel PO first.'))
        self.write({'state': 'cancel'})
    
    def action_reset_to_draft(self):
        self.ensure_one()
        self.write({'state': 'draft'})
    
    def _create_purchase_order(self):
        """Generate Purchase Order from approved requisition"""
        self.ensure_one()
        
        # Get best supplier (highest on-time delivery rate)
        best_supplier = self.suggested_supplier_ids.sorted('on_time_delivery_rate', reverse=True)[0]
        if not best_supplier:
            raise UserError(_('No supplier available'))
        
        # Create PO
        po_vals = {
            'partner_id': best_supplier.id,
            'currency_id': best_supplier.currency_id.id,
            'date_order': fields.Datetime.now(),
            'origin': self.name,
        }
        
        po = self.env['purchase.order'].create(po_vals)
        
        # Create order line
        self.env['purchase.order.line'].create({
            'order_id': po.id,
            'product_id': self.product_id.id,
            'product_qty': self.quantity,
            'product_uom': self.product_id.uom_id.id,
            'price_unit': best_supplier.unit_price or 0.0,
            'name': self.product_id.name,
            'date_planned': self.required_date,
        })
        
        self.purchase_order_id = po.id
        po.button_confirm()
        
        return po
