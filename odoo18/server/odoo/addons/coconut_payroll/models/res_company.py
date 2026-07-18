# -*- coding: utf-8 -*-
from odoo import fields, models

class ResCompany(models.Model):
    _inherit = 'res.company'

    payroll_overtime_rate = fields.Monetary(
        string='Tarif Lembur per Jam',
        currency_field='currency_id',
        default=12000.0,
    )
    payroll_daily_base_wage = fields.Monetary(
        string='Upah Dasar Harian',
        currency_field='currency_id',
        default=65000.0,
    )
    payroll_standard_hours = fields.Float(
        string='Jam Kerja Standar',
        default=7.0,
    )
    payroll_rounding_unit = fields.Monetary(
        string='Satuan Pembulatan Gaji',
        currency_field='currency_id',
        default=1000.0,
    )
