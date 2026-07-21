# -*- coding: utf-8 -*-
from odoo import api, fields, models

class CoconutManufacturing(models.Model):
    _inherit = 'coconut.manufacturing'

    work_sheet_ids = fields.One2many(
        'coconut.work.sheet', 'transfer_id',
        string='Lembar Kerja Terkait',
    )

    realisasi_sheller_mesin = fields.Float(
        string='Hasil Kerja Sheller Mesin (Kg)',
        compute='_compute_realisasi',
        store=True,
    )
    realisasi_sheller_manual = fields.Float(
        string='Hasil Kerja Sheller Manual (Kg)',
        compute='_compute_realisasi',
        store=True,
    )
    realisasi_total_sheller = fields.Float(
        string='Total Hasil Sheller (Kg)',
        compute='_compute_realisasi',
        store=True,
    )
    realisasi_sisa_sheller = fields.Float(
        string='Sisa Area Sheller (Kg)',
        compute='_compute_realisasi',
        store=True,
    )
    realisasi_perrer_mesin = fields.Float(
        string='Hasil Kerja Perrer dari Sheller Mesin (Kg)',
        compute='_compute_realisasi',
        store=True,
    )
    realisasi_perrer_manual = fields.Float(
        string='Hasil Kerja Perrer dari Sheller Manual (Kg)',
        compute='_compute_realisasi',
        store=True,
    )
    realisasi_total_perrer = fields.Float(
        string='Total Hasil Perrer (Kg)',
        compute='_compute_realisasi',
        store=True,
    )
    realisasi_sisa_perrer = fields.Float(
        string='Sisa Area Perrer (Kg)',
        compute='_compute_realisasi',
        store=True,
    )

    # Status Realisasi Produksi
    realisasi_state = fields.Selection([
        ('no_result', 'Belum Ada Hasil Kerja'),
        ('partial', 'Sebagian'),
        ('done', 'Selesai'),
    ], string='Status Realisasi Produksi', compute='_compute_realisasi_state', store=True, default='no_result')

    @api.depends(
        'work_sheet_ids.total_production_qty',
        'work_sheet_ids.state',
        'work_sheet_ids.worker_type',
        'work_sheet_ids.parer_source',
        'total_transfer_sheller',
        'transfer_perrer_mesin_qty',
        'transfer_perrer_manual_qty'
    )
    def _compute_realisasi(self):
        for rec in self:
            sheets = rec.work_sheet_ids.filtered(lambda s: s.state in ('validated', 'processed'))
            
            mesin_sheets = sheets.filtered(lambda s: s.worker_type == 'sheller_mesin')
            manual_sheets = sheets.filtered(lambda s: s.worker_type == 'sheller_manual')
            parer_mesin_sheets = sheets.filtered(lambda s: s.worker_type == 'parer' and s.parer_source == 'mesin')
            parer_manual_sheets = sheets.filtered(lambda s: s.worker_type == 'parer' and s.parer_source == 'manual')
            
            rec.realisasi_sheller_mesin = sum(mesin_sheets.mapped('total_production_qty'))
            rec.realisasi_sheller_manual = sum(manual_sheets.mapped('total_production_qty'))
            rec.realisasi_total_sheller = rec.realisasi_sheller_mesin + rec.realisasi_sheller_manual
            rec.realisasi_sisa_sheller = rec.total_transfer_sheller - rec.realisasi_total_sheller
            
            rec.realisasi_perrer_mesin = sum(parer_mesin_sheets.mapped('total_production_qty'))
            rec.realisasi_perrer_manual = sum(parer_manual_sheets.mapped('total_production_qty'))
            rec.realisasi_total_perrer = rec.realisasi_perrer_mesin + rec.realisasi_perrer_manual
            rec.realisasi_sisa_perrer = (rec.transfer_perrer_mesin_qty + rec.transfer_perrer_manual_qty) - rec.realisasi_total_perrer

    @api.depends(
        'sheller_mesin_qty', 'sheller_manual_qty',
        'transfer_perrer_mesin_qty', 'transfer_perrer_manual_qty',
        'realisasi_sheller_mesin', 'realisasi_sheller_manual',
        'realisasi_perrer_mesin', 'realisasi_perrer_manual'
    )
    def _compute_realisasi_state(self):
        for rec in self:
            total_transferred = (
                rec.sheller_mesin_qty + rec.sheller_manual_qty +
                rec.transfer_perrer_mesin_qty + rec.transfer_perrer_manual_qty
            )
            total_realized = (
                rec.realisasi_sheller_mesin + rec.realisasi_sheller_manual +
                rec.realisasi_perrer_mesin + rec.realisasi_perrer_manual
            )
            if total_transferred <= 0:
                rec.realisasi_state = 'no_result'
            elif total_realized <= 0:
                rec.realisasi_state = 'no_result'
            elif total_realized >= total_transferred:
                rec.realisasi_state = 'done'
            else:
                rec.realisasi_state = 'partial'
