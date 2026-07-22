# -*- coding: utf-8 -*-
from odoo import api, fields, models, _
from odoo.exceptions import UserError, ValidationError
from odoo.tools.float_utils import float_compare, float_is_zero
import logging

_logger = logging.getLogger(__name__)

# Rounding tolerance for kg mass-balance checks
_KG_ROUNDING = 0.01


class CoconutManufacturing(models.Model):
    """
    Transfer Kelapa ke Produksi – dokumen yang mencakup:
      1. Transfer ke Sheller (Kelapa Layak → Area Sheller Mesin / Manual)
      2. Transfer ke Parer (Hasil Sheller Mesin / Manual → Area Parer)
    """
    _name = 'coconut.manufacturing'
    _description = 'Transfer Kelapa ke Produksi'
    _order = 'production_date desc, name desc'
    _inherit = ['mail.thread', 'mail.activity.mixin']

    # ═══════════════════════════════════════════════════════════
    # IDENTIFIKASI
    # ═══════════════════════════════════════════════════════════

    name = fields.Char(
        string='Kode Transfer',
        required=True, copy=False, readonly=True,
        default=lambda self: _('Baru'),
        tracking=True,
    )
    production_date = fields.Date(
        string='Tanggal Transfer',
        default=fields.Date.context_today,
        required=True,
        tracking=True,
    )
    hasil_kerja_ids = fields.One2many(
        'coconut.hasil.kerja.harian', 'transfer_id',
        string='Hasil Kerja Harian',
    )
    material_terbuang_ids = fields.One2many(
        'coconut.material.terbuang', 'transfer_id',
        string='Material Terbuang',
    )
    layak_to_sheller_mesin = fields.Float(string='Kelapa Layak ke Sheller Mesin (Kg)', related='sheller_mesin_qty', readonly=True)
    layak_to_sheller_manual = fields.Float(string='Kelapa Layak ke Sheller Manual (Kg)', related='sheller_manual_qty', readonly=True)
    hasil_to_parer_mesin = fields.Float(string='Hasil Sheller Mesin Ditransfer ke Parer (Kg)', related='transfer_perrer_mesin_qty', readonly=True)
    hasil_to_parer_manual = fields.Float(string='Hasil Sheller Manual Ditransfer ke Parer (Kg)', related='transfer_perrer_manual_qty', readonly=True)

    hkh_sheller_mesin = fields.Float(string='Hasil Sheller Mesin (Kg)', compute='_compute_spk_stats', store=True)
    hkh_sheller_manual = fields.Float(string='Hasil Sheller Manual (Kg)', compute='_compute_spk_stats', store=True)
    hkh_parer_mesin = fields.Float(string='Hasil Parer Mesin (Kg)', compute='_compute_spk_stats', store=True)
    hkh_parer_manual = fields.Float(string='Hasil Parer Manual (Kg)', compute='_compute_spk_stats', store=True)

    waste_rusak = fields.Float(string='Material Terbuang: Rusak/Busuk (Kg)', compute='_compute_spk_stats', store=True)
    waste_tumpah = fields.Float(string='Material Terbuang: Tumpah/Hancur (Kg)', compute='_compute_spk_stats', store=True)
    waste_lainnya = fields.Float(string='Material Terbuang: Lainnya (Kg)', compute='_compute_spk_stats', store=True)
    total_material_terbuang = fields.Float(string='Total Material Terbuang (Kg)', compute='_compute_spk_stats', store=True)

    efficiency_percentage = fields.Float(string='Persentase Efisiensi Produksi (%)', compute='_compute_spk_stats', store=True)

    material_in = fields.Float(string='Material Masuk (Kg)', compute='_compute_spk_stats', store=True)
    qty_hasil = fields.Float(string='Total Hasil Produksi (Kg)', compute='_compute_spk_stats', store=True)
    material_wasted = fields.Float(string='Total Material Terbuang (Kg)', compute='_compute_spk_stats', store=True)
    remaining_material = fields.Float(string='Sisa Material Belum Diproses (Kg)', compute='_compute_spk_stats', store=True)
    status_produksi = fields.Selection([
        ('draft', 'Draft / Belum Dimulai'),
        ('progress', 'Dalam Proses'),
        ('done', 'Selesai'),
    ], string='Status Produksi SPK', compute='_compute_spk_stats', store=True, default='draft')

    @api.depends(
        'state',
        'sheller_mesin_qty',
        'sheller_manual_qty',
        'transfer_perrer_mesin_qty',
        'transfer_perrer_manual_qty',
        'hasil_kerja_ids.state',
        'hasil_kerja_ids.qty_hasil',
        'hasil_kerja_ids.process_type',
        'material_terbuang_ids.state',
        'material_terbuang_ids.qty',
        'material_terbuang_ids.reason'
    )
    def _compute_spk_stats(self):
        for rec in self:
            mat_in = 0.0
            if rec.state == 'done':
                mat_in = (
                    rec.sheller_mesin_qty + rec.sheller_manual_qty +
                    rec.transfer_perrer_mesin_qty + rec.transfer_perrer_manual_qty
                )
            rec.material_in = mat_in

            h_mesin = sum(rec.hasil_kerja_ids.filtered(lambda h: h.state == 'confirmed' and h.process_type == 'sheller_mesin').mapped('qty_hasil'))
            h_manual = sum(rec.hasil_kerja_ids.filtered(lambda h: h.state == 'confirmed' and h.process_type == 'sheller_manual').mapped('qty_hasil'))
            p_mesin = sum(rec.hasil_kerja_ids.filtered(lambda h: h.state == 'confirmed' and h.process_type == 'parer_mesin').mapped('qty_hasil'))
            p_manual = sum(rec.hasil_kerja_ids.filtered(lambda h: h.state == 'confirmed' and h.process_type == 'parer_manual').mapped('qty_hasil'))

            rec.hkh_sheller_mesin = h_mesin
            rec.hkh_sheller_manual = h_manual
            rec.hkh_parer_mesin = p_mesin
            rec.hkh_parer_manual = p_manual
            
            qty_h = h_mesin + h_manual + p_mesin + p_manual
            rec.qty_hasil = qty_h

            w_rusak = sum(rec.material_terbuang_ids.filtered(lambda w: w.state == 'done' and w.reason == 'rusak').mapped('qty'))
            w_tumpah = sum(rec.material_terbuang_ids.filtered(lambda w: w.state == 'done' and w.reason == 'tumpah').mapped('qty'))
            w_lainnya = sum(rec.material_terbuang_ids.filtered(lambda w: w.state == 'done' and w.reason == 'lainnya').mapped('qty'))

            rec.waste_rusak = w_rusak
            rec.waste_tumpah = w_tumpah
            rec.waste_lainnya = w_lainnya

            mat_w = w_rusak + w_tumpah + w_lainnya
            rec.total_material_terbuang = mat_w
            rec.material_wasted = mat_w

            rec.remaining_material = mat_in - qty_h - mat_w

            rec.efficiency_percentage = (qty_h / mat_in) * 100.0 if mat_in > 0 else 0.0

            if qty_h <= 0:
                rec.status_produksi = 'draft'
            elif rec.remaining_material > 0:
                rec.status_produksi = 'progress'
            else:
                rec.status_produksi = 'done'
    responsible_id = fields.Many2one(
        'hr.employee',
        string='Operator / Karyawan',
        default=lambda self: self.env.user.employee_id,
    )
    company_id = fields.Many2one(
        'res.company',
        string='Perusahaan',
        required=True,
        default=lambda self: self.env.company,
    )
    notes = fields.Text(string='Catatan Transfer')

    # ─── Deprecated / Unused fields to maintain history ───
    receipt_id = fields.Many2one('coconut.receipt', string='Penerimaan Kelapa (Deprecated)', deprecated=True)
    receipt_code = fields.Char(string='Kode Penerimaan (Deprecated)', deprecated=True)
    supplier_id = fields.Many2one('res.partner', string='Pemasok (Deprecated)', deprecated=True)
    coconut_origin = fields.Char(string='Asal Kelapa (Deprecated)', deprecated=True)
    receipt_date = fields.Datetime(string='Tanggal Penerimaan (Deprecated)', deprecated=True)
    net_received_weight = fields.Float(string='Berat Bersih Diterima (Deprecated)', deprecated=True)
    vehicle_number = fields.Char(string='Nomor Polisi (Deprecated)', deprecated=True)
    driver_name = fields.Char(string='Nama Supir (Deprecated)', deprecated=True)
    
    machine_sheller_input = fields.Float(string='Machine Sheller Input (Deprecated)', default=0.0, deprecated=True)
    manual_sheller_input = fields.Float(string='Manual Sheller Input (Deprecated)', default=0.0, deprecated=True)
    machine_sheller_output = fields.Float(string='Machine Sheller Output (Deprecated)', default=0.0, deprecated=True)
    manual_sheller_output = fields.Float(string='Manual Sheller Output (Deprecated)', default=0.0, deprecated=True)
    total_sheller_input = fields.Float(string='Total Sheller Input (Deprecated)', default=0.0, deprecated=True)
    total_sheller_output = fields.Float(string='Total Sheller Output (Deprecated)', default=0.0, deprecated=True)
    remaining_layak = fields.Float(string='Remaining Layak (Deprecated)', default=0.0, deprecated=True)
    remaining_reject = fields.Float(string='Remaining Reject (Deprecated)', default=0.0, deprecated=True)
    available_kelapa_sheller = fields.Float(string='Available Kelapa Sheller (Deprecated)', default=0.0, deprecated=True)
    parer_input = fields.Float(string='Parer Input (Deprecated)', default=0.0, deprecated=True)
    parer_output = fields.Float(string='Parer Output (Deprecated)', default=0.0, deprecated=True)
    remaining_kelapa_sheller = fields.Float(string='Remaining Kelapa Sheller (Deprecated)', default=0.0, deprecated=True)
    parer_notes = fields.Text(string='Parer Notes (Deprecated)', deprecated=True)
    
    shell_consume_layak_move_id = fields.Many2one('stock.move', string='Move Cons. Layak (Deprecated)', deprecated=True)
    shell_consume_reject_move_id = fields.Many2one('stock.move', string='Move Cons. Reject (Deprecated)', deprecated=True)
    shell_output_move_id = fields.Many2one('stock.move', string='Move Output Sheller (Deprecated)', deprecated=True)
    parer_consume_move_id = fields.Many2one('stock.move', string='Move Cons. Sheller (Deprecated)', deprecated=True)
    parer_output_move_id = fields.Many2one('stock.move', string='Move Output Parer (Deprecated)', deprecated=True)

    # Initial Stock stored fields (snapshot saat validasi)
    initial_stock_layak = fields.Float(string='Stok Awal Layak (Kg)', readonly=True, copy=False)
    initial_stock_reject = fields.Float(string='Stok Awal Reject (Kg)', readonly=True, copy=False)
    initial_stock_sheller = fields.Float(string='Stok Awal Sheller (Kg)', readonly=True, copy=False)
    initial_stock_parer = fields.Float(string='Stok Awal Parer (Kg)', readonly=True, copy=False)
    
    initial_stock_hasil_sheller_mesin = fields.Float(string='Stok Awal Hasil Sheller Mesin (Kg)', readonly=True, copy=False)
    initial_stock_hasil_sheller_manual = fields.Float(string='Stok Awal Hasil Sheller Manual (Kg)', readonly=True, copy=False)

    def _register_hook(self):
        super()._register_hook()
        menu = self.env.ref('mrp.menu_mrp_unbuild', raise_if_not_found=False)
        if menu:
            menu.write({'name': 'Penerimaan Kelapa'})
            menu.with_context(lang='id_ID').write({'name': 'Penerimaan Kelapa'})
            menu.with_context(lang='en_US').write({'name': 'Penerimaan Kelapa'})

    # ═══════════════════════════════════════════════════════════
    # 1. KETERSEDIAAN STOK & TRANSFER SHELLER
    # ═══════════════════════════════════════════════════════════

    available_kelapa_layak = fields.Float(
        string='Stok Kelapa Layak Tersedia (Kg)',
        compute='_compute_kelapa_layak_stock',
        store=False,
        readonly=True,
    )
    sheller_mesin_qty = fields.Float(
        string='Kelapa Layak ke Sheller Mesin (Kg)',
        default=0.0,
    )
    sheller_manual_qty = fields.Float(
        string='Kelapa Layak ke Sheller Manual (Kg)',
        default=0.0,
    )
    total_transfer_sheller = fields.Float(
        string='Total Transfer Sheller (Kg)',
        compute='_compute_total_transfer_sheller',
        store=True,
    )
    remaining_kelapa_layak = fields.Float(
        string='Sisa Kelapa Layak Setelah Transfer (Kg)',
        compute='_compute_kelapa_layak_stock',
        store=False,
        readonly=True,
    )

    # ═══════════════════════════════════════════════════════════
    # 2. TRANSFER KE PERRER
    # ═══════════════════════════════════════════════════════════

    # Mesin
    available_hasil_sheller_mesin = fields.Float(
        string='Stok Hasil Sheller Mesin Tersedia (Kg)',
        compute='_compute_hasil_sheller_mesin_stock',
        store=False,
        readonly=True,
    )
    transfer_perrer_mesin_qty = fields.Float(
        string='Hasil Sheller Mesin Ditransfer ke Perrer (Kg)',
        default=0.0,
    )
    remaining_hasil_sheller_mesin = fields.Float(
        string='Sisa Hasil Sheller Mesin Setelah Transfer (Kg)',
        compute='_compute_hasil_sheller_mesin_stock',
        store=False,
        readonly=True,
    )

    # Manual
    available_hasil_sheller_manual = fields.Float(
        string='Stok Hasil Sheller Manual Tersedia (Kg)',
        compute='_compute_hasil_sheller_manual_stock',
        store=False,
        readonly=True,
    )
    transfer_perrer_manual_qty = fields.Float(
        string='Hasil Sheller Manual Ditransfer ke Perrer (Kg)',
        default=0.0,
    )
    remaining_hasil_sheller_manual = fields.Float(
        string='Sisa Hasil Sheller Manual Setelah Transfer (Kg)',
        compute='_compute_hasil_sheller_manual_stock',
        store=False,
        readonly=True,
    )

    # ═══════════════════════════════════════════════════════════
    # WORKFLOW STATE
    # ═══════════════════════════════════════════════════════════

    state = fields.Selection([
        ('draft', 'Draft'),
        ('confirmed', 'Dikonfirmasi'),
        ('done', 'Selesai'),
        ('cancelled', 'Dibatalkan'),
    ], string='Status', default='draft', required=True, tracking=True)

    # ═══════════════════════════════════════════════════════════
    # REFERENSI PERGERAKAN STOK BARU
    # ═══════════════════════════════════════════════════════════

    sheller_mesin_move_id = fields.Many2one('stock.move', string='Move: Transfer Sheller Mesin', readonly=True, copy=False)
    sheller_manual_move_id = fields.Many2one('stock.move', string='Move: Transfer Sheller Manual', readonly=True, copy=False)
    perrer_mesin_move_id = fields.Many2one('stock.move', string='Move: Transfer Perrer Mesin', readonly=True, copy=False)
    perrer_manual_move_id = fields.Many2one('stock.move', string='Move: Transfer Perrer Manual', readonly=True, copy=False)

    # ═══════════════════════════════════════════════════════════
    # COMPUTED METHODS
    # ═══════════════════════════════════════════════════════════

    @api.depends('sheller_mesin_qty', 'sheller_manual_qty', 'state')
    def _compute_kelapa_layak_stock(self):
        for rec in self:
            if rec.state == 'done':
                avail = rec.initial_stock_layak
            else:
                avail = rec._get_stock_qty('coconut_receiving.product_kelapa_layak')
            rec.available_kelapa_layak = avail
            rec.remaining_kelapa_layak = avail - rec.total_transfer_sheller

    @api.depends('sheller_mesin_qty', 'sheller_manual_qty')
    def _compute_total_transfer_sheller(self):
        for rec in self:
            rec.total_transfer_sheller = rec.sheller_mesin_qty + rec.sheller_manual_qty

    @api.depends('transfer_perrer_mesin_qty', 'state')
    def _compute_hasil_sheller_mesin_stock(self):
        for rec in self:
            if rec.state == 'done':
                avail = rec.initial_stock_hasil_sheller_mesin
            else:
                avail = rec._get_stock_qty_in_loc('coconut_receiving.product_kelapa_sheller', 'coconut_receiving.location_stok_hasil_sheller_mesin')
            rec.available_hasil_sheller_mesin = avail
            rec.remaining_hasil_sheller_mesin = avail - rec.transfer_perrer_mesin_qty

    @api.depends('transfer_perrer_manual_qty', 'state')
    def _compute_hasil_sheller_manual_stock(self):
        for rec in self:
            if rec.state == 'done':
                avail = rec.initial_stock_hasil_sheller_manual
            else:
                avail = rec._get_stock_qty_in_loc('coconut_receiving.product_kelapa_sheller', 'coconut_receiving.location_stok_hasil_sheller_manual')
            rec.available_hasil_sheller_manual = avail
            rec.remaining_hasil_sheller_manual = avail - rec.transfer_perrer_manual_qty

    # ═══════════════════════════════════════════════════════════
    # ORM OVERRIDES
    # ═══════════════════════════════════════════════════════════

    @api.model_create_multi
    def create(self, vals_list):
        for vals in vals_list:
            if vals.get('name', _('Baru')) in (_('Baru'), _('New'), 'Baru', 'New'):
                vals['name'] = (
                    self.env['ir.sequence'].next_by_code('coconut.manufacturing')
                    or _('Baru')
                )
        return super().create(vals_list)

    def write(self, vals):
        for rec in self:
            if rec.state == 'done':
                user_fields = [
                    k for k in vals.keys()
                    if k != 'state'
                    and not k.startswith('message_')
                    and not k.startswith('activity_')
                    and k not in ('message_ids', 'message_follower_ids', 'activity_ids')
                ]
                if user_fields:
                    raise UserError(_(
                        "Dokumen Pemakaian Kelapa Produksi yang sudah selesai tidak dapat diedit. "
                        "Buat dokumen koreksi jika diperlukan."
                    ))
        return super().write(vals)

    # ═══════════════════════════════════════════════════════════
    # WORKFLOW ACTIONS
    # ═══════════════════════════════════════════════════════════

    def action_confirm(self):
        for rec in self:
            if rec.state != 'draft':
                raise UserError(_("Hanya dokumen Draft yang dapat dikonfirmasi."))
            rec.state = 'confirmed'

    def action_validate(self):
        """
        Validasi dokumen Transfer Kelapa ke Produksi.
        Memindahkan Kelapa Layak Produksi ke Area Sheller Mesin/Manual,
        dan memindahkan Hasil Sheller ke Area Parer.
        """
        for rec in self:
            if rec.state != 'confirmed':
                raise UserError(_("Hanya dokumen yang dikonfirmasi yang dapat divalidasi."))
            
            # Idempotency check
            if rec.sheller_mesin_move_id or rec.sheller_manual_move_id or rec.perrer_mesin_move_id or rec.perrer_manual_move_id:
                raise UserError(_("Dokumen ini sudah divalidasi."))

            uom_kg = self.env.ref('uom.product_uom_kgm')

            # Validation checks against available stocks
            if rec.total_transfer_sheller > rec.available_kelapa_layak:
                raise UserError(_(
                    "Total transfer ke Sheller (%(need)s kg) melebihi stok Kelapa Layak tersedia (%(avail)s kg)."
                ) % {'need': rec.total_transfer_sheller, 'avail': rec.available_kelapa_layak})

            if rec.transfer_perrer_mesin_qty > rec.available_hasil_sheller_mesin:
                raise UserError(_(
                    "Transfer Hasil Sheller Mesin ke Perrer (%(need)s kg) melebihi stok tersedia (%(avail)s kg)."
                ) % {'need': rec.transfer_perrer_mesin_qty, 'avail': rec.available_hasil_sheller_mesin})

            if rec.transfer_perrer_manual_qty > rec.available_hasil_sheller_manual:
                raise UserError(_(
                    "Transfer Hasil Sheller Manual ke Perrer (%(need)s kg) melebihi stok tersedia (%(avail)s kg)."
                ) % {'need': rec.transfer_perrer_manual_qty, 'avail': rec.available_hasil_sheller_manual})

            # Store initial stock levels before stock movements
            rec.write({
                'initial_stock_layak': rec.available_kelapa_layak,
                'initial_stock_hasil_sheller_mesin': rec.available_hasil_sheller_mesin,
                'initial_stock_hasil_sheller_manual': rec.available_hasil_sheller_manual,
            })

            # Resolve products
            p_layak = rec._resolve_product('coconut_receiving.product_kelapa_layak', 'Kelapa Layak Produksi', uom_kg)
            p_sheller = rec._resolve_product('coconut_receiving.product_kelapa_sheller', 'Kelapa Sheller', uom_kg)

            # Resolve locations
            loc_layak = rec.env.ref('coconut_receiving.location_stok_kelapa_layak')
            loc_sheller_mesin = rec.env.ref('coconut_receiving.location_area_sheller_mesin')
            loc_sheller_manual = rec.env.ref('coconut_receiving.location_area_sheller_manual')
            loc_hasil_mesin = rec.env.ref('coconut_receiving.location_stok_hasil_sheller_mesin')
            loc_hasil_manual = rec.env.ref('coconut_receiving.location_stok_hasil_sheller_manual')
            loc_parer = rec.env.ref('coconut_receiving.location_area_parer')

            origin = f'{rec.name}'

            # Move 1: Sheller Mesin
            if rec.sheller_mesin_qty > 0:
                move = rec.env['stock.move'].create({
                    'name': f'{origin} – Transfer Kelapa Layak ke Area Sheller Mesin',
                    'origin': origin,
                    'product_id': p_layak.id,
                    'product_uom_qty': rec.sheller_mesin_qty,
                    'product_uom': uom_kg.id,
                    'location_id': loc_layak.id,
                    'location_dest_id': loc_sheller_mesin.id,
                    'company_id': rec.company_id.id,
                })
                move._action_confirm()
                move._action_assign()
                move.quantity = move.product_uom_qty
                move.picked = True
                move._action_done()
                rec.sheller_mesin_move_id = move.id

            # Move 2: Sheller Manual
            if rec.sheller_manual_qty > 0:
                move = rec.env['stock.move'].create({
                    'name': f'{origin} – Transfer Kelapa Layak ke Area Sheller Manual',
                    'origin': origin,
                    'product_id': p_layak.id,
                    'product_uom_qty': rec.sheller_manual_qty,
                    'product_uom': uom_kg.id,
                    'location_id': loc_layak.id,
                    'location_dest_id': loc_sheller_manual.id,
                    'company_id': rec.company_id.id,
                })
                move._action_confirm()
                move._action_assign()
                move.quantity = move.product_uom_qty
                move.picked = True
                move._action_done()
                rec.sheller_manual_move_id = move.id

            # Move 3: Perrer Mesin
            if rec.transfer_perrer_mesin_qty > 0:
                move = rec.env['stock.move'].create({
                    'name': f'{origin} – Transfer Hasil Sheller Mesin ke Area Parer',
                    'origin': origin,
                    'product_id': p_sheller.id,
                    'product_uom_qty': rec.transfer_perrer_mesin_qty,
                    'product_uom': uom_kg.id,
                    'location_id': loc_hasil_mesin.id,
                    'location_dest_id': loc_parer.id,
                    'company_id': rec.company_id.id,
                })
                move._action_confirm()
                move._action_assign()
                move.quantity = move.product_uom_qty
                move.picked = True
                move._action_done()
                rec.perrer_mesin_move_id = move.id

            # Move 4: Perrer Manual
            if rec.transfer_perrer_manual_qty > 0:
                move = rec.env['stock.move'].create({
                    'name': f'{origin} – Transfer Hasil Sheller Manual ke Area Parer',
                    'origin': origin,
                    'product_id': p_sheller.id,
                    'product_uom_qty': rec.transfer_perrer_manual_qty,
                    'product_uom': uom_kg.id,
                    'location_id': loc_hasil_manual.id,
                    'location_dest_id': loc_parer.id,
                    'company_id': rec.company_id.id,
                })
                move._action_confirm()
                move._action_assign()
                move.quantity = move.product_uom_qty
                move.picked = True
                move._action_done()
                rec.perrer_manual_move_id = move.id

            rec.state = 'done'

    def action_cancel(self):
        for rec in self:
            if rec.state == 'done':
                raise UserError(_(
                    "Dokumen '%s' sudah selesai. Pergerakan stok tidak dapat dibatalkan secara otomatis."
                ) % rec.name)
            rec.state = 'cancelled'

    def action_reset_draft(self):
        for rec in self:
            if rec.state != 'cancelled':
                raise UserError(_("Hanya dokumen yang dibatalkan yang dapat dikembalikan ke Draft."))
            rec.state = 'draft'

    # ═══════════════════════════════════════════════════════════
    # LOCATION & PRODUCT HELPERS
    # ═══════════════════════════════════════════════════════════

    def _resolve_product(self, xml_id, label, uom_kg):
        """Resolve product variant by XML ID with UoM validation."""
        tmpl = self.env.ref(xml_id, raise_if_not_found=False)
        if not tmpl:
            raise UserError(_("Produk '%s' tidak ditemukan.") % label)
        variant = tmpl.product_variant_ids[:1]
        if not variant:
            raise UserError(_("Varian produk '%s' tidak ditemukan.") % label)
        return variant

    def _get_stock_qty(self, xml_id):
        """Get available quantity for a product in its default location mapping."""
        loc_map = {
            'coconut_receiving.product_kelapa_layak': 'coconut_receiving.location_stok_kelapa_layak',
        }
        loc_xml_id = loc_map.get(xml_id)
        if not loc_xml_id:
            return 0.0
        return self._get_stock_qty_in_loc(xml_id, loc_xml_id)

    def _get_stock_qty_in_loc(self, product_xml_id, location_xml_id):
        """Helper to fetch quantity in specific location."""
        try:
            tmpl = self.env.ref(product_xml_id, raise_if_not_found=False)
            if not tmpl:
                return 0.0
            variant = tmpl.product_variant_ids[:1]
            if not variant:
                return 0.0
            location = self.env.ref(location_xml_id, raise_if_not_found=False)
            if not location:
                return 0.0
            return self.env['stock.quant']._get_available_quantity(variant, location)
        except Exception:
            return 0.0

    def get_report_stock_data(self):
        """Returns stock data dictionary for report rendering."""
        return {
            'layak': {
                'awal': self.initial_stock_layak if self.state == 'done' else self._get_stock_qty('coconut_receiving.product_kelapa_layak'),
                'transfer_mesin': self.sheller_mesin_qty,
                'transfer_manual': self.sheller_manual_qty,
            },
            'hasil_mesin': {
                'awal': self.initial_stock_hasil_sheller_mesin if self.state == 'done' else self._get_stock_qty_in_loc('coconut_receiving.product_kelapa_sheller', 'coconut_receiving.location_stok_hasil_sheller_mesin'),
                'transfer': self.transfer_perrer_mesin_qty,
            },
            'hasil_manual': {
                'awal': self.initial_stock_hasil_sheller_manual if self.state == 'done' else self._get_stock_qty_in_loc('coconut_receiving.product_kelapa_sheller', 'coconut_receiving.location_stok_hasil_sheller_manual'),
                'transfer': self.transfer_perrer_manual_qty,
            }
        }

    def format_kg(self, value):
        """Helper to format weight in Indonesian style: 20.000 Kg"""
        return "{:,.0f} Kg".format(value).replace(',', '.')

    def format_kg_raw(self, value):
        """Helper to format weight in Indonesian style without Kg suffix: 20000 -> 20.000"""
        return "{:,.0f}".format(value).replace(',', '.')
