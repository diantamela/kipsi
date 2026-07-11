# -*- coding: utf-8 -*-
from odoo import api, fields, models, _
from odoo.exceptions import UserError, ValidationError
import logging
from odoo.tools.float_utils import float_compare, float_is_zero

_logger = logging.getLogger(__name__)

TOLERANCE = 0.01  # kg rounding tolerance for mass-balance


class CoconutSorting(models.Model):
    """
    Proses Sortir Kelapa

    Mengonsumsi Kelapa Bulat Belum Sortir dari persediaan dan menghasilkan:
      • Kelapa Layak Produksi
      • Kelapa Reject
      • Susut Sortir (loss – dicatat via scrap)

    Mass-balance rule:
      good_coconut_kg + reject_coconut_kg + loss_kg == input_weight_kg  (± TOLERANCE)
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
        'coconut.receipt', string='Penerimaan Kelapa',
        required=True, ondelete='restrict',
        domain=[('state', '=', 'received')],
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
        string='Berat Input Sortir (Kg)',
        required=True, default=0.0,
        help='Jumlah Kelapa Bulat Belum Sortir yang akan diproses dalam batch sortir ini.',
    )

    # ───────────────────────────────── Sorting Outputs ─────────────────────────
    good_coconut_kg = fields.Float(
        string='Kelapa Layak Produksi (Kg)',
        required=True, default=0.0,
    )
    reject_coconut_kg = fields.Float(
        string='Kelapa Reject (Kg)',
        required=True, default=0.0,
    )
    loss_kg = fields.Float(
        string='Susut Sortir (Kg)',
        required=True, default=0.0,
        help='Berat yang hilang atau tidak dapat diidentifikasi selama proses sortir.',
    )

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

    # ───────────────────────────────── Remaining unsorted ───────────────────────
    remaining_unsorted_weight = fields.Float(
        string='Sisa Berat Belum Tersortir (Kg)',
        compute='_compute_remaining_unsorted',
        store=False,
        help='Berat Kelapa Bulat yang masih tersisa dari penerimaan ini (belum diproses sortir).',
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
    # Scrap for loss (stored as Many2one to stock.scrap)
    scrap_id = fields.Many2one(
        'stock.scrap', string='Catatan Susut Sortir',
        readonly=True, copy=False,
    )

    # ═══════════════════════════════ Compute Methods ═══════════════════════════

    @api.depends('good_coconut_kg', 'reject_coconut_kg', 'loss_kg', 'input_weight_kg')
    def _compute_balance(self):
        for rec in self:
            total_out = rec.good_coconut_kg + rec.reject_coconut_kg + rec.loss_kg
            diff = round(total_out - rec.input_weight_kg, 4)
            rec.balance_diff = diff
            rec.is_balanced = abs(diff) <= TOLERANCE

    @api.depends('receipt_id', 'receipt_id.remaining_unsorted_weight')
    def _compute_remaining_unsorted(self):
        for rec in self:
            if not rec.receipt_id:
                rec.remaining_unsorted_weight = 0.0
            else:
                rec.remaining_unsorted_weight = rec.receipt_id.remaining_unsorted_weight

    # ═══════════════════════════════ Constraints ═══════════════════════════════

    @api.constrains('good_coconut_kg', 'reject_coconut_kg', 'loss_kg')
    def _check_non_negative_outputs(self):
        for rec in self:
            if rec.good_coconut_kg < 0:
                raise ValidationError(_('Kelapa Layak Produksi (Kg) tidak boleh negatif.'))
            if rec.reject_coconut_kg < 0:
                raise ValidationError(_('Kelapa Reject (Kg) tidak boleh negatif.'))
            if rec.loss_kg < 0:
                raise ValidationError(_('Susut Sortir (Kg) tidak boleh negatif.'))

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
            if not record.receipt_id:
                raise UserError(_('Penerimaan Kelapa harus dipilih sebelum konfirmasi.'))
            if record.receipt_id.state != 'received':
                raise UserError(_(
                    'Penerimaan Kelapa yang dipilih belum berstatus "Diterima". '
                    'Selesaikan proses penerimaan terlebih dahulu.'
                ))
            if record.input_weight_kg <= 0:
                raise UserError(_('Berat Input Sortir harus lebih besar dari nol.'))
            record.state = 'confirmed'

    def action_done(self):
        """
        Complete the sorting process:
        1. Validate mass balance.
        2. Validate remaining unsorted stock.
        3. Create stock moves:
             • Consume Kelapa Bulat Belum Sortir  (WH → virtual production loc)
             • Produce Kelapa Layak Produksi       (virtual production loc → WH)
             • Produce Kelapa Reject               (virtual production loc → WH)
        4. Create scrap for loss_kg.
        5. Mark state = done.
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
            total_out = record.good_coconut_kg + record.reject_coconut_kg + record.loss_kg
            diff = abs(round(total_out - record.input_weight_kg, 4))
            if diff > TOLERANCE:
                raise UserError(_(
                    'Neraca berat tidak seimbang!\n\n'
                    'Input: %(input).2f kg\n'
                    'Total Output: %(output).2f kg\n'
                    'Selisih: %(diff).4f kg\n\n'
                    'Pastikan: Kelapa Layak + Kelapa Reject + Susut Sortir = Berat Input.'
                ) % {
                    'input': record.input_weight_kg,
                    'output': total_out,
                    'diff': total_out - record.input_weight_kg,
                })

            # ── Remaining stock check ──
            done_sortings = self.search([
                ('receipt_id', '=', record.receipt_id.id),
                ('state', '=', 'done'),
            ])
            already_sorted = sum(done_sortings.mapped('input_weight_kg'))
            remaining = record.receipt_id.net_weight - already_sorted
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

            raw_product = _get_variant('coconut_receiving.product_kelapa_bulat', 'Kelapa Bulat Belum Sortir')
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
                    'Stok Kelapa Bulat Belum Sortir tidak mencukupi.\n\n'
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
                'name': f'{origin} – Hasil Kelapa Layak',
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

            # ── Scrap for loss ──
            if not float_is_zero(record.loss_kg, precision_rounding=uom_kg.rounding):
                scrap = self.env['stock.scrap'].create({
                    'product_id': raw_product.id,
                    'product_uom_id': uom_kg.id,
                    'scrap_qty': record.loss_kg,
                    'location_id': location_wh.id,
                    'origin': origin,
                    'company_id': record.company_id.id,
                })
                scrap.action_validate()
                record.scrap_id = scrap.id

            record.state = 'done'

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
