# -*- coding: utf-8 -*-
from odoo import api, fields, models, _
from odoo.exceptions import UserError
import logging

_logger = logging.getLogger(__name__)


class CoconutStockReport(models.TransientModel):
    """
    Stok Kelapa Harian – Daily Coconut Stock Report

    Displays:
    - Receipt Date, Supplier, Origin, Coconut Count, KG/Coconut
    - Good Coconut / Tonase (Kelapa Layak from sorting)
    - Reject Coconut
    - Total Coconut Processed (Good + Reject)
    - Beginning Raw Coconut Stock
    - Coconut Received Today
    - Coconut Used Today (Machine Sheller Input + Manual Sheller Input)
    - Ending Raw Coconut Stock

    Raw Coconut Stock = Kelapa Bulat + Kelapa Layak + Kelapa Reject
    (NOT including Kelapa Sheller or Kelapa Parer)
    """
    _name = 'coconut.stock.report'
    _description = 'Laporan Stok Kelapa Harian'

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
    line_ids = fields.One2many(
        'coconut.stock.report.line',
        'report_id',
        string='Baris Laporan',
        readonly=True,
    )

    def action_generate(self):
        """Generate report lines from validated documents."""
        self.ensure_one()
        if self.date_from > self.date_to:
            raise UserError(_("Tanggal Dari tidak boleh lebih besar dari Tanggal Sampai."))

        # Clear existing lines
        self.line_ids.unlink()

        # ── Resolve products ──
        def _get_product(xml_id):
            tmpl = self.env.ref(xml_id, raise_if_not_found=False)
            return tmpl.product_variant_ids[:1] if tmpl else False

        p_bulat = _get_product('coconut_receiving.product_kelapa_bulat')
        p_layak = _get_product('coconut_receiving.product_kelapa_layak')
        p_reject = _get_product('coconut_receiving.product_kelapa_reject')

        # ── Get warehouse location ──
        loc_wh = self.env['stock.warehouse'].search(
            [('company_id', '=', self.env.company.id)], limit=1,
        )
        location = loc_wh.lot_stock_id if loc_wh else False

        # ── Fetch done receipts in date range ──
        receipts = self.env['coconut.receipt'].search([
            ('state', '=', 'done'),
            ('entry_datetime', '>=', fields.Datetime.to_datetime(str(self.date_from))),
            ('entry_datetime', '<=', fields.Datetime.to_datetime(str(self.date_to) + ' 23:59:59')),
        ], order='entry_datetime asc')

        lines = []
        for receipt in receipts:
            # Done manufacturing docs for this receipt on this date range
            mfg_docs = self.env['coconut.manufacturing'].search([
                ('receipt_id', '=', receipt.id),
                ('state', '=', 'done'),
                ('production_date', '>=', self.date_from),
                ('production_date', '<=', self.date_to),
            ])

            good_total = sum(mfg_docs.mapped('good_coconut_weight'))
            reject_total = sum(mfg_docs.mapped('reject_coconut_weight'))
            total_processed = good_total + reject_total
            machine_input = sum(mfg_docs.mapped('machine_sheller_input'))
            manual_input = sum(mfg_docs.mapped('manual_sheller_input'))
            coconut_used_today = machine_input + manual_input
            kg_per_coconut = (
                receipt.avg_weight_per_coconut
                if receipt.total_count > 0 else 0.0
            )

            lines.append({
                'report_id': self.id,
                'receipt_date': receipt.entry_datetime.date() if receipt.entry_datetime else False,
                'supplier_id': receipt.partner_id.id,
                'coconut_origin': receipt.origin or '',
                'total_coconut_count': receipt.total_count,
                'kg_per_coconut': kg_per_coconut,
                'good_coconut_tonase': good_total,
                'reject_coconut': reject_total,
                'total_coconut_processed': total_processed,
                'coconut_received': receipt.net_received_weight,
                'coconut_used_today': coconut_used_today,
                'receipt_id': receipt.id,
            })

        if lines:
            # Compute beginning/ending stock for each line
            # Beginning stock = Kelapa Bulat + Layak + Reject at start of day
            for line_vals in lines:
                d = line_vals['receipt_date']
                begin_bulat = self._get_qty_at_date(p_bulat, location, d) if p_bulat and location else 0.0
                begin_layak = self._get_qty_at_date(p_layak, location, d) if p_layak and location else 0.0
                begin_reject = self._get_qty_at_date(p_reject, location, d) if p_reject and location else 0.0
                line_vals['beginning_raw_stock'] = begin_bulat + begin_layak + begin_reject
                line_vals['ending_raw_stock'] = (
                    line_vals['beginning_raw_stock']
                    + line_vals['coconut_received']
                    - line_vals['coconut_used_today']
                )

            self.env['coconut.stock.report.line'].create(lines)

        return {
            'type': 'ir.actions.act_window',
            'res_model': 'coconut.stock.report',
            'res_id': self.id,
            'view_mode': 'form',
            'target': 'new',
        }

    def _get_qty_at_date(self, product, location, date):
        """
        Approximate on-hand quantity at the beginning of `date`
        using current quant qty. For precise historical reporting, use
        stock.move history.
        """
        if not product or not location:
            return 0.0
        quant = self.env['stock.quant'].search([
            ('product_id', '=', product.id),
            ('location_id', '=', location.id),
        ], limit=1)
        return quant.quantity if quant else 0.0


class CoconutStockReportLine(models.TransientModel):
    _name = 'coconut.stock.report.line'
    _description = 'Baris Laporan Stok Kelapa Harian'
    _order = 'receipt_date asc, id asc'

    report_id = fields.Many2one('coconut.stock.report', required=True, ondelete='cascade')
    receipt_id = fields.Many2one('coconut.receipt', string='Penerimaan', readonly=True)

    receipt_date = fields.Date(string='Tanggal Penerimaan', readonly=True)
    supplier_id = fields.Many2one('res.partner', string='Pemasok', readonly=True)
    coconut_origin = fields.Char(string='Asal Kelapa', readonly=True)
    total_coconut_count = fields.Integer(string='Jumlah Kelapa (Butir)', readonly=True)
    kg_per_coconut = fields.Float(string='KG per Butir', readonly=True)
    good_coconut_tonase = fields.Float(string='Kelapa Layak / Tonase (Kg)', readonly=True)
    reject_coconut = fields.Float(string='Kelapa Reject (Kg)', readonly=True)
    total_coconut_processed = fields.Float(string='Total Kelapa Diproses (Kg)', readonly=True)
    beginning_raw_stock = fields.Float(string='Stok Awal Kelapa Mentah (Kg)', readonly=True)
    coconut_received = fields.Float(string='Kelapa Diterima (Kg)', readonly=True)
    coconut_used_today = fields.Float(string='Kelapa Terpakai (Kg)', readonly=True)
    ending_raw_stock = fields.Float(string='Stok Akhir Kelapa Mentah (Kg)', readonly=True)
