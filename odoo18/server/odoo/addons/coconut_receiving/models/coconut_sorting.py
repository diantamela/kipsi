# -*- coding: utf-8 -*-
from odoo import api, fields, models, _
from odoo.exceptions import UserError, ValidationError
import logging
from odoo.tools.float_utils import float_compare, float_is_zero

_logger = logging.getLogger(__name__)

TOLERANCE = 0.01  # kg rounding tolerance for mass-balance


class CoconutSorting(models.Model):
    """
    Proses Sortir Kelapa – Modul Mandiri

    Mengonsumsi Kelapa Bulat dari persediaan gudang dan menghasilkan:
      • Kelapa Layak Produksi
      • Kelapa Reject

    Mass-balance rule:
      good_coconut_kg + reject_coconut_kg == input_weight_kg  (± TOLERANCE)
    """
    _name = 'coconut.sorting'
    _description = 'Sortir Kelapa'
    _order = 'date_sorting desc, id desc'
    _inherit = ['mail.thread', 'mail.activity.mixin']

    # ───────────────────────────────── Identification ──────────────────────────
    name = fields.Char(
        string='Nomor Sortir',
        default='Baru', readonly=True, copy=False,
    )

    # ───────────────────────────────── Links ───────────────────────────────────
    receipt_id = fields.Many2one(
        'coconut.receipt', string='Sumber Penerimaan',
        required=True, ondelete='restrict',
        domain=[('state', '=', 'done')],
        help='Penerimaan kelapa sebagai referensi utama data berat bersih penerimaan.',
    )
    date_sorting = fields.Date(
        string='Tanggal Sortir',
        default=fields.Date.context_today, required=True,
    )

    # ─────────────────── Related fields from receipt (informational) ───────────
    supplier_id = fields.Many2one(
        'res.partner', string='Pemasok',
        related='receipt_id.partner_id', store=True, readonly=True,
    )
    coconut_origin = fields.Char(
        string='Asal Kelapa',
        related='receipt_id.origin', store=True, readonly=True,
    )
    vehicle_plate = fields.Char(
        string='Nomor Polisi Kendaraan',
        related='receipt_id.vehicle_plate', store=True, readonly=True,
    )

    # ───────────────────────────────── Weight Input ─────────────────────────────
    input_weight_kg = fields.Float(
        string='Kelapa Bulat Diproses (Kg)',
        compute='_compute_input_weight_kg',
        store=True,
        readonly=True,
        help='Jumlah Kelapa Bulat yang diproses diambil dari berat bersih penerimaan.',
    )

    # ───────────────────────────────── Sorting Outputs ─────────────────────────
    good_coconut_kg = fields.Float(
        string='Kelapa Layak Produksi (Kg)',
        required=True, default=0.0,
    )
    reject_coconut_kg = fields.Float(
        string='Kelapa Reject (Kg)',
        compute='_compute_reject_coconut_kg',
        store=True,
    )
    
    reject_pecah_kg = fields.Float(string='Kelapa Pecah (Kg)', default=0.0)
    reject_busuk_kg = fields.Float(string='Kelapa Busuk (Kg)', default=0.0)
    reject_kecil_kg = fields.Float(string='Kelapa Kecil (Kg)', default=0.0)
    reject_tunas_kg = fields.Float(string='Kelapa Tunas (Kg)', default=0.0)
    reject_muda_kg = fields.Float(string='Kelapa Muda (Kg)', default=0.0)

    # ───────────────────────────────── Balance Check ────────────────────────────
    balance_diff = fields.Float(
        string='Selisih Berat (Kg)',
        compute='_compute_balance',
        help='Perbedaan antara total output sortir dan input. Harus mendekati nol.',
    )
    is_balanced = fields.Boolean(
        string='Neraca Seimbang',
        compute='_compute_balance',
        store=False,
    )

    # ───────────────────────────────── Stok tersedia ────────────────────────────
    available_kelapa_bulat = fields.Float(
        string='Kelapa Bulat Tersedia di Gudang (Kg)',
        compute='_compute_available_kelapa_bulat',
        store=False,
        help='Stok Kelapa Bulat yang tersedia di gudang saat ini.',
    )

    # ───────────────────────────────── Notes ────────────────────────────────────
    notes = fields.Text(string='Keterangan')

    # ───────────────────────────────── State ────────────────────────────────────
    state = fields.Selection([
        ('draft', 'Draft'),
        ('confirmed', 'Dikonfirmasi'),
        ('done', 'Selesai'),
        ('cancelled', 'Dibatalkan'),
    ], string='Status', default='draft', tracking=True)

    company_id = fields.Many2one(
        'res.company', string='Perusahaan',
        default=lambda self: self.env.company, required=True,
    )

    # ───────────────────────────────── Stock References ─────────────────────────
    # One raw-coconut consumption move per sorting record
    raw_move_id = fields.Many2one(
        'stock.move', string='Pergerakan Kelapa Bulat (Konsumsi)',
        readonly=True, copy=False,
    )
    # Good-coconut production move
    good_move_id = fields.Many2one(
        'stock.move', string='Pergerakan Kelapa Layak',
        readonly=True, copy=False,
    )
    # Reject-coconut production move
    reject_move_id = fields.Many2one(
        'stock.move', string='Pergerakan Kelapa Reject',
        readonly=True, copy=False,
    )


    # ═══════════════════════════════ Compute Methods ═══════════════════════════

    @api.depends('receipt_id', 'receipt_id.net_received_weight')
    def _compute_input_weight_kg(self):
        for rec in self:
            rec.input_weight_kg = rec.receipt_id.net_received_weight if rec.receipt_id else 0.0

    @api.onchange('receipt_id')
    def _onchange_receipt_id(self):
        if self.receipt_id:
            self.input_weight_kg = self.receipt_id.net_received_weight
        else:
            self.input_weight_kg = 0.0

    @api.depends('reject_pecah_kg', 'reject_busuk_kg', 'reject_kecil_kg', 'reject_tunas_kg', 'reject_muda_kg')
    def _compute_reject_coconut_kg(self):
        for rec in self:
            rec.reject_coconut_kg = sum([
                rec.reject_pecah_kg, rec.reject_busuk_kg, rec.reject_kecil_kg,
                rec.reject_tunas_kg, rec.reject_muda_kg
            ])

    @api.depends('good_coconut_kg', 'reject_coconut_kg', 'input_weight_kg')
    def _compute_balance(self):
        for rec in self:
            total_out = rec.good_coconut_kg + rec.reject_coconut_kg
            diff = round(total_out - rec.input_weight_kg, 4)
            rec.balance_diff = diff
            rec.is_balanced = abs(diff) <= TOLERANCE

    @api.depends()
    def _compute_available_kelapa_bulat(self):
        for rec in self:
            rec.available_kelapa_bulat = rec._get_stock_qty(
                'coconut_receiving.product_kelapa_bulat'
            )

    # ═══════════════════════════════ Constraints ═══════════════════════════════

    @api.constrains('good_coconut_kg', 'reject_pecah_kg', 'reject_busuk_kg', 'reject_kecil_kg', 'reject_tunas_kg', 'reject_muda_kg')
    def _check_non_negative_outputs(self):
        for rec in self:
            if rec.good_coconut_kg < 0:
                raise ValidationError(_('Kelapa Layak Produksi (Kg) tidak boleh negatif.'))
            if any(val < 0 for val in [
                rec.reject_pecah_kg, rec.reject_busuk_kg, rec.reject_kecil_kg,
                rec.reject_tunas_kg, rec.reject_muda_kg
            ]):
                raise ValidationError(_('Detail Kelapa Reject (Kg) tidak boleh negatif.'))

    @api.constrains('good_coconut_kg', 'reject_pecah_kg', 'reject_busuk_kg', 'reject_kecil_kg', 'reject_tunas_kg', 'reject_muda_kg', 'input_weight_kg')
    def _check_total_output_vs_input(self):
        for rec in self:
            total_out = rec.good_coconut_kg + rec.reject_coconut_kg
            if total_out > rec.input_weight_kg:
                raise ValidationError(_('Total hasil sortir tidak boleh melebihi berat kelapa yang diproses.'))

    @api.constrains('input_weight_kg')
    def _check_input_weight(self):
        for rec in self:
            if rec.input_weight_kg <= 0:
                raise ValidationError(_('Berat Input Sortir harus lebih besar dari nol.'))

    # ═══════════════════════════════ ORM Overrides ═════════════════════════════

    @api.model_create_multi
    def create(self, vals_list):
        for vals in vals_list:
            if vals.get('name', 'Baru') in ('Baru', 'New'):
                vals['name'] = (
                    self.env['ir.sequence'].next_by_code('coconut.sorting')
                    or 'Baru'
                )
        return super().create(vals_list)

    # ═══════════════════════════════ Workflow Actions ══════════════════════════

    def action_confirm(self):
        for record in self:
            if record.state != 'draft':
                raise UserError(_('Hanya dokumen draft yang dapat dikonfirmasi.'))
            if record.input_weight_kg <= 0:
                raise UserError(_('Berat Input Sortir harus lebih besar dari nol.'))
            # Jika penerimaan dipilih, pastikan statusnya sudah selesai
            if record.receipt_id and record.receipt_id.state != 'done':
                raise UserError(_(
                    'Penerimaan Kelapa yang dipilih belum berstatus "Selesai". '
                    'Selesaikan proses penerimaan terlebih dahulu.'
                ))
            record.state = 'confirmed'

    def action_done(self):
        """
        Selesaikan proses sortir:
        1. Validasi mass balance.
        2. (Opsional) Validasi sisa stok dari penerimaan jika receipt_id dipilih.
        3. Buat stock moves:
             • Consume Kelapa Bulat  (WH → virtual production loc)
             • Produce Kelapa Layak  (virtual production loc → WH)
             • Produce Kelapa Reject (virtual production loc → WH)
        5. Set state = done.
        """
        for record in self:
            if record.state != 'confirmed':
                raise UserError(_('Hanya dokumen yang dikonfirmasi yang dapat diselesaikan.'))

            # ── Idempotency guard ──
            if record.raw_move_id or record.good_move_id or record.reject_move_id:
                raise UserError(_(
                    'Dokumen ini sudah diselesaikan dan pergerakan stok sudah tercatat. '
                    'Tidak dapat membuat pergerakan stok duplikat.'
                ))

            uom_kg = self.env.ref('uom.product_uom_kgm')

            # ── Mass balance ──
            total_out = record.good_coconut_kg + record.reject_coconut_kg
            diff = abs(round(total_out - record.input_weight_kg, 4))
            if diff > TOLERANCE:
                raise UserError(_(
                    'Neraca berat tidak seimbang!\n\n'
                    'Input: %(input).2f kg\n'
                    'Total Output: %(output).2f kg\n'
                    'Selisih: %(diff).4f kg\n\n'
                    'Pastikan: Kelapa Layak + Kelapa Reject = Berat Input.'
                ) % {
                    'input': record.input_weight_kg,
                    'output': total_out,
                    'diff': total_out - record.input_weight_kg,
                })

            # ── Cek sisa stok dari penerimaan (hanya jika receipt_id dipilih) ──
            if record.receipt_id:
                done_sortings = self.search([
                    ('receipt_id', '=', record.receipt_id.id),
                    ('state', '=', 'done'),
                ])
                already_sorted = sum(done_sortings.mapped('input_weight_kg'))
                remaining = record.receipt_id.net_received_weight - already_sorted
                if float_compare(record.input_weight_kg, remaining + TOLERANCE,
                                 precision_rounding=uom_kg.rounding) > 0:
                    raise UserError(_(
                        'Berat Input Sortir (%(input).2f kg) melebihi sisa berat belum tersortir '
                        '(%(remaining).2f kg) dari penerimaan %(receipt)s.\n\n'
                        'Kurangi berat input atau buat dokumen sortir baru sesuai sisa.'
                    ) % {
                        'input': record.input_weight_kg,
                        'remaining': remaining,
                        'receipt': record.receipt_id.name,
                    })

            # ── Resolve products ──
            def _get_variant(xml_id, label):
                tmpl = self.env.ref(xml_id, raise_if_not_found=False)
                if not tmpl:
                    raise UserError(_(
                        "Produk '%s' (XML ID: %s) tidak ditemukan. "
                        "Harap perbarui modul coconut_receiving."
                    ) % (label, xml_id))
                variant = tmpl.product_variant_id
                if not variant:
                    raise UserError(_(
                        "Varian produk '%s' tidak ditemukan. "
                        "Pastikan produk memiliki varian yang aktif."
                    ) % label)
                if variant.uom_id.category_id != uom_kg.category_id:
                    raise UserError(_(
                        "Produk '%(name)s' masih menggunakan satuan '%(uom)s' "
                        "yang bukan kategori Berat.\n"
                        "Silakan ubah satuan produk tersebut menjadi kg sebelum melanjutkan."
                    ) % {'name': variant.name, 'uom': variant.uom_id.name})
                return variant

            raw_product = _get_variant('coconut_receiving.product_kelapa_bulat', 'Kelapa Bulat')
            good_product = _get_variant('coconut_receiving.product_kelapa_layak', 'Kelapa Layak Produksi')
            reject_product = _get_variant('coconut_receiving.product_kelapa_reject', 'Kelapa Reject')

            # ── Resolve locations ──
            warehouse = self.env['stock.warehouse'].search(
                [('company_id', '=', record.company_id.id)], limit=1,
            )
            location_wh = warehouse.lot_stock_id if warehouse else False
            if not location_wh:
                location_wh = self.env['stock.location'].search(
                    [('usage', '=', 'internal'), ('company_id', '=', record.company_id.id)],
                    limit=1,
                )
            if not location_wh:
                raise UserError(_('Lokasi stok internal (Warehouse) tidak ditemukan.'))

            location_prod = self.env.ref(
                'coconut_sorting.stock_location_coconut_sorting',
                raise_if_not_found=False,
            )
            if not location_prod:
                location_prod = self.env['stock.location'].search(
                    [('usage', '=', 'production')], limit=1,
                )
            if not location_prod:
                raise UserError(_('Lokasi produksi untuk sortir kelapa tidak ditemukan.'))

            # ── Validate available stock ──
            available_qty = self.env['stock.quant']._get_available_quantity(
                raw_product, location_wh,
            )
            if float_compare(
                available_qty, record.input_weight_kg,
                precision_rounding=uom_kg.rounding,
            ) < 0:
                raise UserError(_(
                    'Stok Kelapa Bulat tidak mencukupi.\n\n'
                    'Stok tersedia: %(avail).2f kg\n'
                    'Berat yang akan disortir: %(need).2f kg'
                ) % {'avail': available_qty, 'need': record.input_weight_kg})

            # ── Create moves ──
            origin = record.name

            # Move 1: Consume raw coconut (WH → Production virtual loc)
            raw_move_vals = {
                'name': f'{origin} – Konsumsi Kelapa Bulat',
                'origin': origin,
                'product_id': raw_product.id,
                'product_uom_qty': record.input_weight_kg,
                'product_uom': uom_kg.id,
                'location_id': location_wh.id,
                'location_dest_id': location_prod.id,
                'company_id': record.company_id.id,
            }

            # Move 2: Produce good coconut (Production virtual loc → WH)
            good_move_vals = {
                'name': f'{origin} – Hasil Kelapa Layak Produksi',
                'origin': origin,
                'product_id': good_product.id,
                'product_uom_qty': record.good_coconut_kg,
                'product_uom': uom_kg.id,
                'location_id': location_prod.id,
                'location_dest_id': location_wh.id,
                'company_id': record.company_id.id,
            }

            # Move 3: Produce reject coconut (Production virtual loc → WH)
            reject_move_vals = {
                'name': f'{origin} – Hasil Kelapa Reject',
                'origin': origin,
                'product_id': reject_product.id,
                'product_uom_qty': record.reject_coconut_kg,
                'product_uom': uom_kg.id,
                'location_id': location_prod.id,
                'location_dest_id': location_wh.id,
                'company_id': record.company_id.id,
            }

            all_move_vals = [raw_move_vals, good_move_vals, reject_move_vals]
            moves = self.env['stock.move'].create(all_move_vals)
            moves._action_confirm()
            moves._action_assign()
            for move in moves:
                move.quantity = move.product_uom_qty
                move.picked = True
            moves._action_done()

            record.raw_move_id = moves[0].id
            record.good_move_id = moves[1].id
            record.reject_move_id = moves[2].id

            record.state = 'done'

            # ── Sync to Daily Stock Report ──
            if record.receipt_id:
                self.env['coconut.daily.stock']._sync_from_receipt(record.receipt_id)

    def action_cancel(self):
        for record in self:
            if record.state == 'done' or record.raw_move_id or record.good_move_id:
                raise UserError(_(
                    'Dokumen sortir yang sudah menghasilkan pergerakan stok tidak dapat '
                    'dibatalkan langsung.\n'
                    'Lakukan proses pembalikan stok (reverse) terlebih dahulu, '
                    'kemudian batalkan dokumen ini.'
                ))
            record.state = 'cancelled'

    def action_reset_draft(self):
        for record in self:
            if record.state != 'cancelled':
                raise UserError(_('Hanya dokumen yang dibatalkan yang dapat dikembalikan ke Draft.'))
            record.state = 'draft'

    # ═══════════════════════════════ Helpers ══════════════════════════════════

    def _get_stock_qty(self, xml_id):
        """Get available quantity for a product identified by XML ID."""
        try:
            tmpl = self.env.ref(xml_id, raise_if_not_found=False)
            if not tmpl:
                return 0.0
            variant = tmpl.product_variant_ids[:1]
            if not variant:
                return 0.0
            warehouse = self.env['stock.warehouse'].search(
                [('company_id', '=', self.env.company.id)], limit=1
            )
            if not warehouse:
                return 0.0
            location = warehouse.lot_stock_id
            return self.env['stock.quant']._get_available_quantity(variant, location)
        except Exception:
            return 0.0
