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
    Manufaktur Kelapa – dokumen tunggal yang mencakup:
      1. Sortir Kelapa (Kelapa Bulat → Kelapa Layak + Kelapa Reject)
      2. Sheller   (Machine: Layak → Sheller | Manual: Reject → Sheller)
      3. Parer     (Kelapa Sheller → Kelapa Parer)

    Setiap proses dieksekusi saat dokumen divalidasi (action_validate).
    Pergerakan stok direkam melalui stock.move standar Odoo.
    """
    _name = 'coconut.manufacturing'
    _description = 'Manufaktur Kelapa'
    _order = 'production_date desc, name desc'
    _inherit = ['mail.thread', 'mail.activity.mixin']

    # ═══════════════════════════════════════════════════════════
    # IDENTIFIKASI
    # ═══════════════════════════════════════════════════════════

    name = fields.Char(
        string='Kode Manufaktur',
        required=True, copy=False, readonly=True,
        default=lambda self: _('Baru'),
        tracking=True,
    )
    production_date = fields.Date(
        string='Tanggal Produksi',
        default=fields.Date.context_today,
        required=True,
        tracking=True,
    )
    responsible_id = fields.Many2one(
        'hr.employee',
        string='Karyawan Bertanggung Jawab',
        default=lambda self: self.env.user.employee_id,
    )
    company_id = fields.Many2one(
        'res.company',
        string='Perusahaan',
        required=True,
        default=lambda self: self.env.company,
    )
    notes = fields.Text(string='Catatan Produksi')

    # ═══════════════════════════════════════════════════════════
    # SUMBER PENERIMAAN
    # ═══════════════════════════════════════════════════════════

    receipt_id = fields.Many2one(
        'coconut.receipt',
        string='Penerimaan Kelapa',
        required=True,
        ondelete='restrict',
        domain=[('state', '=', 'done')],
        tracking=True,
    )

    # ─── Related / readonly display from receipt ───
    receipt_code = fields.Char(
        string='Kode Penerimaan',
        related='receipt_id.name',
        readonly=True,
        store=False,
    )
    supplier_id = fields.Many2one(
        'res.partner',
        string='Pemasok',
        related='receipt_id.partner_id',
        readonly=True,
        store=True,
    )
    coconut_origin = fields.Char(
        string='Asal Kelapa',
        related='receipt_id.origin',
        readonly=True,
        store=True,
    )
    receipt_date = fields.Datetime(
        string='Tanggal Penerimaan',
        related='receipt_id.entry_datetime',
        readonly=True,
        store=False,
    )
    net_received_weight = fields.Float(
        string='Berat Bersih Diterima (Kg)',
        related='receipt_id.net_received_weight',
        readonly=True,
        store=False,
    )
    vehicle_number = fields.Char(
        string='Nomor Polisi',
        related='receipt_id.vehicle_plate',
        readonly=True,
        store=False,
    )
    driver_name = fields.Char(
        string='Nama Supir',
        related='receipt_id.driver_name',
        readonly=True,
        store=False,
    )

    # Remaining Kelapa Bulat from this receipt (computed from stock)
    remaining_kelapa_bulat = fields.Float(
        string='Sisa Kelapa Bulat dari Penerimaan (Kg)',
        compute='_compute_remaining_kelapa_bulat',
        store=False,
        readonly=True,
        help='Sisa Kelapa Bulat yang tersedia dari penerimaan ini berdasarkan pergerakan stok.',
    )

    # ═══════════════════════════════════════════════════════════
    # SORTIR KELAPA
    # ═══════════════════════════════════════════════════════════

    raw_coconut_processed = fields.Float(
        string='Kelapa Bulat Diproses (Kg)',
        default=0.0,
        help='Jumlah Kelapa Bulat yang masuk ke proses sortir.',
    )
    total_coconut_count = fields.Integer(
        string='Jumlah Kelapa (Butir)',
        default=0,
        help='Total jumlah buah kelapa yang disortir.',
    )
    good_coconut_weight = fields.Float(
        string='Kelapa Layak Produksi (Kg)',
        default=0.0,
    )
    reject_coconut_weight = fields.Float(
        string='Kelapa Reject (Kg)',
        default=0.0,
    )

    # computed
    kg_per_coconut = fields.Float(
        string='KG per Butir',
        compute='_compute_sorting_derived',
        store=False,
        readonly=True,
    )
    remaining_unsorted = fields.Float(
        string='Sisa Kelapa Belum Disortir (Kg)',
        compute='_compute_sorting_derived',
        store=False,
        readonly=True,
        help='Sisa Kelapa Bulat dari penerimaan ini yang belum diproses sortir.',
    )

    # ═══════════════════════════════════════════════════════════
    # SHELLER
    # ═══════════════════════════════════════════════════════════

    machine_sheller_input = fields.Float(
        string='Input Machine Sheller (Kg)',
        default=0.0,
        help='Kelapa Layak Produksi yang dimasukkan ke Machine Sheller.',
    )
    manual_sheller_input = fields.Float(
        string='Input Manual Sheller (Kg)',
        default=0.0,
        help='Kelapa Reject yang dimasukkan ke Manual Sheller.',
    )
    machine_sheller_output = fields.Float(
        string='Output Machine Sheller (Kg)',
        default=0.0,
    )
    manual_sheller_output = fields.Float(
        string='Output Manual Sheller (Kg)',
        default=0.0,
    )

    # computed
    total_sheller_input = fields.Float(
        string='Total Input Sheller (Kg)',
        compute='_compute_sheller_derived',
        store=False,
        readonly=True,
    )
    total_sheller_output = fields.Float(
        string='Total Output Sheller (Kg)',
        compute='_compute_sheller_derived',
        store=False,
        readonly=True,
    )
    remaining_layak = fields.Float(
        string='Sisa Kelapa Layak Produksi (Kg)',
        compute='_compute_sheller_derived',
        store=False,
        readonly=True,
        help='Kelapa Layak Produksi yang tersedia dikurangi Machine Sheller Input (dokumen ini).',
    )
    remaining_reject = fields.Float(
        string='Sisa Kelapa Reject (Kg)',
        compute='_compute_sheller_derived',
        store=False,
        readonly=True,
        help='Kelapa Reject yang tersedia dikurangi Manual Sheller Input (dokumen ini).',
    )

    # ═══════════════════════════════════════════════════════════
    # PARER
    # ═══════════════════════════════════════════════════════════

    available_kelapa_sheller = fields.Float(
        string='Kelapa Sheller Tersedia (Kg)',
        compute='_compute_available_sheller',
        store=False,
        readonly=True,
        help='Stok Kelapa Sheller yang tersedia di gudang saat ini.',
    )
    parer_input = fields.Float(
        string='Input Parer (Kg)',
        default=0.0,
        help='Kelapa Sheller yang dimasukkan ke proses Parer.',
    )
    parer_output = fields.Float(
        string='Output Parer / Kelapa Parer (Kg)',
        default=0.0,
    )
    remaining_kelapa_sheller = fields.Float(
        string='Sisa Kelapa Sheller (Kg)',
        compute='_compute_parer_derived',
        store=False,
        readonly=True,
        help='Kelapa Sheller tersedia dikurangi Parer Input (dokumen ini).',
    )
    parer_notes = fields.Text(string='Catatan Parer')

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
    # REFERENSI PERGERAKAN STOK
    # ═══════════════════════════════════════════════════════════

    # Sorting moves
    sort_raw_move_id = fields.Many2one(
        'stock.move', string='Move: Konsumsi Kelapa Bulat',
        readonly=True, copy=False,
    )
    sort_good_move_id = fields.Many2one(
        'stock.move', string='Move: Produksi Kelapa Layak',
        readonly=True, copy=False,
    )
    sort_reject_move_id = fields.Many2one(
        'stock.move', string='Move: Produksi Kelapa Reject',
        readonly=True, copy=False,
    )
    # Sheller moves
    shell_consume_layak_move_id = fields.Many2one(
        'stock.move', string='Move: Konsumsi Kelapa Layak (Machine)',
        readonly=True, copy=False,
    )
    shell_consume_reject_move_id = fields.Many2one(
        'stock.move', string='Move: Konsumsi Kelapa Reject (Manual)',
        readonly=True, copy=False,
    )
    shell_output_move_id = fields.Many2one(
        'stock.move', string='Move: Produksi Kelapa Sheller',
        readonly=True, copy=False,
    )
    # Parer moves
    parer_consume_move_id = fields.Many2one(
        'stock.move', string='Move: Konsumsi Kelapa Sheller',
        readonly=True, copy=False,
    )
    parer_output_move_id = fields.Many2one(
        'stock.move', string='Move: Produksi Kelapa Parer',
        readonly=True, copy=False,
    )

    # ═══════════════════════════════════════════════════════════
    # COMPUTED METHODS
    # ═══════════════════════════════════════════════════════════

    @api.depends('receipt_id', 'receipt_id.net_received_weight')
    def _compute_remaining_kelapa_bulat(self):
        """
        Remaining Kelapa Bulat for this receipt = net_received_weight
        minus sum of raw_coconut_processed from Done manufacturing records
        for the same receipt.
        """
        uom_kg = self.env.ref('uom.product_uom_kgm')
        for rec in self:
            if not rec.receipt_id:
                rec.remaining_kelapa_bulat = 0.0
                continue
            # Sum processed from done manufacturing docs (excluding current if not saved)
            done_mfg = self.search([
                ('receipt_id', '=', rec.receipt_id.id),
                ('state', '=', 'done'),
                ('id', '!=', rec.id if rec.id else 0),
            ])
            already_used = sum(done_mfg.mapped('raw_coconut_processed'))
            rec.remaining_kelapa_bulat = (
                rec.receipt_id.net_received_weight - already_used
            )

    @api.depends(
        'good_coconut_weight', 'reject_coconut_weight',
        'total_coconut_count', 'raw_coconut_processed',
        'remaining_kelapa_bulat',
    )
    def _compute_sorting_derived(self):
        for rec in self:
            if rec.total_coconut_count > 0 and rec.good_coconut_weight > 0:
                rec.kg_per_coconut = rec.good_coconut_weight / rec.total_coconut_count
            else:
                rec.kg_per_coconut = 0.0
            rec.remaining_unsorted = (
                rec.remaining_kelapa_bulat - rec.raw_coconut_processed
            )

    @api.depends(
        'machine_sheller_input', 'manual_sheller_input',
        'machine_sheller_output', 'manual_sheller_output',
    )
    def _compute_sheller_derived(self):
        uom_kg = self.env.ref('uom.product_uom_kgm')
        for rec in self:
            rec.total_sheller_input = (
                rec.machine_sheller_input + rec.manual_sheller_input
            )
            rec.total_sheller_output = (
                rec.machine_sheller_output + rec.manual_sheller_output
            )
            # Available Layak/Reject from stock minus this doc's planned input
            layak_stock = rec._get_stock_qty('coconut_receiving.product_kelapa_layak')
            reject_stock = rec._get_stock_qty('coconut_receiving.product_kelapa_reject')
            rec.remaining_layak = layak_stock - rec.machine_sheller_input
            rec.remaining_reject = reject_stock - rec.manual_sheller_input

    @api.depends('parer_input')
    def _compute_available_sheller(self):
        for rec in self:
            rec.available_kelapa_sheller = rec._get_stock_qty(
                'coconut_receiving.product_kelapa_sheller'
            )

    @api.depends('parer_input', 'available_kelapa_sheller')
    def _compute_parer_derived(self):
        for rec in self:
            rec.remaining_kelapa_sheller = (
                rec.available_kelapa_sheller - rec.parer_input
            )

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

    # ═══════════════════════════════════════════════════════════
    # WORKFLOW ACTIONS
    # ═══════════════════════════════════════════════════════════

    def action_confirm(self):
        for rec in self:
            if rec.state != 'draft':
                raise UserError(_(
                    "Hanya dokumen Draft yang dapat dikonfirmasi."
                ))
            if not rec.receipt_id:
                raise UserError(_(
                    "Pilih Penerimaan Kelapa sebelum mengkonfirmasi."
                ))
            if rec.receipt_id.state != 'done':
                raise UserError(_(
                    "Penerimaan Kelapa yang dipilih belum divalidasi. "
                    "Selesaikan proses penerimaan terlebih dahulu."
                ))
            rec.state = 'confirmed'

    def action_validate(self):
        """
        Validate the full manufacturing document.
        Creates stock moves for all three processes:
        1. Sorting: Kelapa Bulat → Layak + Reject
        2. Sheller: Layak+Reject → Kelapa Sheller
        3. Parer:   Kelapa Sheller → Kelapa Parer
        """
        for rec in self:
            if rec.state != 'confirmed':
                raise UserError(_(
                    "Hanya dokumen yang dikonfirmasi yang dapat divalidasi."
                ))
            # ── Idempotency guard (duplicate validation) ──
            if rec.sort_raw_move_id or rec.shell_output_move_id or rec.parer_output_move_id:
                raise UserError(_(
                    "Dokumen '%s' sudah divalidasi dan pergerakan stok sudah tercatat. "
                    "Tidak dapat membuat pergerakan stok duplikat."
                ) % rec.name)

            uom_kg = self.env.ref('uom.product_uom_kgm')

            # ── Resolve products ──
            p_bulat = rec._resolve_product('coconut_receiving.product_kelapa_bulat', 'Kelapa Bulat', uom_kg)
            p_layak = rec._resolve_product('coconut_receiving.product_kelapa_layak', 'Kelapa Layak Produksi', uom_kg)
            p_reject = rec._resolve_product('coconut_receiving.product_kelapa_reject', 'Kelapa Reject', uom_kg)
            p_sheller = rec._resolve_product('coconut_receiving.product_kelapa_sheller', 'Kelapa Sheller', uom_kg)
            p_parer = rec._resolve_product('coconut_receiving.product_kelapa_parer', 'Kelapa Parer', uom_kg)

            # ── Resolve locations ──
            loc_wh = rec._get_warehouse_location()
            loc_prod = rec._get_production_location()

            origin = f'{rec.name} / {rec.receipt_id.name}'

            # ── SECTION 1: SORTIR ──
            rec._validate_sorting(uom_kg, loc_wh, origin)
            sort_moves = rec._create_sorting_moves(
                p_bulat, p_layak, p_reject, loc_wh, loc_prod, uom_kg, origin
            )
            rec.sort_raw_move_id = sort_moves[0].id
            rec.sort_good_move_id = sort_moves[1].id
            rec.sort_reject_move_id = sort_moves[2].id

            # ── SECTION 2: SHELLER ──
            rec._validate_sheller(uom_kg, loc_wh)
            shell_moves = rec._create_sheller_moves(
                p_layak, p_reject, p_sheller, loc_wh, loc_prod, uom_kg, origin
            )
            if shell_moves:
                # shell_moves = [consume_layak?, consume_reject?, produce_sheller]
                if shell_moves.get('consume_layak'):
                    rec.shell_consume_layak_move_id = shell_moves['consume_layak'].id
                if shell_moves.get('consume_reject'):
                    rec.shell_consume_reject_move_id = shell_moves['consume_reject'].id
                if shell_moves.get('produce_sheller'):
                    rec.shell_output_move_id = shell_moves['produce_sheller'].id

            # ── SECTION 3: PARER ──
            rec._validate_parer(uom_kg, loc_wh)
            parer_moves = rec._create_parer_moves(
                p_sheller, p_parer, loc_wh, loc_prod, uom_kg, origin
            )
            if parer_moves:
                if parer_moves.get('consume_sheller'):
                    rec.parer_consume_move_id = parer_moves['consume_sheller'].id
                if parer_moves.get('produce_parer'):
                    rec.parer_output_move_id = parer_moves['produce_parer'].id

            rec.state = 'done'

    def action_cancel(self):
        for rec in self:
            if rec.state == 'done':
                raise UserError(_(
                    "Dokumen '%s' sudah selesai. Pergerakan stok yang sudah dicatat "
                    "tidak dapat dibatalkan secara otomatis. Hubungi administrator "
                    "untuk pembalikan stok manual."
                ) % rec.name)
            rec.state = 'cancelled'

    def action_reset_draft(self):
        for rec in self:
            if rec.state != 'cancelled':
                raise UserError(_(
                    "Hanya dokumen yang dibatalkan yang dapat dikembalikan ke Draft."
                ))
            rec.state = 'draft'

    # ═══════════════════════════════════════════════════════════
    # VALIDATION HELPERS
    # ═══════════════════════════════════════════════════════════

    def _validate_sorting(self, uom_kg, loc_wh, origin):
        """Validate all sorting section business rules."""
        rec = self
        if rec.raw_coconut_processed <= 0:
            raise UserError(_(
                "Kelapa Bulat Diproses harus lebih besar dari nol."
            ))
        if rec.good_coconut_weight < 0:
            raise UserError(_("Kelapa Layak Produksi tidak boleh negatif."))
        if rec.reject_coconut_weight < 0:
            raise UserError(_("Kelapa Reject tidak boleh negatif."))
        if rec.total_coconut_count < 0:
            raise UserError(_("Jumlah Kelapa tidak boleh negatif."))

        # good + reject must equal raw_coconut_processed
        total_out = rec.good_coconut_weight + rec.reject_coconut_weight
        diff = abs(round(total_out - rec.raw_coconut_processed, 4))
        if diff > _KG_ROUNDING:
            raise UserError(_(
                "Sortir: Kelapa Layak (%(good)s kg) + Kelapa Reject (%(reject)s kg) "
                "= %(total)s kg harus sama dengan Kelapa Bulat Diproses (%(raw)s kg).\n"
                "Selisih: %(diff)s kg."
            ) % {
                'good': rec.good_coconut_weight,
                'reject': rec.reject_coconut_weight,
                'total': total_out,
                'raw': rec.raw_coconut_processed,
                'diff': total_out - rec.raw_coconut_processed,
            })

        # Cannot exceed remaining Kelapa Bulat from this receipt
        remaining = rec.remaining_kelapa_bulat
        if float_compare(
            rec.raw_coconut_processed,
            remaining + _KG_ROUNDING,
            precision_rounding=uom_kg.rounding,
        ) > 0:
            raise UserError(_(
                "Sortir: Kelapa Bulat Diproses (%(proc)s kg) melebihi sisa "
                "Kelapa Bulat dari penerimaan %(receipt)s (%(rem)s kg)."
            ) % {
                'proc': rec.raw_coconut_processed,
                'receipt': rec.receipt_id.name,
                'rem': remaining,
            })

        # Check actual stock availability
        available = self._get_stock_qty('coconut_receiving.product_kelapa_bulat')
        if float_compare(
            available,
            rec.raw_coconut_processed,
            precision_rounding=uom_kg.rounding,
        ) < 0:
            raise UserError(_(
                "Sortir: Stok Kelapa Bulat tidak mencukupi.\n"
                "Tersedia: %(avail)s kg | Dibutuhkan: %(need)s kg"
            ) % {'avail': available, 'need': rec.raw_coconut_processed})

    def _validate_sheller(self, uom_kg, loc_wh):
        """Validate all sheller business rules."""
        rec = self
        if rec.machine_sheller_input < 0:
            raise UserError(_("Input Machine Sheller tidak boleh negatif."))
        if rec.manual_sheller_input < 0:
            raise UserError(_("Input Manual Sheller tidak boleh negatif."))
        if rec.machine_sheller_output < 0:
            raise UserError(_("Output Machine Sheller tidak boleh negatif."))
        if rec.manual_sheller_output < 0:
            raise UserError(_("Output Manual Sheller tidak boleh negatif."))

        if float_compare(
            rec.machine_sheller_output,
            rec.machine_sheller_input,
            precision_rounding=uom_kg.rounding,
        ) > 0:
            raise UserError(_(
                "Output Machine Sheller (%(out)s kg) tidak boleh melebihi "
                "Input Machine Sheller (%(inp)s kg)."
            ) % {'out': rec.machine_sheller_output, 'inp': rec.machine_sheller_input})

        if float_compare(
            rec.manual_sheller_output,
            rec.manual_sheller_input,
            precision_rounding=uom_kg.rounding,
        ) > 0:
            raise UserError(_(
                "Output Manual Sheller (%(out)s kg) tidak boleh melebihi "
                "Input Manual Sheller (%(inp)s kg)."
            ) % {'out': rec.manual_sheller_output, 'inp': rec.manual_sheller_input})

        # Check Kelapa Layak stock vs machine_sheller_input
        if not float_is_zero(rec.machine_sheller_input, precision_rounding=uom_kg.rounding):
            layak_avail = self._get_stock_qty('coconut_receiving.product_kelapa_layak')
            if float_compare(
                layak_avail,
                rec.machine_sheller_input,
                precision_rounding=uom_kg.rounding,
            ) < 0:
                raise UserError(_(
                    "Sheller: Stok Kelapa Layak Produksi tidak mencukupi untuk Machine Sheller.\n"
                    "Tersedia: %(avail)s kg | Dibutuhkan: %(need)s kg"
                ) % {'avail': layak_avail, 'need': rec.machine_sheller_input})

        # Check Kelapa Reject stock vs manual_sheller_input
        if not float_is_zero(rec.manual_sheller_input, precision_rounding=uom_kg.rounding):
            reject_avail = self._get_stock_qty('coconut_receiving.product_kelapa_reject')
            if float_compare(
                reject_avail,
                rec.manual_sheller_input,
                precision_rounding=uom_kg.rounding,
            ) < 0:
                raise UserError(_(
                    "Sheller: Stok Kelapa Reject tidak mencukupi untuk Manual Sheller.\n"
                    "Tersedia: %(avail)s kg | Dibutuhkan: %(need)s kg"
                ) % {'avail': reject_avail, 'need': rec.manual_sheller_input})

    def _validate_parer(self, uom_kg, loc_wh):
        """Validate parer business rules."""
        rec = self
        if rec.parer_input < 0:
            raise UserError(_("Input Parer tidak boleh negatif."))
        if rec.parer_output < 0:
            raise UserError(_("Output Parer tidak boleh negatif."))

        if float_compare(
            rec.parer_output,
            rec.parer_input,
            precision_rounding=uom_kg.rounding,
        ) > 0:
            raise UserError(_(
                "Output Parer (%(out)s kg) tidak boleh melebihi "
                "Input Parer (%(inp)s kg)."
            ) % {'out': rec.parer_output, 'inp': rec.parer_input})

        if not float_is_zero(rec.parer_input, precision_rounding=uom_kg.rounding):
            sheller_avail = self._get_stock_qty('coconut_receiving.product_kelapa_sheller')
            if float_compare(
                sheller_avail,
                rec.parer_input,
                precision_rounding=uom_kg.rounding,
            ) < 0:
                raise UserError(_(
                    "Parer: Stok Kelapa Sheller tidak mencukupi.\n"
                    "Tersedia: %(avail)s kg | Dibutuhkan: %(need)s kg\n\n"
                    "Input Parer sebesar %(inp)s kg tidak dapat diproses "
                    "karena hanya tersedia %(avail)s kg Kelapa Sheller."
                ) % {'avail': sheller_avail, 'need': rec.parer_input,
                     'inp': rec.parer_input})

    # ═══════════════════════════════════════════════════════════
    # STOCK MOVE CREATORS
    # ═══════════════════════════════════════════════════════════

    def _create_sorting_moves(self, p_bulat, p_layak, p_reject,
                              loc_wh, loc_prod, uom_kg, origin):
        """Create and complete 3 stock moves for the sorting section."""
        rec = self
        move_vals = [
            # Consume Kelapa Bulat (WH → Production)
            {
                'name': f'{origin} – Sortir: Konsumsi Kelapa Bulat',
                'origin': origin,
                'product_id': p_bulat.id,
                'product_uom_qty': rec.raw_coconut_processed,
                'product_uom': uom_kg.id,
                'location_id': loc_wh.id,
                'location_dest_id': loc_prod.id,
                'company_id': rec.company_id.id,
            },
            # Produce Kelapa Layak (Production → WH)
            {
                'name': f'{origin} – Sortir: Produksi Kelapa Layak',
                'origin': origin,
                'product_id': p_layak.id,
                'product_uom_qty': rec.good_coconut_weight,
                'product_uom': uom_kg.id,
                'location_id': loc_prod.id,
                'location_dest_id': loc_wh.id,
                'company_id': rec.company_id.id,
            },
            # Produce Kelapa Reject (Production → WH)
            {
                'name': f'{origin} – Sortir: Produksi Kelapa Reject',
                'origin': origin,
                'product_id': p_reject.id,
                'product_uom_qty': rec.reject_coconut_weight,
                'product_uom': uom_kg.id,
                'location_id': loc_prod.id,
                'location_dest_id': loc_wh.id,
                'company_id': rec.company_id.id,
            },
        ]
        moves = self.env['stock.move'].create(move_vals)
        moves._action_confirm()
        moves._action_assign()
        for move in moves:
            move.quantity = move.product_uom_qty
            move.picked = True
        moves._action_done()
        return moves

    def _create_sheller_moves(self, p_layak, p_reject, p_sheller,
                              loc_wh, loc_prod, uom_kg, origin):
        """Create stock moves for sheller section. Returns dict of moves."""
        rec = self
        result = {}
        moves_to_create = []
        move_keys = []

        if not float_is_zero(rec.machine_sheller_input, precision_rounding=uom_kg.rounding):
            moves_to_create.append({
                'name': f'{origin} – Sheller: Konsumsi Kelapa Layak (Machine)',
                'origin': origin,
                'product_id': p_layak.id,
                'product_uom_qty': rec.machine_sheller_input,
                'product_uom': uom_kg.id,
                'location_id': loc_wh.id,
                'location_dest_id': loc_prod.id,
                'company_id': rec.company_id.id,
            })
            move_keys.append('consume_layak')

        if not float_is_zero(rec.manual_sheller_input, precision_rounding=uom_kg.rounding):
            moves_to_create.append({
                'name': f'{origin} – Sheller: Konsumsi Kelapa Reject (Manual)',
                'origin': origin,
                'product_id': p_reject.id,
                'product_uom_qty': rec.manual_sheller_input,
                'product_uom': uom_kg.id,
                'location_id': loc_wh.id,
                'location_dest_id': loc_prod.id,
                'company_id': rec.company_id.id,
            })
            move_keys.append('consume_reject')

        total_sheller_out = rec.machine_sheller_output + rec.manual_sheller_output
        if not float_is_zero(total_sheller_out, precision_rounding=uom_kg.rounding):
            moves_to_create.append({
                'name': f'{origin} – Sheller: Produksi Kelapa Sheller',
                'origin': origin,
                'product_id': p_sheller.id,
                'product_uom_qty': total_sheller_out,
                'product_uom': uom_kg.id,
                'location_id': loc_prod.id,
                'location_dest_id': loc_wh.id,
                'company_id': rec.company_id.id,
            })
            move_keys.append('produce_sheller')

        if moves_to_create:
            moves = self.env['stock.move'].create(moves_to_create)
            moves._action_confirm()
            moves._action_assign()
            for move in moves:
                move.quantity = move.product_uom_qty
                move.picked = True
            moves._action_done()
            for key, move in zip(move_keys, moves):
                result[key] = move

        return result

    def _create_parer_moves(self, p_sheller, p_parer,
                            loc_wh, loc_prod, uom_kg, origin):
        """Create stock moves for parer section. Returns dict of moves."""
        rec = self
        result = {}

        if float_is_zero(rec.parer_input, precision_rounding=uom_kg.rounding):
            return result

        moves_to_create = [
            # Consume Kelapa Sheller (WH → Production)
            {
                'name': f'{origin} – Parer: Konsumsi Kelapa Sheller',
                'origin': origin,
                'product_id': p_sheller.id,
                'product_uom_qty': rec.parer_input,
                'product_uom': uom_kg.id,
                'location_id': loc_wh.id,
                'location_dest_id': loc_prod.id,
                'company_id': rec.company_id.id,
            },
        ]
        move_keys = ['consume_sheller']

        if not float_is_zero(rec.parer_output, precision_rounding=uom_kg.rounding):
            moves_to_create.append({
                'name': f'{origin} – Parer: Produksi Kelapa Parer',
                'origin': origin,
                'product_id': p_parer.id,
                'product_uom_qty': rec.parer_output,
                'product_uom': uom_kg.id,
                'location_id': loc_prod.id,
                'location_dest_id': loc_wh.id,
                'company_id': rec.company_id.id,
            })
            move_keys.append('produce_parer')

        moves = self.env['stock.move'].create(moves_to_create)
        moves._action_confirm()
        moves._action_assign()
        for move in moves:
            move.quantity = move.product_uom_qty
            move.picked = True
        moves._action_done()
        for key, move in zip(move_keys, moves):
            result[key] = move

        return result

    # ═══════════════════════════════════════════════════════════
    # LOCATION & PRODUCT HELPERS
    # ═══════════════════════════════════════════════════════════

    def _get_warehouse_location(self):
        """Return the main internal stock location for this company."""
        warehouse = self.env['stock.warehouse'].search(
            [('company_id', '=', self.company_id.id)], limit=1,
        )
        loc = warehouse.lot_stock_id if warehouse else False
        if not loc:
            loc = self.env['stock.location'].search(
                [('usage', '=', 'internal'),
                 ('company_id', '=', self.company_id.id)],
                limit=1,
            )
        if not loc:
            raise UserError(_(
                "Lokasi stok internal (Gudang) tidak ditemukan untuk perusahaan ini."
            ))
        return loc

    def _get_production_location(self):
        """Return the virtual production location for manufacturing."""
        loc = self.env.ref(
            'coconut_sorting.stock_location_coconut_manufacturing',
            raise_if_not_found=False,
        )
        if not loc:
            # Fallback to any production location
            loc = self.env['stock.location'].search(
                [('usage', '=', 'production')], limit=1,
            )
        if not loc:
            raise UserError(_(
                "Lokasi produksi virtual tidak ditemukan. "
                "Pastikan modul coconut_sorting terinstal dengan benar."
            ))
        return loc

    def _resolve_product(self, xml_id, label, uom_kg):
        """Resolve product variant by XML ID with UoM validation."""
        tmpl = self.env.ref(xml_id, raise_if_not_found=False)
        if not tmpl:
            raise UserError(_(
                "Produk '%(label)s' (XML ID: %(xml_id)s) tidak ditemukan. "
                "Harap perbarui modul coconut_receiving."
            ) % {'label': label, 'xml_id': xml_id})
        variant = tmpl.product_variant_ids[:1]
        if not variant:
            raise UserError(_(
                "Varian produk '%(label)s' tidak ditemukan. "
                "Pastikan produk memiliki varian yang aktif."
            ) % {'label': label})
        if variant.uom_id.category_id != uom_kg.category_id:
            raise UserError(_(
                "Produk '%(name)s' menggunakan satuan '%(uom)s' yang bukan kategori Berat. "
                "Silakan ubah satuan produk menjadi kg sebelum melanjutkan.\n\n"
                "Contoh pesan: 'Product %(name)s must use kg from the Weight UoM category.'"
            ) % {'name': variant.name, 'uom': variant.uom_id.name})
        return variant

    def _get_stock_qty(self, xml_id):
        """Get available quantity for a product identified by XML ID."""
        try:
            tmpl = self.env.ref(xml_id, raise_if_not_found=False)
            if not tmpl:
                return 0.0
            variant = tmpl.product_variant_ids[:1]
            if not variant:
                return 0.0
            loc_wh = self._get_warehouse_location()
            return self.env['stock.quant']._get_available_quantity(
                variant, loc_wh,
            )
        except Exception:
            return 0.0
