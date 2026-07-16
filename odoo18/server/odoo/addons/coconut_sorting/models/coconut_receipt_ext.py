# -*- coding: utf-8 -*-
from odoo import api, fields, models


class CoconutReceiptSortingMixin(models.Model):
    """
    Extension of coconut.receipt owned by coconut_sorting.

    Adds:
      • sorting_ids              – One2many to coconut.sorting records
      • manufacturing_ids        – One2many to manufacturing (PKK) documents
      • total_sorting_input_weight     – sum of input from done sortir records
      • remaining_unsorted_weight      – net_received_weight minus total yang sudah disortir
    """
    _inherit = 'coconut.receipt'

    # ── Sorting records (coconut.sorting – modul Sortir Kelapa) ──
    sorting_ids = fields.One2many(
        comodel_name='coconut.sorting',
        inverse_name='receipt_id',
        string='Sortir Kelapa',
        readonly=True,
    )

    # ── Manufacturing documents (coconut.manufacturing – PKK) ──
    manufacturing_ids = fields.One2many(
        comodel_name='coconut.manufacturing',
        inverse_name='receipt_id',
        string='Pemakaian Kelapa Produksi (PKK)',
        readonly=True,
    )

    # ── Summary computed from sorting records ──
    total_sorting_input_weight = fields.Float(
        string='Total Kelapa Disortir (Kg)',
        compute='_compute_sorting_summary',
        store=True,
        readonly=True,
        help='Jumlah Kelapa Bulat yang sudah diproses dari penerimaan ini (status Done).',
    )

    remaining_unsorted_weight = fields.Float(
        string='Sisa Kelapa Bulat Belum Disortir (Kg)',
        compute='_compute_sorting_summary',
        store=True,
        readonly=True,
        help='Berat Kelapa Bulat yang belum disortir dari penerimaan ini.',
    )

    @api.depends(
        'net_received_weight',
        'sorting_ids.state',
        'sorting_ids.input_weight_kg',
    )
    def _compute_sorting_summary(self):
        for receipt in self:
            # Dari sorting records yang sudah selesai
            done_sort = receipt.sorting_ids.filtered(
                lambda s: s.state == 'done'
            )
            sort_total = sum(done_sort.mapped('input_weight_kg'))

            receipt.total_sorting_input_weight = sort_total
            receipt.remaining_unsorted_weight = receipt.net_received_weight - sort_total
