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
    Pemakaian Kelapa Produksi – dokumen yang mencakup:
      1. Sheller Mesin  (Kelapa Layak → Kelapa Sheller)
      2. Sheller Manual (Kelapa Reject → Kelapa Sheller)
      3. Parer          (Kelapa Sheller → Kelapa Parer)

    Proses Sortir Kelapa dilakukan di modul terpisah (coconut.sorting).
    Pergerakan stok direkam melalui stock.move standar Odoo.
    """
    _name = 'coconut.manufacturing'
    _description = 'Pemakaian Kelapa Produksi'
    _order = 'production_date desc, name desc'
    _inherit = ['mail.thread', 'mail.activity.mixin']

    # ═══════════════════════════════════════════════════════════
    # IDENTIFIKASI
    # ═══════════════════════════════════════════════════════════

    name = fields.Char(
        string='Kode Pemakaian',
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
        string='Operator / Karyawan',
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
    # SUMBER PENERIMAAN (Opsional – hanya untuk tracing)
    # ═══════════════════════════════════════════════════════════

    receipt_id = fields.Many2one(
        'coconut.receipt',
        string='Penerimaan Kelapa (Opsional)',
        required=False,
        ondelete='restrict',
        domain=[('state', '=', 'done')],
        tracking=True,
        help='Opsional. Pilih penerimaan untuk keperluan tracing.',
    )

    # Initial Stock stored fields (snapshot saat validasi)
    initial_stock_layak = fields.Float(string='Stok Awal Layak (Kg)', readonly=True, copy=False)
    initial_stock_reject = fields.Float(string='Stok Awal Reject (Kg)', readonly=True, copy=False)
    initial_stock_sheller = fields.Float(string='Stok Awal Sheller (Kg)', readonly=True, copy=False)
    initial_stock_parer = fields.Float(string='Stok Awal Parer (Kg)', readonly=True, copy=False)

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

    # ═══════════════════════════════════════════════════════════
    # SHELLER
    # ═══════════════════════════════════════════════════════════

    machine_sheller_input = fields.Float(
        string='Kelapa Layak Produksi Digunakan (Kg)',
        default=0.0,
        help='Kelapa Layak Produksi yang dimasukkan ke Machine Sheller.',
    )
    manual_sheller_input = fields.Float(
        string='Kelapa Reject Digunakan (Kg)',
        default=0.0,
        help='Kelapa Reject yang dimasukkan ke Manual Sheller.',
    )
    machine_sheller_output = fields.Float(
        string='Output Machine Sheller / Kelapa Sheller (Kg)',
        default=0.0,
    )
    manual_sheller_output = fields.Float(
        string='Output Manual Sheller / Kelapa Sheller (Kg)',
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
        string='Total Output Kelapa Sheller (Kg)',
        compute='_compute_sheller_derived',
        store=False,
        readonly=True,
    )
    remaining_layak = fields.Float(
        string='Sisa Kelapa Layak Setelah Proses Ini (Kg)',
        compute='_compute_sheller_derived',
        store=False,
        readonly=True,
        help='Kelapa Layak Produksi yang tersedia dikurangi Machine Sheller Input (dokumen ini).',
    )
    remaining_reject = fields.Float(
        string='Sisa Kelapa Reject Setelah Proses Ini (Kg)',
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
        string='Kelapa Sheller Digunakan / Input Parer (Kg)',
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

    @api.depends('machine_sheller_output', 'manual_sheller_output', 'state')
    def _compute_available_sheller(self):
        for rec in self:
            if rec.state == 'done':
                rec.available_kelapa_sheller = rec.initial_stock_sheller + rec.machine_sheller_output + rec.manual_sheller_output
            else:
                existing = rec._get_stock_qty('coconut_receiving.product_kelapa_sheller')
                rec.available_kelapa_sheller = existing + rec.machine_sheller_output + rec.manual_sheller_output

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

    def write(self, vals):
        for rec in self:
            if rec.state == 'done':
                # Allow chatter, activities, and workflow state updates, but block other edits
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
                raise UserError(_(
                    "Hanya dokumen Draft yang dapat dikonfirmasi."
                ))
            if rec.receipt_id and rec.receipt_id.state != 'done':
                raise UserError(_(
                    "Penerimaan Kelapa yang dipilih belum divalidasi. "
                    "Selesaikan proses penerimaan terlebih dahulu."
                ))
            rec.state = 'confirmed'

    def action_validate(self):
        """
        Validasi dokumen Pemakaian Kelapa Produksi.
        Mencakup proses Sheller (Machine + Manual) dan Parer.
        """
        for rec in self:
            if rec.state != 'confirmed':
                raise UserError(_(
                    "Hanya dokumen yang dikonfirmasi yang dapat divalidasi."
                ))
            # ── Idempotency guard ──
            if rec.shell_output_move_id or rec.parer_output_move_id:
                raise UserError(_(
                    "Dokumen '%s' sudah divalidasi dan pergerakan stok sudah tercatat. "
                    "Tidak dapat membuat pergerakan stok duplikat."
                ) % rec.name)

            uom_kg = self.env.ref('uom.product_uom_kgm')

            # Store initial stock levels before stock movements
            rec.write({
                'initial_stock_layak': rec._get_stock_qty('coconut_receiving.product_kelapa_layak'),
                'initial_stock_reject': rec._get_stock_qty('coconut_receiving.product_kelapa_reject'),
                'initial_stock_sheller': rec._get_stock_qty('coconut_receiving.product_kelapa_sheller'),
                'initial_stock_parer': rec._get_stock_qty('coconut_receiving.product_kelapa_parer'),
            })

            # ── Resolve products ──
            p_layak = rec._resolve_product('coconut_receiving.product_kelapa_layak', 'Kelapa Layak Produksi', uom_kg)
            p_reject = rec._resolve_product('coconut_receiving.product_kelapa_reject', 'Kelapa Reject', uom_kg)
            p_sheller = rec._resolve_product('coconut_receiving.product_kelapa_sheller', 'Kelapa Sheller', uom_kg)
            p_parer = rec._resolve_product('coconut_receiving.product_kelapa_parer', 'Kelapa Parer', uom_kg)

            # ── Resolve locations ──
            loc_wh = rec._get_warehouse_location()
            loc_prod = rec._get_production_location()

            origin = f'{rec.name}' + (f' / {rec.receipt_id.name}' if rec.receipt_id else '')

            # ── SHELLER ──
            rec._validate_sheller(uom_kg, loc_wh)
            shell_moves = rec._create_sheller_moves(
                p_layak, p_reject, p_sheller, loc_wh, loc_prod, uom_kg, origin
            )
            if shell_moves:
                if shell_moves.get('consume_layak'):
                    rec.shell_consume_layak_move_id = shell_moves['consume_layak'].id
                if shell_moves.get('consume_reject'):
                    rec.shell_consume_reject_move_id = shell_moves['consume_reject'].id
                if shell_moves.get('produce_sheller'):
                    rec.shell_output_move_id = shell_moves['produce_sheller'].id

            # ── PARER ──
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
                    "Tersedia: %(avail)s kg | Dibutuhkan: %(need)s kg"
                ) % {'avail': sheller_avail, 'need': rec.parer_input})

    # ═══════════════════════════════════════════════════════════
    # STOCK MOVE CREATORS
    # ═══════════════════════════════════════════════════════════

    def _create_sheller_moves(self, p_layak, p_reject, p_sheller,
                              loc_wh, loc_prod, uom_kg, origin):
        """Create stock moves for sheller section. Returns dict of moves."""
        rec = self
        result = {}
        moves_to_create = []
        move_keys = []

        if not float_is_zero(rec.machine_sheller_input, precision_rounding=uom_kg.rounding):
            moves_to_create.append({
                'name': f'{origin} – Sheller Mesin: Konsumsi Kelapa Layak',
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
                'name': f'{origin} – Sheller Manual: Konsumsi Kelapa Reject',
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
                'name': f'{origin} – Produksi Kelapa Sheller',
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
                "Silakan ubah satuan produk menjadi kg sebelum melanjutkan."
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

    def get_report_stock_data(self):
        """Returns dictionary of stock data for the report."""
        # Determine Awal based on state
        if self.state == 'done':
            awal_layak = self.initial_stock_layak
            awal_reject = self.initial_stock_reject
            awal_sheller = self.initial_stock_sheller
            awal_parer = self.initial_stock_parer
        else:
            awal_layak = self._get_stock_qty('coconut_receiving.product_kelapa_layak')
            awal_reject = self._get_stock_qty('coconut_receiving.product_kelapa_reject')
            awal_sheller = self._get_stock_qty('coconut_receiving.product_kelapa_sheller')
            awal_parer = self._get_stock_qty('coconut_receiving.product_kelapa_parer')

        # Pemakaian / Produced
        used_layak = self.machine_sheller_input
        used_reject = self.manual_sheller_input
        used_sheller = self.parer_input

        produced_sheller = self.machine_sheller_output + self.manual_sheller_output
        produced_parer = self.parer_output

        # Akhir
        akhir_layak = awal_layak - used_layak
        akhir_reject = awal_reject - used_reject
        akhir_sheller = awal_sheller + produced_sheller - used_sheller
        akhir_parer = awal_parer + produced_parer

        return {
            'layak': {'awal': awal_layak, 'used': used_layak, 'akhir': akhir_layak},
            'reject': {'awal': awal_reject, 'used': used_reject, 'akhir': akhir_reject},
            'sheller': {'awal': awal_sheller, 'used': used_sheller, 'akhir': akhir_sheller, 'produced': produced_sheller},
            'parer': {'awal': awal_parer, 'used': 0.0, 'akhir': akhir_parer, 'produced': produced_parer},
        }

    def format_kg(self, value):
        """Helper to format weight in Indonesian style: 20.000 Kg"""
        return "{:,.0f} Kg".format(value).replace(',', '.')

    def format_kg_raw(self, value):
        """Helper to format weight in Indonesian style without Kg suffix: 20000 -> 20.000"""
        return "{:,.0f}".format(value).replace(',', '.')
