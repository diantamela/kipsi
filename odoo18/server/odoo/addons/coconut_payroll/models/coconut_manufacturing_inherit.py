# -*- coding: utf-8 -*-
from odoo import api, fields, models

class CoconutManufacturing(models.Model):
    _inherit = 'coconut.manufacturing'

    work_sheet_ids = fields.One2many(
        'coconut.work.sheet', 'transfer_id',
        string='Lembar Kerja Terkait',
    )
