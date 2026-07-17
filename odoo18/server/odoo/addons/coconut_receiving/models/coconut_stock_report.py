# -*- coding: utf-8 -*-
from odoo import api, fields, models, _
from odoo.exceptions import UserError
import logging

_logger = logging.getLogger(__name__)


class CoconutDailyStock(models.Model):
    """
    Stok Kelapa Harian -- Daily Coconut Stock Record

    Setiap record mewakili SATU baris penerimaan kelapa pada suatu tanggal,
    dilengkapi data sortir, produksi, dan ringkasan stok real-time.

    Format sesuai Excel perusahaan:
        Tanggal | Supplier | Asal Kelapa | Butir | Kg/Butir | Tonase | Reject | Bruto
        + TOTAL STOK KELAPA (real-time dari stock.quant)
        + PAKAI KELAPA HARI INI (dari coconut.manufacturing)
    """
    _name = 'coconut.daily.stock'
    _description = 'Stok Kelapa Harian'
    _order = 'receipt_date desc, id desc'
    _rec_name = 'display_name'

    # ===================================================================
    # SOURCE LINK
    # ===================================================================

    receipt_id = fields.Many2one(
        'coconut.receipt',
        string='Penerimaan Kelapa',
        ondelete='restrict',
        required=True,
        readonly=True,
    )

    # ===================================================================
    # KOLOM EXCEL: INFORMASI PENERIMAAN
    # ===================================================================

    receipt_date = fields.Date(
        string='Tanggal',
        readonly=True,
    )
    supplier_id = fields.Many2one(
        'res.partner',
        string='Supplier',
        readonly=True,
    )
    coconut_origin = fields.Char(
        string='Asal Kelapa',
        readonly=True,
    )
    total_coconut_count = fields.Integer(
        string='Butir',
        readonly=True,
        help='Jumlah buah kelapa yang diterima.',
    )
    kg_per_coconut = fields.Float(
        string='Kg/Butir',
        digits=(16, 3),
        readonly=True,
    )
    # Tonase = berat kelapa layak dari sortir (diisi dari coconut.sorting)
    tonase_layak = fields.Float(
        string='Tonase (Kg Layak)',
        digits=(16, 3),
        readonly=True,
        help='Berat Kelapa Layak Produksi hasil sortir.',
    )
    # Reject = berat kelapa reject dari sortir
    reject_kg = fields.Float(
        string='Reject (Kg)',
        digits=(16, 3),
        readonly=True,
        help='Berat Kelapa Reject hasil sortir.',
    )
    # Bruto = gross_vehicle_weight dari slip timbangan
    bruto_kg = fields.Float(
        string='Bruto (Kg)',
        digits=(16, 3),
        readonly=True,
        help='Berat kotor kendaraan + muatan dari slip timbangan.',
    )

    # ===================================================================
    # KOLOM EXCEL: TOTAL STOK KELAPA (real-time dari stock.quant)
    # ===================================================================

    stok_kelapa_bulat = fields.Float(
        string='Stok Kelapa Bulat (Kg)',
        digits=(16, 3),
        compute='_compute_stok_real_time',
        store=False,
        help='Stok Kelapa Bulat saat ini di gudang.',
    )
    stok_kelapa_layak = fields.Float(
        string='Stok Kelapa Layak (Kg)',
        digits=(16, 3),
        compute='_compute_stok_real_time',
        store=False,
        help='Stok Kelapa Layak Produksi saat ini di gudang.',
    )
    stok_kelapa_reject = fields.Float(
        string='Stok Kelapa Reject (Kg)',
        digits=(16, 3),
        compute='_compute_stok_real_time',
        store=False,
        help='Stok Kelapa Reject saat ini di gudang.',
    )
    stok_kelapa_sheller = fields.Float(
        string='Stok Kelapa Sheller (Kg)',
        digits=(16, 3),
        compute='_compute_stok_real_time',
        store=False,
    )
    stok_kelapa_parer = fields.Float(
        string='Stok Kelapa Parer (Kg)',
        digits=(16, 3),
        compute='_compute_stok_real_time',
        store=False,
    )
    stok_kelapa_akhir_mp = fields.Float(
        string='Stok Kelapa Akhir MP (Kg)',
        digits=(16, 3),
        compute='_compute_stok_real_time',
        store=False,
    )
    total_stok_kelapa = fields.Float(
        string='Total Stok Kelapa (Kg)',
        digits=(16, 3),
        compute='_compute_stok_real_time',
        store=False,
        help='Total stok bahan baku: Kelapa Bulat + Layak + Reject.',
    )

    # ===================================================================
    # KOLOM EXCEL: PAKAI KELAPA HARI INI (dari coconut.manufacturing)
    # ===================================================================

    pakai_kelapa_hari_ini = fields.Float(
        string='Pakai Kelapa Hari Ini (Kg)',
        digits=(16, 3),
        compute='_compute_pakai_hari_ini',
        store=False,
        help='Total input Sheller (Machine + Manual) pada tanggal penerimaan ini.',
    )

    # ===================================================================
    # DISPLAY NAME
    # ===================================================================

    display_name = fields.Char(
        string='Nama',
        compute='_compute_display_name',
        store=False,
    )

    @api.depends('receipt_id', 'receipt_date', 'supplier_id')
    def _compute_display_name(self):
        for rec in self:
            date_str = str(rec.receipt_date) if rec.receipt_date else '-'
            supplier = rec.supplier_id.name if rec.supplier_id else '-'
            rec.display_name = f'{date_str} | {supplier}'

    # ===================================================================
    # COMPUTED: STOK REAL-TIME
    # ===================================================================

    def _get_stock_qty(self, xml_id, loc_xml_id=None):
        """Helper: get current on-hand qty for a product template XML ID and optional location XML ID."""
        tmpl = self.env.ref(xml_id, raise_if_not_found=False)
        if not tmpl:
            return 0.0
        product = tmpl.product_variant_ids[:1]
        if not product:
            return 0.0
        
        if loc_xml_id:
            location = self.env.ref(loc_xml_id, raise_if_not_found=False)
        else:
            wh = self.env['stock.warehouse'].search(
                [('company_id', '=', self.env.company.id)], limit=1
            )
            location = wh.lot_stock_id if wh else False

        if not location:
            return 0.0

        quant = self.env['stock.quant'].search([
            ('product_id', '=', product.id),
            ('location_id', '=', location.id),
        ], limit=1)
        return quant.quantity if quant else 0.0

    @api.depends()
    def _compute_stok_real_time(self):
        # Fetch once per compute call (same value for all records)
        bulat = self._get_stock_qty('coconut_receiving.product_kelapa_bulat', 'coconut_receiving.location_gudang_kelapa_bulat')
        layak = self._get_stock_qty('coconut_receiving.product_kelapa_layak', 'coconut_receiving.location_stok_kelapa_layak')
        reject = self._get_stock_qty('coconut_receiving.product_kelapa_reject', 'coconut_receiving.location_stok_kelapa_reject')
        sheller = self._get_stock_qty('coconut_receiving.product_kelapa_sheller', 'coconut_receiving.location_area_sheller')
        parer = self._get_stock_qty('coconut_receiving.product_kelapa_parer', 'coconut_receiving.location_area_parer')
        akhir_mp = self._get_stock_qty('coconut_receiving.product_kelapa_akhir_mp', 'coconut_receiving.location_gudang_kelapa_akhir_mp')
        total = bulat + layak + reject
        for rec in self:
            rec.stok_kelapa_bulat = bulat
            rec.stok_kelapa_layak = layak
            rec.stok_kelapa_reject = reject
            rec.stok_kelapa_sheller = sheller
            rec.stok_kelapa_parer = parer
            rec.stok_kelapa_akhir_mp = akhir_mp
            rec.total_stok_kelapa = total

    # ===================================================================
    # COMPUTED: PAKAI KELAPA HARI INI
    # ===================================================================

    @api.depends('receipt_date')
    def _compute_pakai_hari_ini(self):
        for rec in self:
            if not rec.receipt_date:
                rec.pakai_kelapa_hari_ini = 0.0
                continue
            mfg_docs = self.env['coconut.manufacturing'].search([
                ('production_date', '=', rec.receipt_date),
                ('state', '=', 'done'),
            ])
            total_input = sum(mfg_docs.mapped('machine_sheller_input')) + \
                          sum(mfg_docs.mapped('manual_sheller_input'))
            rec.pakai_kelapa_hari_ini = total_input

    @api.model
    def _search(self, domain, offset=0, limit=None, order=None):
        selected_product_code = self.env.context.get('selected_product_code')
        if selected_product_code:
            if selected_product_code == 'COCO-BULAT':
                domain = domain + [('total_coconut_count', '>', 0)]
            elif selected_product_code == 'COCO-LAYAK':
                domain = domain + [('tonase_layak', '>', 0)]
            elif selected_product_code == 'COCO-REJECT':
                domain = domain + [('reject_kg', '>', 0)]
            elif selected_product_code in ('COCO-SHELLER', 'COCO-PARER', 'COCO-AKHIR-MP'):
                domain = domain + [('pakai_kelapa_hari_ini', '>', 0)]
        return super(CoconutDailyStock, self)._search(domain, offset=offset, limit=limit, order=order)

    # ===================================================================
    # ORM: CREATE FROM RECEIPT
    # ===================================================================

    @api.model
    def _sync_from_receipt(self, receipt):
        """
        Create or update the daily stock record for a validated receipt.
        Called from coconut.receipt.action_validate (via post-validate hook).
        """
        existing = self.search([('receipt_id', '=', receipt.id)], limit=1)

        # Resolve sortir data (from coconut.sorting linked to this receipt)
        sorting = self.env['coconut.sorting'].search([
            ('receipt_id', '=', receipt.id),
            ('state', '=', 'done'),
        ], limit=1)
        tonase_layak = sorting.good_coconut_kg if sorting else 0.0
        reject_kg = sorting.reject_coconut_kg if sorting else 0.0

        kg_per_butir = (
            receipt.net_received_weight / receipt.total_count
            if receipt.total_count and receipt.total_count > 0
            else 0.0
        )

        vals = {
            'receipt_id': receipt.id,
            'receipt_date': (
                receipt.entry_datetime.date() if receipt.entry_datetime else fields.Date.today()
            ),
            'supplier_id': receipt.partner_id.id,
            'coconut_origin': receipt.origin or '',
            'total_coconut_count': receipt.total_count or 0,
            'kg_per_coconut': kg_per_butir,
            'tonase_layak': tonase_layak,
            'reject_kg': reject_kg,
            'bruto_kg': receipt.gross_vehicle_weight or 0.0,
        }

        if existing:
            existing.write(vals)
            return existing
        else:
            return self.create(vals)


class CoconutDailyStockWizard(models.TransientModel):
    """
    Wizard untuk melihat laporan Stok Kelapa Harian dengan filter tanggal.
    Menggantikan peran lama coconut.stock.report sebagai entry point filter.
    """
    _name = 'coconut.stock.report'
    _description = 'Laporan Stok Kelapa Harian (Filter)'

    date_from = fields.Date(
        string='Dari Tanggal',
        required=True,
        default=fields.Date.context_today,
    )
    date_to = fields.Date(
        string='Sampai Tanggal',
        required=True,
        default=fields.Date.context_today,
    )

    def action_open_report(self):
        """Open the daily stock list filtered by selected date range."""
        self.ensure_one()
        if self.date_from > self.date_to:
            raise UserError(_("Tanggal Dari tidak boleh lebih besar dari Tanggal Sampai."))
        return {
            'type': 'ir.actions.act_window',
            'name': _('Stok Kelapa Harian'),
            'res_model': 'coconut.daily.stock',
            'view_mode': 'list,form',
            'domain': [
                ('receipt_date', '>=', self.date_from),
                ('receipt_date', '<=', self.date_to),
            ],
            'context': {
                'search_default_date_from': str(self.date_from),
                'search_default_date_to': str(self.date_to),
            },
            'target': 'main',
        }

    def action_view_all(self):
        """Open all daily stock records without date filter."""
        return {
            'type': 'ir.actions.act_window',
            'name': _('Stok Kelapa Harian'),
            'res_model': 'coconut.daily.stock',
            'view_mode': 'list,form',
            'target': 'main',
        }
