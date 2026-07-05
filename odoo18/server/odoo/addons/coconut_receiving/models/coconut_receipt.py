# -*- coding: utf-8 -*-
from odoo import api, fields, models, _
from odoo.exceptions import UserError, ValidationError

class CoconutReceipt(models.Model):
    _name = 'coconut.receipt'
    _description = 'Penerimaan Kelapa'
    _order = 'date_receipt desc, id desc'

    # General Information
    name = fields.Char(string='Nomor Penerimaan', required=True, copy=False, readonly=True, default=lambda self: _('Baru'))
    date_receipt = fields.Datetime(string='Tanggal Penerimaan', default=fields.Datetime.now, required=True)
    purchase_id = fields.Many2one('purchase.order', string='Purchase Order')
    partner_id = fields.Many2one('res.partner', string='Pemasok', related='purchase_id.partner_id', store=True)
    partner_ref = fields.Char(string='Nama Perusahaan Pemasok', related='partner_id.name')
    driver_name = fields.Char(string='Nama Supir')
    driver_phone = fields.Char(string='Nomor Telepon Supir')
    vehicle_plate = fields.Char(string='Nomor Polisi Kendaraan')
    delivery_note = fields.Char(string='Nomor Surat Jalan')
    origin = fields.Char(string='Asal Kelapa')
    company_id = fields.Many2one('res.company', string='Perusahaan', required=True, default=lambda self: self.env.company)

    # Weight Information
    gross_weight = fields.Float(string='Berat Kotor (KG)', required=True)
    total_count = fields.Integer(string='Total Jumlah Kelapa', default=0)
    avg_weight = fields.Float(string='Berat Rata-rata per Kelapa (KG)', compute='_compute_avg_weight', store=True)
    rejected_weight = fields.Float(string='Berat Ditolak (KG)', default=0.0)
    reject_percentage = fields.Float(string='Persentase Ditolak (%)', compute='_compute_weights', store=True)
    net_weight = fields.Float(string='Berat Bersih (KG)', compute='_compute_weights', store=True)

    # Sorting Results
    machine_shelling_weight = fields.Float(string='Berat Cungkil Mesin (KG)', default=0.0)
    manual_shelling_weight = fields.Float(string='Berat Cungkil Manual (KG)', default=0.0)

    # Quality Assessment
    quality_grade = fields.Selection([
        ('excellent', 'Sangat Baik'),
        ('good', 'Baik'),
        ('average', 'Rata-rata'),
        ('poor', 'Buruk')
    ], string='Nilai Kualitas', default='average')
    quality_notes = fields.Text(string='Catatan Kualitas')

    # Receiving Information
    receiving_employee_id = fields.Many2one('hr.employee', string='Karyawan Penerima', default=lambda self: self.env.user.employee_id)
    receiving_time = fields.Datetime(string='Waktu Penerimaan')
    notes = fields.Text(string='Catatan')
    attachment_delivery = fields.Binary(string='Lampiran Surat Jalan', attachment=True)
    attachment_weighing = fields.Binary(string='Lampiran Slip Timbangan', attachment=True)

    # Workflow
    state = fields.Selection([
        ('draft', 'Draft'),
        ('inspection', 'Pemeriksaan'),
        ('approved', 'Disetujui'),
        ('received', 'Diterima'),
        ('cancelled', 'Dibatalkan')
    ], string='Status', default='draft', required=True, tracking=True)

    # Inventory References
    picking_id = fields.Many2one('stock.picking', string='Pengambilan Stok', readonly=True, copy=False)
    move_ids = fields.One2many('stock.move', related='picking_id.move_ids_without_package', string='Pergerakan Stok')

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
                raise ValidationError(_("Berat Kotor KG harus lebih besar dari nol."))
            if rec.rejected_weight > rec.gross_weight:
                raise ValidationError(_("Berat Ditolak KG tidak boleh lebih besar dari Berat Kotor KG."))
            if rec.net_weight < 0:
                raise ValidationError(_("Berat Bersih KG tidak boleh negatif."))

    @api.constrains('machine_shelling_weight', 'manual_shelling_weight', 'net_weight')
    def _check_sorting_weights(self):
        for rec in self:
            # Avoid floating point precision issues by rounding
            total_sorting = round(rec.machine_shelling_weight + rec.manual_shelling_weight, 2)
            net_rounded = round(rec.net_weight, 2)
            # Only validate if state is approved or beyond to allow drafting
            if rec.state in ['approved', 'received'] and total_sorting != net_rounded:
                raise ValidationError(_("Berat Cungkil Mesin KG + Berat Cungkil Manual KG harus sama dengan Berat Bersih KG."))

    @api.constrains('rejected_weight', 'machine_shelling_weight', 'manual_shelling_weight')
    def _check_non_negative_weights(self):
        for rec in self:
            if rec.rejected_weight < 0:
                raise ValidationError(_("Berat Ditolak KG tidak boleh negatif."))
            if rec.machine_shelling_weight < 0:
                raise ValidationError(_("Berat Cungkil Mesin KG tidak boleh negatif."))
            if rec.manual_shelling_weight < 0:
                raise ValidationError(_("Berat Cungkil Manual KG tidak boleh negatif."))

    @api.model_create_multi
    def create(self, vals_list):
        for vals in vals_list:
            if vals.get('name', _('Baru')) == _('Baru') or vals.get('name', _('New')) == _('New'):
                vals['name'] = self.env['ir.sequence'].next_by_code('coconut.receipt.seq') or _('Baru')
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
                raise UserError(_("Hanya penerimaan yang disetujui yang dapat diterima ke dalam persediaan."))

            product = self.env['product.product'].search([('name', '=', 'Kelapa Bulat')], limit=1)
            if not product:
                raise UserError(_("Produk 'Kelapa Bulat' tidak ditemukan di sistem."))

            picking_type = self.env['stock.picking.type'].search([
                ('code', '=', 'incoming'),
                ('company_id', '=', rec.company_id.id)
            ], limit=1)
            if not picking_type:
                raise UserError(_("Tipe pengambilan barang masuk tidak ditemukan untuk perusahaan."))

            location_dest_id = picking_type.default_location_dest_id
            location_src_id = self.env.ref('stock.stock_location_suppliers', raise_if_not_found=False)
            if not location_dest_id:
                raise UserError(_("Lokasi tujuan default tidak ditemukan pada tipe pengambilan."))
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
                raise UserError(_("Tidak dapat mengembalikan ke draft karena pengambilan stok terkait sudah diproses."))
            rec.state = 'draft'
