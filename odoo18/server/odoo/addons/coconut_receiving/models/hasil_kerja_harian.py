# -*- coding: utf-8 -*-
from odoo import api, fields, models, _
from odoo.exceptions import UserError, ValidationError

class CoconutHasilKerjaHarian(models.Model):
    _name = 'coconut.hasil.kerja.harian'
    _description = 'Hasil Kerja Harian'
    _order = 'date desc, name desc'
    _inherit = ['mail.thread', 'mail.activity.mixin']

    name = fields.Char(
        string='Nomor Hasil Kerja',
        required=True, copy=False, readonly=True,
        default=lambda self: _('Baru'),
    )
    transfer_id = fields.Many2one(
        'coconut.manufacturing',
        string='Transfer Kelapa ke Produksi',
        required=True,
        domain=[('state', '=', 'done')],
        tracking=True,
    )
    date = fields.Date(
        string='Tanggal',
        default=fields.Date.context_today,
        required=True,
        tracking=True,
    )
    shift = fields.Selection([
        ('shift_1', 'Shift 1'),
        ('shift_2', 'Shift 2'),
        ('shift_3', 'Shift 3'),
    ], string='Shift', required=True, default='shift_1', tracking=True)

    operator_id = fields.Many2one(
        'hr.employee',
        string='Operator / Karyawan',
        required=True,
        tracking=True,
    )
    machine_id = fields.Many2one(
        'mrp.workcenter',
        string='Mesin',
    )
    process_type = fields.Selection([
        ('sheller_mesin', 'Sheller Mesin'),
        ('sheller_manual', 'Sheller Manual'),
        ('parer_mesin', 'Perrer dari Sheller Mesin'),
        ('parer_manual', 'Perrer dari Sheller Manual'),
    ], string='Jenis Proses', required=True, tracking=True)

    material_in_qty = fields.Float(
        string='Material Masuk (Kg)',
        compute='_compute_material_in_qty',
        store=True,
        readonly=True,
    )
    qty_hasil = fields.Float(
        string='Qty Hasil (Kg)',
        required=True,
        default=0.0,
        tracking=True,
    )
    remaining_material = fields.Float(
        string='Sisa Material (Kg)',
        compute='_compute_remaining_material',
        store=True,
        readonly=True,
    )
    state = fields.Selection([
        ('draft', 'Draft'),
        ('confirmed', 'Dikonfirmasi'),
        ('cancelled', 'Dibatalkan'),
    ], string='Status', default='draft', required=True, tracking=True)

    raw_move_id = fields.Many2one('stock.move', string='Move: Konsumsi Bahan Baku', readonly=True, copy=False)
    finished_move_id = fields.Many2one('stock.move', string='Move: Hasil Produksi', readonly=True, copy=False)

    @api.depends('transfer_id', 'process_type')
    def _compute_material_in_qty(self):
        for rec in self:
            qty = 0.0
            if rec.transfer_id and rec.process_type:
                if rec.process_type == 'sheller_mesin':
                    qty = rec.transfer_id.sheller_mesin_qty
                elif rec.process_type == 'sheller_manual':
                    qty = rec.transfer_id.sheller_manual_qty
                elif rec.process_type == 'parer_mesin':
                    qty = rec.transfer_id.transfer_perrer_mesin_qty
                elif rec.process_type == 'parer_manual':
                    qty = 0.0
            rec.material_in_qty = qty

    @api.depends('material_in_qty', 'qty_hasil')
    def _compute_remaining_material(self):
        for rec in self:
            rec.remaining_material = rec.material_in_qty - rec.qty_hasil

    @api.model_create_multi
    def create(self, vals_list):
        for vals in vals_list:
            if vals.get('name', _('Baru')) in (_('Baru'), _('New'), 'Baru', 'New'):
                vals['name'] = (
                    self.env['ir.sequence'].next_by_code('coconut.hasil.kerja.harian')
                    or _('Baru')
                )
        return super().create(vals_list)

    def write(self, vals):
        for rec in self:
            if rec.state == 'confirmed' and any(k in vals for k in ('qty_hasil', 'process_type', 'transfer_id')):
                raise UserError(_("Dokumen yang sudah dikonfirmasi tidak dapat diedit."))
        return super().write(vals)

    def action_confirm(self):
        for rec in self:
            if rec.state != 'draft':
                raise UserError(_("Hanya dokumen Draft yang dapat dikonfirmasi."))

            if rec.qty_hasil <= 0:
                raise UserError(_("Kuantitas hasil produksi harus lebih besar dari 0."))

            # Cumulative Validation
            domain = [
                ('transfer_id', '=', rec.transfer_id.id),
                ('process_type', '=', rec.process_type),
                ('state', '=', 'confirmed'),
                ('id', '!=', rec.id),
            ]
            other_records = self.search(domain)
            total_other = sum(other_records.mapped('qty_hasil'))

            if total_other + rec.qty_hasil > rec.material_in_qty:
                raise ValidationError(_(
                    "Total hasil produksi secara kumulatif (%(total)s Kg) tidak boleh melebihi kuantitas material masuk transfer asal (%(limit)s Kg)."
                ) % {
                    'total': total_other + rec.qty_hasil,
                    'limit': rec.material_in_qty
                })

            # Create stock movements
            rec._create_stock_moves()
            rec.state = 'confirmed'

    def action_cancel(self):
        for rec in self:
            if rec.state != 'confirmed':
                raise UserError(_("Hanya dokumen dikonfirmasi yang dapat dibatalkan."))
            if rec.raw_move_id or rec.finished_move_id:
                moves = (rec.raw_move_id | rec.finished_move_id).filtered(lambda m: m.state not in ('cancel', 'done'))
                moves._action_cancel()
            rec.state = 'cancelled'

    def action_reset_draft(self):
        for rec in self:
            if rec.state != 'cancelled':
                raise UserError(_("Hanya dokumen dibatalkan yang dapat dikembalikan ke draft."))
            rec.state = 'draft'

    def _create_stock_moves(self):
        self.ensure_one()
        uom_kg = self.env.ref('uom.product_uom_kgm')

        p_layak = self.env.ref('coconut_receiving.product_kelapa_layak').product_variant_ids[:1]
        p_sheller = self.env.ref('coconut_receiving.product_kelapa_sheller').product_variant_ids[:1]
        p_parer = self.env.ref('coconut_receiving.product_kelapa_parer').product_variant_ids[:1]

        loc_production = self.env.ref('coconut_receiving.stock_location_coconut_manufacturing')
        loc_sheller_mesin = self.env.ref('coconut_receiving.location_area_sheller_mesin')
        loc_sheller_manual = self.env.ref('coconut_receiving.location_area_sheller_manual')
        loc_hasil_mesin = self.env.ref('coconut_receiving.location_stok_hasil_sheller_mesin')
        loc_hasil_manual = self.env.ref('coconut_receiving.location_stok_hasil_sheller_manual')
        loc_area_parer = self.env.ref('coconut_receiving.location_area_parer')

        origin = self.name

        if self.process_type == 'sheller_mesin':
            raw_move = self.env['stock.move'].create({
                'name': f'{origin} – Konsumsi Kelapa Layak (Sheller Mesin)',
                'origin': origin,
                'product_id': p_layak.id,
                'product_uom_qty': self.qty_hasil,
                'product_uom': uom_kg.id,
                'location_id': loc_sheller_mesin.id,
                'location_dest_id': loc_production.id,
                'company_id': self.transfer_id.company_id.id,
            })
            finished_move = self.env['stock.move'].create({
                'name': f'{origin} – Produksi Kelapa Sheller (Sheller Mesin)',
                'origin': origin,
                'product_id': p_sheller.id,
                'product_uom_qty': self.qty_hasil,
                'product_uom': uom_kg.id,
                'location_id': loc_production.id,
                'location_dest_id': loc_hasil_mesin.id,
                'company_id': self.transfer_id.company_id.id,
            })
        elif self.process_type == 'sheller_manual':
            raw_move = self.env['stock.move'].create({
                'name': f'{origin} – Konsumsi Kelapa Reject (Sheller Manual)',
                'origin': origin,
                'product_id': p_reject.id,
                'product_uom_qty': self.qty_hasil,
                'product_uom': uom_kg.id,
                'location_id': loc_sheller_manual.id,
                'location_dest_id': loc_production.id,
                'company_id': self.transfer_id.company_id.id,
            })
            finished_move = self.env['stock.move'].create({
                'name': f'{origin} – Produksi Kelapa Sheller (Sheller Manual)',
                'origin': origin,
                'product_id': p_sheller.id,
                'product_uom_qty': self.qty_hasil,
                'product_uom': uom_kg.id,
                'location_id': loc_production.id,
                'location_dest_id': loc_hasil_manual.id,
                'company_id': self.transfer_id.company_id.id,
            })
        elif self.process_type in ('parer_mesin', 'parer_manual'):
            raw_move = self.env['stock.move'].create({
                'name': f'{origin} – Konsumsi Kelapa Sheller (Parer)',
                'origin': origin,
                'product_id': p_sheller.id,
                'product_uom_qty': self.qty_hasil,
                'product_uom': uom_kg.id,
                'location_id': loc_area_parer.id,
                'location_dest_id': loc_production.id,
                'company_id': self.transfer_id.company_id.id,
            })
            finished_move = self.env['stock.move'].create({
                'name': f'{origin} – Produksi Kelapa Parer',
                'origin': origin,
                'product_id': p_parer.id,
                'product_uom_qty': self.qty_hasil,
                'product_uom': uom_kg.id,
                'location_id': loc_production.id,
                'location_dest_id': loc_area_parer.id,
                'company_id': self.transfer_id.company_id.id,
            })

        for move in (raw_move | finished_move):
            move._action_confirm()
            move._action_assign()
            move.quantity = move.product_uom_qty
            move.picked = True
            move._action_done()

        self.write({
            'raw_move_id': raw_move.id,
            'finished_move_id': finished_move.id,
        })
