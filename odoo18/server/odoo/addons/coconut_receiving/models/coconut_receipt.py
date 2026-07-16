# -*- coding: utf-8 -*-
from odoo import api, fields, models, _
from odoo.exceptions import UserError, ValidationError
from odoo.tools.float_utils import float_compare, float_is_zero


class CoconutReceipt(models.Model):
    _name = 'coconut.receipt'
    _description = 'Penerimaan Kelapa'
    _order = 'entry_datetime desc, id desc'
    _inherit = ['mail.thread', 'mail.activity.mixin']

    # ═══════════════════════════════════════════════════════════
    # A. INFORMASI TIMBANGAN (Weighbridge Information)
    # ═══════════════════════════════════════════════════════════

    name = fields.Char(
        string='Kode Penerimaan',
        required=True, copy=False, readonly=True,
        default=lambda self: _('Baru'),
    )
    entry_datetime = fields.Datetime(
        string='Tanggal & Waktu Masuk',
        default=fields.Datetime.now, required=True,
        tracking=True,
    )
    exit_datetime = fields.Datetime(
        string='Tanggal & Waktu Keluar',
        tracking=True,
    )
    partner_id = fields.Many2one(
        'res.partner',
        string='Pemasok',
        required=True,
        tracking=True,
    )
    origin = fields.Char(
        string='Asal Kelapa',
        tracking=True,
    )
    driver_name = fields.Char(string='Nama Supir')
    driver_phone = fields.Char(string='Nomor Telepon Supir')
    vehicle_plate = fields.Char(
        string='Nomor Polisi Kendaraan',
        tracking=True,
    )
    item_name = fields.Char(
        string='Nama Barang',
        default='Kelapa Bulat',
        required=True,
    )
    reference_number = fields.Char(string='Nomor Referensi')
    npwp = fields.Char(string='NPWP', help='Nomor Pokok Wajib Pajak (opsional).')
    pphd2 = fields.Char(string='PPHD2', help='Opsional.')

    # ── Timbangan ──
    gross_vehicle_weight = fields.Float(
        string='Berat Kotor Kendaraan (Kg)',
        help='Berat total kendaraan beserta kelapa (bruto).',
        required=True,
        tracking=True,
    )
    tare_vehicle_weight = fields.Float(
        string='Berat Tara Kendaraan (Kg)',
        help='Berat kendaraan kosong.',
        required=True,
        tracking=True,
    )
    pot_weight = fields.Float(
        string='Berat Wadah/Pot (Kg)',
        default=0.0,
        help='Berat wadah atau kontainer (opsional, default 0).',
    )
    net_received_weight = fields.Float(
        string='Berat Bersih Diterima (Kg)',
        compute='_compute_net_received_weight',
        store=True,
        readonly=True,
        help='Berat kelapa yang diterima = Bruto - Tara - Wadah.',
        tracking=True,
    )

    # ── Legacy backward-compat (hidden – do NOT remove; existing DB records use them) ──
    # These are kept invisible in views and not used in new business logic.
    net_weight = fields.Float(
        string='[Legacy] Berat Bersih Lama (Kg)',
        default=0.0,
        help='Field lama, disimpan untuk kompatibilitas data historis. Tidak digunakan lagi.',
    )
    purchase_id = fields.Many2one(
        'purchase.order',
        string='[Legacy] Purchase Order',
        help='Field lama, tidak digunakan dalam proses baru.',
    )
    partner_ref = fields.Char(
        string='[Legacy] Nama Perusahaan Pemasok',
        related='partner_id.name',
    )
    machine_shelling_weight = fields.Float(
        string='[Legacy] Berat Kelapa Layak (Kg)',
        default=0.0,
    )
    manual_shelling_weight = fields.Float(
        string='[Legacy] Berat Kelapa Reject (Kg)',
        default=0.0,
    )
    total_sorting_weight = fields.Float(
        string='[Legacy] Total Berat Tersortir (Kg)',
        compute='_compute_total_sorting',
        store=True,
        readonly=True,
    )
    # legacy receipt date alias
    date_receipt = fields.Datetime(
        string='[Legacy] Tanggal Penerimaan',
        related='entry_datetime',
        store=True,
    )

    # ═══════════════════════════════════════════════════════════
    # B. PENILAIAN KUALITAS (Quality Assessment – informational only)
    # ═══════════════════════════════════════════════════════════

    total_count = fields.Integer(
        string='Total Jumlah Kelapa (Butir)',
        default=0,
        help='Jumlah buah kelapa yang diterima.',
    )
    quality_grade = fields.Selection([
        ('excellent', 'Sangat Baik'),
        ('good', 'Baik'),
        ('average', 'Rata-rata'),
        ('poor', 'Buruk'),
    ], string='Nilai Kualitas', default='average')
    avg_quality = fields.Float(
        string='Rata-rata Kualitas',
        help='Skor rata-rata kualitas kelapa (informasi saja).',
        default=0.0,
    )
    quality_notes = fields.Text(string='Catatan Kualitas')

    # computed kg/butir for reporting
    avg_weight_per_coconut = fields.Float(
        string='KG per Butir',
        compute='_compute_avg_weight_per_coconut',
        store=True,
        readonly=True,
    )

    # ── Legacy reject breakdown (kept for historical data) ──
    reject_pecah = fields.Float(string='Kelapa Pecah (Kg)', default=0.0)
    reject_kecil = fields.Float(string='Kelapa Kecil (Kg)', default=0.0)
    reject_tunas = fields.Float(string='Kelapa Tunas (Kg)', default=0.0)
    reject_busuk = fields.Float(string='Kelapa Busuk (Kg)', default=0.0)
    reject_muda = fields.Float(string='Kelapa Muda (Kg)', default=0.0)
    total_reject = fields.Float(
        string='Total Sortiran Reject (Kg)',
        compute='_compute_legacy_reject',
        store=True,
    )
    gross_weight = fields.Float(
        string='[Legacy] Berat Kotor Historis (Kg)',
        compute='_compute_legacy_reject',
        store=True,
    )

    # ═══════════════════════════════════════════════════════════
    # C. DETAIL PENERIMAAN
    # ═══════════════════════════════════════════════════════════

    receiving_employee_id = fields.Many2one(
        'hr.employee',
        string='Karyawan Penerima',
        default=lambda self: self.env.user.employee_id,
    )
    administrator_id = fields.Many2one(
        'hr.employee',
        string='Administrator',
    )
    receiving_time = fields.Datetime(
        string='Waktu Validasi',
        readonly=True,
    )
    notes = fields.Text(string='Catatan Umum')

    # ═══════════════════════════════════════════════════════════
    # D. LAMPIRAN
    # ═══════════════════════════════════════════════════════════

    attachment_delivery = fields.Binary(
        string='Lampiran Surat Jalan',
        attachment=True,
    )
    attachment_delivery_name = fields.Char(
        string='Nama File Surat Jalan',
        default='surat_jalan.pdf',
    )
    attachment_weighing = fields.Binary(
        string='Lampiran Slip Timbangan',
        attachment=True,
    )
    attachment_weighing_name = fields.Char(
        string='Nama File Slip Timbangan',
        default='slip_timbangan.pdf',
    )
    attachment_additional = fields.Binary(
        string='Lampiran Tambahan',
        attachment=True,
    )
    attachment_additional_name = fields.Char(
        string='Nama File Lampiran Tambahan',
        default='lampiran_tambahan.pdf',
    )

    # ═══════════════════════════════════════════════════════════
    # WORKFLOW
    # ═══════════════════════════════════════════════════════════

    state = fields.Selection([
        ('draft', 'Draft'),
        ('done', 'Selesai'),
        ('cancelled', 'Dibatalkan'),
    ], string='Status', default='draft', required=True, tracking=True)

    # ═══════════════════════════════════════════════════════════
    # REFERENSI PERSEDIAAN
    # ═══════════════════════════════════════════════════════════

    picking_id = fields.Many2one(
        'stock.picking',
        string='Penerimaan Stok (Picking)',
        readonly=True, copy=False,
    )
    move_ids = fields.One2many(
        'stock.move',
        related='picking_id.move_ids_without_package',
        string='Pergerakan Stok',
        readonly=True,
    )

    company_id = fields.Many2one(
        'res.company',
        string='Perusahaan',
        required=True,
        default=lambda self: self.env.company,
    )

    # ═══════════════════════════════════════════════════════════
    # BACKWARD COMPAT: fields referenced by coconut_sorting extension
    # remaining_unsorted_weight is added by coconut_sorting via _inherit
    # ═══════════════════════════════════════════════════════════

    # ═══════════════════════════════════════════════════════════
    # COMPUTED METHODS
    # ═══════════════════════════════════════════════════════════

    @api.depends('gross_vehicle_weight', 'tare_vehicle_weight', 'pot_weight')
    def _compute_net_received_weight(self):
        for rec in self:
            rec.net_received_weight = (
                rec.gross_vehicle_weight
                - rec.tare_vehicle_weight
                - rec.pot_weight
            )

    @api.depends('net_received_weight', 'total_count')
    def _compute_avg_weight_per_coconut(self):
        for rec in self:
            if rec.total_count > 0:
                rec.avg_weight_per_coconut = rec.net_received_weight / rec.total_count
            else:
                rec.avg_weight_per_coconut = 0.0

    @api.depends(
        'net_received_weight',
        'reject_pecah', 'reject_kecil',
        'reject_tunas', 'reject_busuk', 'reject_muda',
    )
    def _compute_legacy_reject(self):
        for rec in self:
            rec.total_reject = (
                rec.reject_pecah + rec.reject_kecil
                + rec.reject_tunas + rec.reject_busuk + rec.reject_muda
            )
            # gross_weight for legacy field (stored for historical reports)
            rec.gross_weight = rec.net_received_weight + rec.total_reject

    @api.depends('machine_shelling_weight', 'manual_shelling_weight')
    def _compute_total_sorting(self):
        for rec in self:
            rec.total_sorting_weight = (
                rec.machine_shelling_weight + rec.manual_shelling_weight
            )

    # ═══════════════════════════════════════════════════════════
    # CONSTRAINTS
    # ═══════════════════════════════════════════════════════════

    @api.constrains(
        'gross_vehicle_weight', 'tare_vehicle_weight',
        'pot_weight', 'net_received_weight',
        'exit_datetime', 'entry_datetime',
    )
    def _check_weighbridge_fields(self):
        for rec in self:
            # Skip validation for legacy records that haven't set weighbridge fields yet.
            # The constraint is enforced at action_validate time for business rules.
            # Here we only block clearly invalid inputs when the user is actively editing.
            if rec.gross_vehicle_weight == 0.0 and rec.tare_vehicle_weight == 0.0:
                # Legacy or blank record – skip automatic constraint.
                # Full validation will happen in action_validate.
                continue

            if rec.tare_vehicle_weight < 0:
                raise ValidationError(_(
                    "Berat Tara Kendaraan tidak boleh negatif."
                ))
            if rec.pot_weight < 0:
                raise ValidationError(_(
                    "Berat Wadah tidak boleh negatif."
                ))
            if rec.gross_vehicle_weight <= (rec.tare_vehicle_weight + rec.pot_weight):
                raise ValidationError(_(
                    "Berat Kotor Kendaraan (%(gross)s kg) harus lebih besar dari "
                    "Tara + Wadah (%(sum)s kg)."
                ) % {
                    'gross': rec.gross_vehicle_weight,
                    'sum': rec.tare_vehicle_weight + rec.pot_weight,
                })
            if rec.exit_datetime and rec.entry_datetime:
                if rec.exit_datetime < rec.entry_datetime:
                    raise ValidationError(_(
                        "Waktu Keluar tidak boleh lebih awal dari Waktu Masuk."
                    ))

    # ═══════════════════════════════════════════════════════════
    # ORM OVERRIDES
    # ═══════════════════════════════════════════════════════════

    @api.model_create_multi
    def create(self, vals_list):
        for vals in vals_list:
            if vals.get('name', _('Baru')) in (_('Baru'), _('New'), 'Baru', 'New'):
                vals['name'] = (
                    self.env['ir.sequence'].next_by_code('coconut.receipt.seq')
                    or _('Baru')
                )
        return super().create(vals_list)

    # ═══════════════════════════════════════════════════════════
    # WORKFLOW ACTIONS
    # ═══════════════════════════════════════════════════════════

    def action_validate(self):
        """
        Validate the receiving document:
        1. Ensure state is draft.
        2. Block duplicate validation.
        3. Validate UoM of Kelapa Bulat product.
        4. Create one inbound stock picking for net_received_weight of Kelapa Bulat.
        5. Confirm & validate the picking immediately.
        6. Set state to 'done'.
        """
        for rec in self:
            # ── State guard ──
            if rec.state != 'draft':
                raise UserError(_(
                    "Hanya dokumen Draft yang dapat divalidasi. "
                    "Status saat ini: %s"
                ) % rec.state)

            # ── Duplicate guard ──
            if rec.picking_id and rec.picking_id.state == 'done':
                raise UserError(_(
                    "Dokumen '%s' sudah divalidasi dan pergerakan stok sudah dicatat. "
                    "Tidak dapat membuat pergerakan stok duplikat."
                ) % rec.name)

            # ── Weight guard ──
            if rec.net_received_weight <= 0:
                raise UserError(_(
                    "Berat Bersih Diterima harus lebih besar dari nol sebelum validasi."
                ))

            # ── Resolve Kelapa Bulat product ──
            uom_kg = self.env.ref('uom.product_uom_kgm')
            product_bulat = self._get_coconut_product(
                'coconut_receiving.product_kelapa_bulat',
                'Kelapa Bulat',
                uom_kg,
            )

            # ── Resolve picking type (incoming) ──
            picking_type = self.env['stock.picking.type'].search([
                ('code', '=', 'incoming'),
                ('company_id', '=', rec.company_id.id),
            ], limit=1)
            if not picking_type:
                raise UserError(_(
                    "Tipe operasi penerimaan barang (Incoming) tidak ditemukan "
                    "untuk perusahaan ini."
                ))

            location_dest = picking_type.default_location_dest_id
            if not location_dest:
                raise UserError(_(
                    "Lokasi tujuan default tidak ditemukan pada tipe operasi penerimaan."
                ))

            # ── Resolve supplier location ──
            location_src = self.env.ref(
                'stock.stock_location_suppliers', raise_if_not_found=False,
            )
            if not location_src:
                location_src = self.env['stock.location'].search(
                    [('usage', '=', 'supplier')], limit=1,
                )
            if not location_src:
                raise UserError(_("Lokasi Pemasok (Supplier) tidak ditemukan dalam sistem."))

            # ── Create picking ──
            picking = self.env['stock.picking'].create({
                'partner_id': rec.partner_id.id,
                'picking_type_id': picking_type.id,
                'location_id': location_src.id,
                'location_dest_id': location_dest.id,
                'origin': rec.name,
                'company_id': rec.company_id.id,
            })

            # ── Create move: Supplier → WH Stock for net_received_weight ──
            self.env['stock.move'].create({
                'name': _('%(receipt)s – Penerimaan %(product)s') % {
                    'receipt': rec.name,
                    'product': product_bulat.name,
                },
                'product_id': product_bulat.id,
                'product_uom_qty': rec.net_received_weight,
                'product_uom': product_bulat.uom_id.id,
                'picking_id': picking.id,
                'location_id': location_src.id,
                'location_dest_id': location_dest.id,
                'company_id': rec.company_id.id,
                'origin': rec.name,
            })

            # ── Confirm and immediately validate ──
            picking.action_confirm()
            for move in picking.move_ids:
                move.quantity = move.product_uom_qty
                move.picked = True
            picking.button_validate()

            # ── Finalise record ──
            rec.picking_id = picking.id
            rec.receiving_time = fields.Datetime.now()
            rec.state = 'done'

    def action_cancel(self):
        for rec in self:
            if rec.state == 'done':
                raise UserError(_(
                    "Dokumen '%s' sudah divalidasi. Untuk membatalkan, "
                    "kembalikan pergerakan stok terkait terlebih dahulu."
                ) % rec.name)
            if rec.picking_id and rec.picking_id.state not in ('draft', 'cancel'):
                raise UserError(_(
                    "Tidak dapat membatalkan penerimaan karena pengambilan stok "
                    "terkait sudah diproses. Batalkan picking terlebih dahulu."
                ))
            if rec.picking_id:
                rec.picking_id.action_cancel()
            rec.state = 'cancelled'

    def action_reset_draft(self):
        for rec in self:
            if rec.state != 'cancelled':
                raise UserError(_(
                    "Hanya dokumen yang dibatalkan yang dapat dikembalikan ke Draft."
                ))
            if rec.picking_id and rec.picking_id.state not in ('draft', 'cancel'):
                raise UserError(_(
                    "Tidak dapat mengembalikan ke draft karena picking terkait "
                    "sudah diproses."
                ))
            rec.state = 'draft'

    # ── Legacy workflow aliases (kept so old button references don't break) ──
    def action_start_inspection(self):
        """Legacy alias – direct to validate."""
        return self.action_validate()

    def action_approve(self):
        """Legacy alias – no-op in new flow."""
        raise UserError(_("Proses inspeksi dan persetujuan tidak lagi digunakan. "
                          "Gunakan tombol 'Validasi' langsung dari status Draft."))

    def action_receive(self):
        """Legacy alias – direct to validate."""
        return self.action_validate()

    # ═══════════════════════════════════════════════════════════
    # HELPERS
    # ═══════════════════════════════════════════════════════════

    def _get_coconut_product(self, xml_id, label, uom_kg):
        """
        Resolve a product template by XML ID.
        Returns the first product variant.
        Raises UserError if not found or UoM category mismatch.
        """
        self.ensure_one()
        tmpl = self.env.ref(xml_id, raise_if_not_found=False)
        if not tmpl:
            raise UserError(_(
                "Produk '%(label)s' (XML ID: %(xml_id)s) tidak ditemukan. "
                "Harap perbarui modul coconut_receiving."
            ) % {'label': label, 'xml_id': xml_id})
        variant = tmpl.product_variant_ids[:1]
        if not variant:
            raise UserError(_(
                "Varian produk untuk '%(label)s' tidak ditemukan. "
                "Pastikan produk memiliki varian yang aktif."
            ) % {'label': label})
        if variant.uom_id.category_id != uom_kg.category_id:
            raise UserError(_(
                "Produk '%(name)s' menggunakan satuan '%(uom)s' yang bukan kategori Berat. "
                "Silakan ubah satuan produk menjadi kg sebelum melanjutkan."
            ) % {'name': variant.name, 'uom': variant.uom_id.name})
        return variant
