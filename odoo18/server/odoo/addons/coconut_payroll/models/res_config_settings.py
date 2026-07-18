# -*- coding: utf-8 -*-
from odoo import fields, models

class ResConfigSettings(models.TransientModel):
    _inherit = 'res.config.settings'

    payroll_overtime_rate = fields.Monetary(
        related='company_id.payroll_overtime_rate',
        readonly=False,
        string='Tarif Lembur per Jam',
    )
    payroll_daily_base_wage = fields.Monetary(
        related='company_id.payroll_daily_base_wage',
        readonly=False,
        string='Upah Dasar Harian',
    )
    payroll_standard_hours = fields.Float(
        related='company_id.payroll_standard_hours',
        readonly=False,
        string='Jam Kerja Standar',
    )
    payroll_rounding_unit = fields.Monetary(
        related='company_id.payroll_rounding_unit',
        readonly=False,
        string='Satuan Pembulatan Gaji',
    )
