# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import api, fields, models, _
from odoo.exceptions import UserError, ValidationError
from odoo.tools.float_utils import float_is_zero


class CoconutSupplierReceipt(models.Model):
    _name = 'coconut.supplier.receipt'
    _description = 'Coconut Supplier Receipt'
    _rec_name = 'name'
    _order = 'date_received desc, id desc'
    _inherit = ['mail.thread', 'mail.activity.mixin']

    # ======================================================================
    # SEQUENCE / IDENTITY
    # ======================================================================
    name = fields.Char(
        string='Receipt Number',
        required=True,
        index='trigram',
        copy=False,
        default=lambda self: _('New'),
        readonly=True,
        tracking=True,
    )

    # ======================================================================
    # SUPPLIER DATA (DATA PEMASOK)
    # ======================================================================
    supplier_id = fields.Many2one(
        'res.partner',
        string='CV Supplier',
        required=True,
        index=True,
        change_default=True,
        tracking=True,
        domain="[('is_coconut_supplier', '=', True)]",
        help="Nama CV pemasok kelapa.",
    )
    contact_person = fields.Char(
        string='Contact Person',
        related='supplier_id.contact_person',
        readonly=False,
        help="Nama kontak pemasok (diambil dari data partner).",
    )
    supplier_phone = fields.Char(
        string='Supplier Phone',
        related='supplier_id.supplier_phone',
        readonly=False,
        help="Nomor HP pemasok (diambil dari data partner).",
    )
    supplier_address = fields.Text(
        string='Supplier Address',
        related='supplier_id.supplier_address',
        readonly=False,
        help="Alamat pemasok (diambil dari data partner).",
    )

    # ======================================================================
    # DELIVERY DATA (DATA PENGIRIMAN)
    # ======================================================================
    driver_name = fields.Char(
        string='Driver Name',
        required=True,
        tracking=True,
        help="Nama sopir pengirim kelapa.",
    )
    driver_phone = fields.Char(
        string='Driver Phone',
        required=True,
        help="Nomor HP sopir.",
    )
    vehicle_number = fields.Char(
        string='Vehicle Number',
        required=True,
        help="Nomor kendaraan pengirim kelapa.",
    )

    # ======================================================================
    # RECEIPT DATA (DATA PENERIMAAN)
    # ======================================================================
    date_received = fields.Date(
        string='Receipt Date',
        required=True,
        index=True,
        default=fields.Date.today,
        tracking=True,
        help="Tanggal masuk penerimaan kelapa.",
    )
    time_in = fields.Float(
        string='Time In',
        required=True,
        help="Jam masuk penerimaan kelapa (format: HH.MM, contoh: 08.30).",
    )
    total_weight_kg = fields.Float(
        string='Total Weight (Kg)',
        required=True,
        digits=(10, 2),
        tracking=True,
        help="Berat total kelapa dalam kilogram.",
    )

    # ======================================================================
    # QUALITY DATA (DATA KUALITAS KELAPA)
    # ======================================================================
    machine_cracked_kg = fields.Float(
        string='Machine Cracked (Kg)',
        required=True,
        digits=(10, 2),
        help="Kelapa cungkil mesin dalam kilogram.",
    )
    manual_cracked_kg = fields.Float(
        string='Manual Cracked (Kg)',
        required=True,
        digits=(10, 2),
        help="Kelapa cungkil manual dalam kilogram.",
    )

    # ======================================================================
    # VALIDATION STATUS (COMPUTED)
    # ======================================================================
    weight_validation_status = fields.Selection(
        [
            ('valid', '✓ Valid'),
            ('invalid', '✗ Not Valid'),
        ],
        compute='_compute_weight_validation',
        string='Weight Validation',
        help="Menampilkan status validasi: total cungkil mesin + manual harus sama dengan berat total.",
    )
    weight_difference = fields.Float(
        compute='_compute_weight_validation',
        string='Weight Difference (Kg)',
        digits=(10, 2),
        help="Selisih berat: (mesin + manual) - total. Nilai 0 berarti valid.",
    )

    @api.depends('machine_cracked_kg', 'manual_cracked_kg', 'total_weight_kg')
    def _compute_weight_validation(self):
        """Compute validation status: machine + manual must equal total weight."""
        for rec in self:
            cracked_total = rec.machine_cracked_kg + rec.manual_cracked_kg
            diff = abs(cracked_total - rec.total_weight_kg)
            if float_is_zero(diff, precision_digits=2):
                rec.weight_validation_status = 'valid'
                rec.weight_difference = 0.0
            else:
                rec.weight_validation_status = 'invalid'
                rec.weight_difference = cracked_total - rec.total_weight_kg

    # ======================================================================
    # ADDITIONAL DATA (DATA TAMBAHAN)
    # ======================================================================
    notes = fields.Text(
        string='Notes',
        help="Catatan penerimaan kelapa.",
    )
    rmp_employee_id = fields.Many2one(
        'res.users',
        string='RMP Employee',
        required=True,
        default=lambda self: self.env.user,
        tracking=True,
        help="Nama pegawai RMP yang menerima barang.",
    )

    # ======================================================================
    # INVENTORY INTEGRATION
    # ======================================================================
    picking_id = fields.Many2one(
        'stock.picking',
        string='Inventory Picking',
        readonly=True,
        copy=False,
        help="Stock picking yang dibuat saat konfirmasi penerimaan.",
    )
    picking_count = fields.Integer(
        string='Picking Count',
        compute='_compute_picking_count',
    )

    @api.depends('picking_id')
    def _compute_picking_count(self):
        for rec in self:
            rec.picking_count = 1 if rec.picking_id else 0

    # ======================================================================
    # STATE MANAGEMENT
    # ======================================================================
    state = fields.Selection(
        [
            ('draft', 'Draft'),
            ('confirmed', 'Confirmed'),
            ('done', 'Done'),
            ('cancelled', 'Cancelled'),
        ],
        string='Status',
        default='draft',
        required=True,
        tracking=True,
    )

    # ======================================================================
    # COMPANY / CURRENCY
    # ======================================================================
    company_id = fields.Many2one(
        'res.company',
        string='Company',
        required=True,
        index=True,
        default=lambda self: self.env.company.id,
    )

    # ======================================================================
    # CONSTRAINTS / VALIDATION
    # ======================================================================
    @api.constrains('machine_cracked_kg', 'manual_cracked_kg', 'total_weight_kg')
    def _check_weight_balance(self):
        """Validasi: Berat cungkil mesin + manual harus sama dengan berat total."""
        for rec in self:
            cracked_total = rec.machine_cracked_kg + rec.manual_cracked_kg
            if not float_is_zero(cracked_total - rec.total_weight_kg, precision_digits=2):
                raise ValidationError(_(
                    "Weight validation failed!\n"
                    "Machine Cracked (%.2f kg) + Manual Cracked (%.2f kg) = %.2f kg\n"
                    "Must equal Total Weight: %.2f kg.\n"
                    "Difference: %.2f kg"
                ) % (
                    rec.machine_cracked_kg,
                    rec.manual_cracked_kg,
                    cracked_total,
                    rec.total_weight_kg,
                    cracked_total - rec.total_weight_kg,
                ))

    @api.constrains('total_weight_kg', 'machine_cracked_kg', 'manual_cracked_kg')
    def _check_positive_weight(self):
        """Validasi: Semua nilai berat harus positif."""
        for rec in self:
            if rec.total_weight_kg <= 0:
                raise ValidationError(_("Total weight must be greater than 0 kg."))
            if rec.machine_cracked_kg < 0:
                raise ValidationError(_("Machine cracked weight cannot be negative."))
            if rec.manual_cracked_kg < 0:
                raise ValidationError(_("Manual cracked weight cannot be negative."))

    @api.constrains('time_in')
    def _check_time_in(self):
        """Validasi: Jam masuk harus antara 00.00 - 23.59."""
        for rec in self:
            if rec.time_in:
                hours = int(rec.time_in)
                minutes = round((rec.time_in - hours) * 100)
                if hours < 0 or hours > 23 or minutes < 0 or minutes > 59:
                    raise ValidationError(_(
                        "Time In must be a valid time between 0.00 and 23.59. "
                        "Use format HH.MM (e.g., 08.30 for 8:30 AM)."
                    ))

    # ======================================================================
    # CRUD OVERRIDES
    # ======================================================================
    @api.model_create_multi
    def create(self, vals_list):
        """Auto-generate sequence number for receipt."""
        for vals in vals_list:
            if vals.get('name', _('New')) == _('New'):
                seq_date = None
                if 'date_received' in vals:
                    seq_date = fields.Date.from_string(vals['date_received'])
                vals['name'] = self.env['ir.sequence'].next_by_code(
                    'coconut.supplier.receipt',
                    sequence_date=seq_date,
                ) or '/'
        return super(CoconutSupplierReceipt, self).create(vals_list)

    def write(self, vals):
        """Prevent editing confirmed/done/cancelled records."""
        for rec in self:
            if rec.state in ('confirmed', 'done', 'cancelled') and not self.env.context.get('force_edit'):
                raise UserError(_(
                    "Cannot edit a receipt that is already in '%s' state. "
                    "Cancel it first if you need to make changes."
                ) % rec.state)
        return super(CoconutSupplierReceipt, self).write(vals)

    def unlink(self):
        """Prevent deletion of confirmed/done records."""
        for rec in self:
            if rec.state not in ('draft', 'cancelled'):
                raise UserError(_(
                    "Cannot delete a receipt that is in '%s' state. "
                    "Cancel it first."
                ) % rec.state)
        return super(CoconutSupplierReceipt, self).unlink()

    # ======================================================================
    # BUSINESS METHODS
    # ======================================================================
    def action_confirm(self):
        """Confirm receipt: validate data and create stock picking."""
        for rec in self:
            # 1. Validate all required conditions
            if rec.state != 'draft':
                raise UserError(_("Only draft receipts can be confirmed."))

            # 2. Validate weight balance explicitly (not just constrains)
            rec._check_weight_balance()

            # 3. Get products
            machine_product = self.env.ref(
                'coconut_purchase_customization.product_coconut_machine_cracked',
                raise_if_not_found=False,
            )
            manual_product = self.env.ref(
                'coconut_purchase_customization.product_coconut_manual_cracked',
                raise_if_not_found=False,
            )

            if not machine_product or not manual_product:
                raise UserError(_(
                    "Coconut products not found. Please ensure the module data is loaded correctly."
                ))

            # 4. Get operation types
            picking_type = self.env.ref('stock.picking_type_in', raise_if_not_found=False)
            location_supplier = self.env.ref('stock.stock_location_suppliers')
            location_stock = self.env.ref('stock.stock_location_stock')

            if not picking_type:
                raise UserError(_("Receipt operation type not found. Please install the Stock module."))

            # 5. Create stock moves
            move_machine = (0, 0, {
                'name': _('Machine Cracked Coconut Receipt'),
                'product_id': machine_product.id,
                'product_uom_qty': rec.machine_cracked_kg,
                'product_uom': machine_product.uom_id.id,
                'location_id': location_supplier.id,
                'location_dest_id': location_stock.id,
            })
            move_manual = (0, 0, {
                'name': _('Manual Cracked Coconut Receipt'),
                'product_id': manual_product.id,
                'product_uom_qty': rec.manual_cracked_kg,
                'product_uom': manual_product.uom_id.id,
                'location_id': location_supplier.id,
                'location_dest_id': location_stock.id,
            })

            # 6. Create stock picking
            picking = self.env['stock.picking'].create({
                'picking_type_id': picking_type.id,
                'partner_id': rec.supplier_id.id,
                'location_id': location_supplier.id,
                'location_dest_id': location_stock.id,
                'origin': rec.name,
                'move_ids_without_package': [move_machine, move_manual],
            })

            # 7. Update receipt state
            rec.write({
                'state': 'confirmed',
                'picking_id': picking.id,
            })

        return True

    def action_validate_stock(self):
        """Validate the stock picking to actually receive goods into inventory."""
        self.ensure_one()
        if self.state != 'confirmed':
            raise UserError(_("Only confirmed receipts can be stock-validated."))
        if not self.picking_id:
            raise UserError(_("No stock picking found. Please confirm the receipt first."))

        # Validate the picking (receive products into stock)
        self.picking_id.button_validate()
        self.state = 'done'
        return True

    def action_cancel(self):
        """Cancel the receipt."""
        for rec in self:
            if rec.state not in ('draft', 'confirmed'):
                raise UserError(_("Only draft or confirmed receipts can be cancelled."))
            rec.state = 'cancelled'
        return True

    def action_draft(self):
        """Reset to draft (from cancelled)."""
        for rec in self:
            if rec.state != 'cancelled':
                raise UserError(_("Only cancelled receipts can be reset to draft."))
            rec.state = 'draft'
        return True

    def action_view_picking(self):
        """Open the related stock picking."""
        self.ensure_one()
        return {
            'type': 'ir.actions.act_window',
            'name': _('Stock Picking'),
            'res_model': 'stock.picking',
            'view_mode': 'form',
            'res_id': self.picking_id.id,
            'context': {'create': False},
        }