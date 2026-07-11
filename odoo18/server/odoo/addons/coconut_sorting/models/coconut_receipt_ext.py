# -*- coding: utf-8 -*-
from odoo import api, fields, models


class CoconutReceiptSortingMixin(models.Model):
    """
    Extension of coconut.receipt owned by coconut_sorting.

    Adds:
      • sorting_ids  – One2many to all sorting records for this receipt
      • total_sorting_input_weight  – sum of input_weight_kg from done sortings
      • remaining_unsorted_weight   – net_weight minus total_sorting_input_weight
    """
    _inherit = 'coconut.receipt'

    sorting_ids = fields.One2many(
        comodel_name='coconut.sorting',
        inverse_name='receipt_id',
        string='Proses Sortir',
        readonly=True,
    )

    total_sorting_input_weight = fields.Float(
        string='Total Input Sortir (Kg)',
        compute='_compute_sorting_summary',
        store=True,
        readonly=True,
        help='Jumlah berat input dari semua proses sortir yang sudah selesai (status Done).',
    )

    remaining_unsorted_weight = fields.Float(
        string='Sisa Berat Belum Tersortir (Kg)',
        compute='_compute_sorting_summary',
        store=True,
        readonly=True,
        help='Berat Kelapa Bulat yang belum diproses sortir dari penerimaan ini.',
    )

    @api.depends(
        'net_weight',
        'sorting_ids.state',
        'sorting_ids.input_weight_kg',
    )
    def _compute_sorting_summary(self):
        for receipt in self:
            done_lines = receipt.sorting_ids.filtered(
                lambda s: s.state == 'done'
            )
            total_in = sum(done_lines.mapped('input_weight_kg'))
            receipt.total_sorting_input_weight = total_in
            receipt.remaining_unsorted_weight = receipt.net_weight - total_in
