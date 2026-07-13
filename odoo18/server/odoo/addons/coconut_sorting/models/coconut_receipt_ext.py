# -*- coding: utf-8 -*-
from odoo import api, fields, models


class CoconutReceiptSortingMixin(models.Model):
    """
    Extension of coconut.receipt owned by coconut_sorting.

    Adds:
      • sorting_ids              – One2many to historical sorting records
      • manufacturing_ids        – One2many to manufacturing documents
      • total_sorting_input_weight     – sum of raw_coconut_processed from done manufacturing
      • remaining_unsorted_weight      – net_received_weight minus total sorted/manufactured
    """
    _inherit = 'coconut.receipt'

    # ── Historical sorting records (coconut.sorting – kept for audit) ──
    sorting_ids = fields.One2many(
        comodel_name='coconut.sorting',
        inverse_name='receipt_id',
        string='Riwayat Sortir (Lama)',
        readonly=True,
    )

    # ── Manufacturing documents (coconut.manufacturing – new workflow) ──
    manufacturing_ids = fields.One2many(
        comodel_name='coconut.manufacturing',
        inverse_name='receipt_id',
        string='Dokumen Manufaktur',
        readonly=True,
    )

    # ── Summary computed from new manufacturing documents ──
    total_sorting_input_weight = fields.Float(
        string='Total Kelapa Diproses (Kg)',
        compute='_compute_sorting_summary',
        store=True,
        readonly=True,
        help='Jumlah Kelapa Bulat yang sudah diproses dari penerimaan ini (status Done).',
    )

    remaining_unsorted_weight = fields.Float(
        string='Sisa Kelapa Bulat Belum Diproses (Kg)',
        compute='_compute_sorting_summary',
        store=True,
        readonly=True,
        help='Berat Kelapa Bulat yang belum diproses dari penerimaan ini.',
    )

    @api.depends(
        'net_received_weight',
        'manufacturing_ids.state',
        'manufacturing_ids.raw_coconut_processed',
        # backward compat: also consider old sorting records
        'sorting_ids.state',
        'sorting_ids.input_weight_kg',
    )
    def _compute_sorting_summary(self):
        for receipt in self:
            # From new manufacturing workflow
            done_mfg = receipt.manufacturing_ids.filtered(
                lambda m: m.state == 'done'
            )
            mfg_total = sum(done_mfg.mapped('raw_coconut_processed'))

            # From legacy sorting workflow (historical)
            done_sort = receipt.sorting_ids.filtered(
                lambda s: s.state == 'done'
            )
            sort_total = sum(done_sort.mapped('input_weight_kg'))

            total_in = mfg_total + sort_total
            receipt.total_sorting_input_weight = total_in
            receipt.remaining_unsorted_weight = receipt.net_received_weight - total_in
