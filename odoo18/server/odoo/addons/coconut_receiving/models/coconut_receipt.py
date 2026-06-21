# -*- coding: utf-8 -*-
from odoo import api, fields, models, _
from odoo.exceptions import UserError, ValidationError

class CoconutReceipt(models.Model):
    _name = 'coconut.receipt'
    _description = 'Coconut Receipt'
    _order = 'date_receipt desc, id desc'

    # General Information
    name = fields.Char(string='Receipt Number', required=True, copy=False, readonly=True, default=lambda self: _('New'))
    date_receipt = fields.Datetime(string='Receipt Date', default=fields.Datetime.now, required=True)
    purchase_id = fields.Many2one('purchase.order', string='Purchase Order')
    partner_id = fields.Many2one('res.partner', string='Supplier', related='purchase_id.partner_id', store=True)
    partner_ref = fields.Char(string='Supplier Company Name', related='partner_id.name')
    driver_name = fields.Char(string='Driver Name')
    driver_phone = fields.Char(string='Driver Phone Number')
    vehicle_plate = fields.Char(string='Vehicle Plate Number')
    delivery_note = fields.Char(string='Delivery Note Number')
    origin = fields.Char(string='Coconut Origin')
    company_id = fields.Many2one('res.company', string='Company', required=True, default=lambda self: self.env.company)

    # Weight Information
    gross_weight = fields.Float(string='Gross Weight (KG)', required=True)
    total_count = fields.Integer(string='Total Coconut Count', default=0)
    avg_weight = fields.Float(string='Average Weight per Coconut (KG)', compute='_compute_avg_weight', store=True)
    rejected_weight = fields.Float(string='Rejected Weight (KG)', default=0.0)
    reject_percentage = fields.Float(string='Reject Percentage (%)', compute='_compute_weights', store=True)
    net_weight = fields.Float(string='Net Weight (KG)', compute='_compute_weights', store=True)

    # Sorting Results
    machine_shelling_weight = fields.Float(string='Machine Shelling Weight (KG)', default=0.0)
    manual_shelling_weight = fields.Float(string='Manual Shelling Weight (KG)', default=0.0)

    # Quality Assessment
    quality_grade = fields.Selection([
        ('excellent', 'Excellent'),
        ('good', 'Good'),
        ('average', 'Average'),
        ('poor', 'Poor')
    ], string='Quality Grade', default='average')
    quality_notes = fields.Text(string='Quality Notes')

    # Receiving Information
    receiving_employee_id = fields.Many2one('hr.employee', string='Receiving Employee', default=lambda self: self.env.user.employee_id)
    receiving_time = fields.Datetime(string='Receiving Time')
    notes = fields.Text(string='Notes')
    attachment_delivery = fields.Binary(string='Delivery Note Attachment', attachment=True)
    attachment_weighing = fields.Binary(string='Weighing Slip Attachment', attachment=True)

    # Workflow
    state = fields.Selection([
        ('draft', 'Draft'),
        ('inspection', 'Inspection'),
        ('approved', 'Approved'),
        ('received', 'Received'),
        ('cancelled', 'Cancelled')
    ], string='Status', default='draft', required=True, tracking=True)

    # Inventory References
    picking_id = fields.Many2one('stock.picking', string='Stock Picking', readonly=True, copy=False)
    move_ids = fields.One2many('stock.move', related='picking_id.move_ids_without_package', string='Stock Moves')

    @api.depends('gross_weight', 'total_count')
    def _compute_avg_weight(self):
        for rec in self:
            if rec.total_count > 0 and rec.gross_weight > 0:
                rec.avg_weight = rec.gross_weight / rec.total_count
            else:
                rec.avg_weight = 0.0

    @api.depends('gross_weight', 'rejected_weight')
    def _compute_weights(self):
        for rec in self:
            rec.net_weight = rec.gross_weight - rec.rejected_weight
            if rec.gross_weight > 0:
                rec.reject_percentage = (rec.rejected_weight / rec.gross_weight) * 100
            else:
                rec.reject_percentage = 0.0

    @api.constrains('gross_weight', 'rejected_weight')
    def _check_weights(self):
        for rec in self:
            if rec.gross_weight is None or rec.gross_weight <= 0:
                raise ValidationError(_("Gross Weight KG must be greater than zero."))
            if rec.rejected_weight > rec.gross_weight:
                raise ValidationError(_("Rejected Weight KG cannot be greater than Gross Weight KG."))
            if rec.net_weight < 0:
                raise ValidationError(_("Net Weight KG cannot be negative."))

    @api.constrains('machine_shelling_weight', 'manual_shelling_weight', 'net_weight')
    def _check_sorting_weights(self):
        for rec in self:
            # Avoid floating point precision issues by rounding
            total_sorting = round(rec.machine_shelling_weight + rec.manual_shelling_weight, 2)
            net_rounded = round(rec.net_weight, 2)
            # Only validate if state is approved or beyond to allow drafting
            if rec.state in ['approved', 'received'] and total_sorting != net_rounded:
                raise ValidationError(_("Machine Shelling Weight KG + Manual Shelling Weight KG must equal Net Weight KG."))

    @api.constrains('rejected_weight', 'machine_shelling_weight', 'manual_shelling_weight')
    def _check_non_negative_weights(self):
        for rec in self:
            if rec.rejected_weight < 0:
                raise ValidationError(_("Rejected Weight KG cannot be negative."))
            if rec.machine_shelling_weight < 0:
                raise ValidationError(_("Machine Shelling Weight KG cannot be negative."))
            if rec.manual_shelling_weight < 0:
                raise ValidationError(_("Manual Shelling Weight KG cannot be negative."))

    @api.model_create_multi
    def create(self, vals_list):
        for vals in vals_list:
            if vals.get('name', _('New')) == _('New'):
                vals['name'] = self.env['ir.sequence'].next_by_code('coconut.receipt.seq') or _('New')
        return super(CoconutReceipt, self).create(vals_list)

    def action_start_inspection(self):
        for rec in self:
            rec.state = 'inspection'

    def action_approve(self):
        for rec in self:
            # Ensure sorting weights match net weight before approving
            rec._check_sorting_weights()
            rec.state = 'approved'

    def action_receive(self):
        for rec in self:
            if rec.state != 'approved':
                raise UserError(_("Only approved receipts can be received into inventory."))

            product = self.env['product.product'].search([('name', '=', 'Coconut with Shell')], limit=1)
            if not product:
                raise UserError(_("Product 'Coconut with Shell' not found in the system."))

            picking_type = self.env['stock.picking.type'].search([
                ('code', '=', 'incoming'),
                ('company_id', '=', rec.company_id.id)
            ], limit=1)
            if not picking_type:
                raise UserError(_("No incoming picking type found for the company."))

            location_dest_id = picking_type.default_location_dest_id
            location_src_id = self.env.ref('stock.stock_location_suppliers', raise_if_not_found=False)
            if not location_dest_id:
                raise UserError(_("No default destination location found on the picking type."))
            if not location_src_id:
                # Fallback if XML ID is missing
                location_src_id = self.env['stock.location'].search([('usage', '=', 'supplier')], limit=1)

            picking_vals = {
                'partner_id': rec.partner_id.id,
                'picking_type_id': picking_type.id,
                'location_id': location_src_id.id,
                'location_dest_id': location_dest_id.id,
                'origin': rec.name,
                'company_id': rec.company_id.id,
            }
            picking = self.env['stock.picking'].create(picking_vals)

            move_vals = {
                'name': product.name,
                'product_id': product.id,
                'product_uom_qty': rec.net_weight,
                'product_uom': product.uom_id.id,
                'picking_id': picking.id,
                'location_id': location_src_id.id,
                'location_dest_id': location_dest_id.id,
                'company_id': rec.company_id.id,
            }
            self.env['stock.move'].create(move_vals)

            picking.action_confirm()
            # If auto-assign is needed: picking.action_assign()
            
            # Auto validate the picking
            for move in picking.move_ids:
                move.quantity = move.product_uom_qty
                move.picked = True
            picking.button_validate()

            rec.picking_id = picking.id
            rec.receiving_time = fields.Datetime.now()
            rec.state = 'received'

    def action_cancel(self):
        for rec in self:
            if rec.picking_id and rec.picking_id.state != 'cancel':
                rec.picking_id.action_cancel()
            rec.state = 'cancelled'

    def action_reset_draft(self):
        for rec in self:
            if rec.picking_id and rec.picking_id.state not in ('draft', 'cancel'):
                raise UserError(_("Cannot reset to draft because the associated stock picking is already processed."))
            rec.state = 'draft'
