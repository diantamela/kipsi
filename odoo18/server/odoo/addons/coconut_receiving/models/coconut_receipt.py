# -*- coding: utf-8 -*-
from odoo import api, fields, models, _
from odoo.exceptions import UserError, ValidationError


class CoconutReceipt(models.Model):
    _name = 'coconut.receipt'
    _description = 'Penerimaan Kelapa'
    _order = 'date_receipt desc, id desc'
    _inherit = ['mail.thread', 'mail.activity.mixin']

    # ───────────────────────────────── General Information ─────────────────────
    name = fields.Char(
        string='Nomor Penerimaan',
        required=True, copy=False, readonly=True,
        default=lambda self: _('Baru'),
    )
    date_receipt = fields.Datetime(
        string='Tanggal Penerimaan',
        default=fields.Datetime.now, required=True,
    )
    purchase_id = fields.Many2one('purchase.order', string='Purchase Order')
    partner_id = fields.Many2one(
        'res.partner', string='Pemasok',
        related='purchase_id.partner_id', store=True,
    )
    partner_ref = fields.Char(
        string='Nama Perusahaan Pemasok',
        related='partner_id.name',
    )
    driver_name = fields.Char(string='Nama Supir')
    driver_phone = fields.Char(string='Nomor Telepon Supir')
    vehicle_plate = fields.Char(string='Nomor Polisi Kendaraan')
    delivery_note = fields.Char(string='Nomor Surat Jalan')
    origin = fields.Char(string='Asal Kelapa')
    company_id = fields.Many2one(
        'res.company', string='Perusahaan',
        required=True, default=lambda self: self.env.company,
    )

    # ───────────────────────────────── Weight Information ──────────────────────
    total_count = fields.Integer(string='Total Jumlah Kelapa (Butir)', default=0)
    net_weight = fields.Float(
        string='Berat Bersih / Tonase (Kg)',
        required=True,
    )

    # Reject details recorded at gate inspection
    reject_pecah = fields.Float(string='Kelapa Pecah (Kg)', default=0.0)
    reject_kecil = fields.Float(string='Kelapa Kecil (Kg)', default=0.0)
    reject_tunas = fields.Float(string='Kelapa Tunas (Kg)', default=0.0)
    reject_busuk = fields.Float(string='Kelapa Busuk (Kg)', default=0.0)
    reject_muda = fields.Float(string='Kelapa Muda (Kg)', default=0.0)

    # Computed weight summaries
    total_reject = fields.Float(
        string='Total Sortiran Reject (Kg)',
        compute='_compute_total_reject', store=True,
    )
    gross_weight = fields.Float(
        string='Berat Kotor / Bruto (Kg)',
        compute='_compute_total_reject', store=True,
    )
    avg_weight = fields.Float(
        string='Berat Rata-rata per Kelapa (Kg/Butir)',
        compute='_compute_total_reject', store=True,
    )

    # ─────────────────────────────── Sorting Summary ───────────────────────────
    # These two fields are kept for backward compatibility with existing DB records.
    # In the new design they represent the gate-rejection breakdown captured at
    # receipt (before warehouse sorting), not shelling weights.  The labels have
    # been updated in the view to reflect their actual meaning.
    machine_shelling_weight = fields.Float(
        string='Berat Kelapa Layak (Kg)',
        default=0.0,
        help='Berat kelapa layak produksi yang teridentifikasi saat penerimaan (data historis).',
    )
    manual_shelling_weight = fields.Float(
        string='Berat Kelapa Reject (Kg)',
        default=0.0,
        help='Berat kelapa reject yang teridentifikasi saat penerimaan (data historis).',
    )
    total_sorting_weight = fields.Float(
        string='Total Berat Tersortir (Kg)',
        compute='_compute_total_sorting',
        store=True, readonly=True,
    )

    # ─────────────────────────────── Quality ───────────────────────────────────
    quality_grade = fields.Selection([
        ('excellent', 'Sangat Baik'),
        ('good', 'Baik'),
        ('average', 'Rata-rata'),
        ('poor', 'Buruk'),
    ], string='Nilai Kualitas', default='average')
    quality_notes = fields.Text(string='Catatan Kualitas')

    # ─────────────────────────────── Personnel ─────────────────────────────────
    receiving_employee_id = fields.Many2one(
        'hr.employee', string='Karyawan Penerima',
        default=lambda self: self.env.user.employee_id,
    )
    receiving_time = fields.Datetime(string='Waktu Penerimaan', readonly=True)
    notes = fields.Text(string='Catatan')
    attachment_delivery = fields.Binary(string='Lampiran Surat Jalan', attachment=True)
    attachment_weighing = fields.Binary(string='Lampiran Slip Timbangan', attachment=True)

    # ─────────────────────────────── Workflow ──────────────────────────────────
    state = fields.Selection([
        ('draft', 'Draft'),
        ('inspection', 'Pemeriksaan'),
        ('approved', 'Disetujui'),
        ('received', 'Diterima'),
        ('cancelled', 'Dibatalkan'),
    ], string='Status', default='draft', required=True, tracking=True)

    # ─────────────────────────────── Inventory References ──────────────────────
    picking_id = fields.Many2one(
        'stock.picking', string='Pengambilan Stok',
        readonly=True, copy=False,
    )
    move_ids = fields.One2many(
        'stock.move', related='picking_id.move_ids_without_package',
        string='Pergerakan Stok',
    )

    # ─────────────────────────────── Sorting Back-ref ──────────────────────────
    # These fields are populated by coconut_sorting when it extends this model.
    # They are declared here as placeholders so that views in this module do not
    # fail if coconut_sorting is not installed.
    # coconut_sorting adds the real One2many and computed field via _inherit.

    # ═══════════════════════════════ Compute Methods ═══════════════════════════

    @api.depends(
        'net_weight', 'reject_pecah', 'reject_kecil',
        'reject_tunas', 'reject_busuk', 'reject_muda', 'total_count',
    )
    def _compute_total_reject(self):
        for rec in self:
            rec.total_reject = (
                rec.reject_pecah + rec.reject_kecil
                + rec.reject_tunas + rec.reject_busuk + rec.reject_muda
            )
            rec.gross_weight = rec.net_weight + rec.total_reject
            rec.avg_weight = (
                rec.net_weight / rec.total_count
                if rec.total_count > 0 else 0.0
            )

    @api.depends('machine_shelling_weight', 'manual_shelling_weight')
    def _compute_total_sorting(self):
        for rec in self:
            rec.total_sorting_weight = (
                rec.machine_shelling_weight + rec.manual_shelling_weight
            )

    # ═══════════════════════════════ Constraints ═══════════════════════════════

    @api.constrains('net_weight')
    def _check_weights(self):
        for rec in self:
            if not rec.net_weight or rec.net_weight <= 0:
                raise ValidationError(_(
                    "Berat Bersih (Kg) harus lebih besar dari nol."
                ))

    @api.constrains('machine_shelling_weight', 'manual_shelling_weight')
    def _check_non_negative_weights(self):
        for rec in self:
            if rec.machine_shelling_weight < 0:
                raise ValidationError(_(
                    "Berat Kelapa Layak tidak boleh negatif."
                ))
            if rec.manual_shelling_weight < 0:
                raise ValidationError(_(
                    "Berat Kelapa Reject tidak boleh negatif."
                ))

    # ═══════════════════════════════ ORM Overrides ═════════════════════════════

    @api.model_create_multi
    def create(self, vals_list):
        for vals in vals_list:
            if vals.get('name', _('Baru')) in (_('Baru'), _('New'), 'Baru', 'New'):
                vals['name'] = (
                    self.env['ir.sequence'].next_by_code('coconut.receipt.seq')
                    or _('Baru')
                )
        return super().create(vals_list)

    # ═══════════════════════════════ Workflow Actions ══════════════════════════

    def action_start_inspection(self):
        for rec in self:
            if rec.state != 'draft':
                raise UserError(_("Hanya dokumen draft yang dapat dipindahkan ke status Pemeriksaan."))
            rec.state = 'inspection'

    def action_approve(self):
        for rec in self:
            if rec.state != 'inspection':
                raise UserError(_("Hanya dokumen dalam status Pemeriksaan yang dapat disetujui."))
            rec.state = 'approved'

    def action_receive(self):
        """
        Create an inbound stock picking to record receipt of unsorted coconuts.
        This method is idempotent – if a picking already exists and is done,
        it raises an error instead of creating a duplicate.
        """
        for rec in self:
            if rec.state != 'approved':
                raise UserError(_(
                    "Hanya penerimaan yang disetujui yang dapat diterima ke dalam persediaan."
                ))
            if rec.picking_id and rec.picking_id.state == 'done':
                raise UserError(_(
                    "Dokumen ini sudah diselesaikan dan pergerakan stok sudah tercatat. "
                    "Tidak dapat membuat pergerakan stok duplikat."
                ))

            if rec.net_weight <= 0:
                raise UserError(_("Berat Bersih (Kg) harus lebih besar dari nol."))

            # ── Resolve unsorted coconut product ──
            bulat_template = self.env.ref(
                'coconut_receiving.product_kelapa_bulat',
                raise_if_not_found=False,
            )
            if not bulat_template:
                raise UserError(_(
                    "Produk 'Kelapa Bulat' (XML ID: coconut_receiving.product_kelapa_bulat) "
                    "tidak ditemukan. Harap perbarui modul coconut_receiving."
                ))
            product_bulat = bulat_template.product_variant_ids[:1]
            if not product_bulat:
                raise UserError(_(
                    "Varian produk untuk 'Kelapa Bulat' tidak ditemukan. "
                    "Pastikan produk tersebut memiliki varian yang aktif."
                ))

            # ── Validate UoM ──
            uom_kg = self.env.ref('uom.product_uom_kgm')
            if product_bulat.uom_id.category_id != uom_kg.category_id:
                raise UserError(_(
                    "Produk '%s' masih menggunakan satuan '%s' yang bukan kategori Berat. "
                    "Silakan ubah satuan produk tersebut menjadi kg sebelum melanjutkan proses."
                ) % (product_bulat.name, product_bulat.uom_id.name))

            # ── Resolve picking type ──
            picking_type = self.env['stock.picking.type'].search([
                ('code', '=', 'incoming'),
                ('company_id', '=', rec.company_id.id),
            ], limit=1)
            if not picking_type:
                raise UserError(_(
                    "Tipe pengambilan barang masuk (Incoming) tidak ditemukan untuk perusahaan ini."
                ))

            location_dest_id = picking_type.default_location_dest_id
            if not location_dest_id:
                raise UserError(_(
                    "Lokasi tujuan default tidak ditemukan pada tipe pengambilan."
                ))

            location_src_id = self.env.ref(
                'stock.stock_location_suppliers', raise_if_not_found=False,
            )
            if not location_src_id:
                location_src_id = self.env['stock.location'].search(
                    [('usage', '=', 'supplier')], limit=1,
                )
            if not location_src_id:
                raise UserError(_("Lokasi Pemasok (Supplier) tidak ditemukan dalam sistem."))

            # ── Create picking ──
            picking = self.env['stock.picking'].create({
                'partner_id': rec.partner_id.id,
                'picking_type_id': picking_type.id,
                'location_id': location_src_id.id,
                'location_dest_id': location_dest_id.id,
                'origin': rec.name,
                'company_id': rec.company_id.id,
            })

            # ── Create move: Supplier → WH for net_weight of Kelapa Bulat ──
            self.env['stock.move'].create({
                'name': product_bulat.name,
                'product_id': product_bulat.id,
                'product_uom_qty': rec.net_weight,
                'product_uom': product_bulat.uom_id.id,
                'picking_id': picking.id,
                'location_id': location_src_id.id,
                'location_dest_id': location_dest_id.id,
                'company_id': rec.company_id.id,
                'origin': rec.name,
            })

            picking.action_confirm()
            for move in picking.move_ids:
                move.quantity = move.product_uom_qty
                move.picked = True
            picking.button_validate()

            rec.picking_id = picking.id
            rec.receiving_time = fields.Datetime.now()
            rec.state = 'received'

    def action_cancel(self):
        for rec in self:
            if rec.picking_id and rec.picking_id.state not in ('draft', 'cancel'):
                raise UserError(_(
                    "Tidak dapat membatalkan penerimaan karena pengambilan stok terkait "
                    "sudah diproses. Harap batalkan atau kembalikan pengambilan stok terlebih dahulu."
                ))
            if rec.picking_id:
                rec.picking_id.action_cancel()
            rec.state = 'cancelled'

    def action_reset_draft(self):
        for rec in self:
            if rec.state != 'cancelled':
                raise UserError(_("Hanya dokumen yang dibatalkan yang dapat dikembalikan ke Draft."))
            if rec.picking_id and rec.picking_id.state not in ('draft', 'cancel'):
                raise UserError(_(
                    "Tidak dapat mengembalikan ke draft karena pengambilan stok terkait sudah diproses."
                ))
            rec.state = 'draft'
