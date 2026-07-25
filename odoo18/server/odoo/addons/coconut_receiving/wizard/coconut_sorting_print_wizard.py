# -*- coding: utf-8 -*-
from odoo import api, fields, models, _

class CoconutSortingPrintWizard(models.TransientModel):
    _name = 'coconut.sorting.print.wizard'
    _description = 'Cetak Form Hasil Sortir Kelapa Wizard'

    date = fields.Date(
        string='Tanggal',
        default=fields.Date.context_today,
        required=True
    )

    def print_pdf(self):
        self.ensure_one()
        return self.env.ref('coconut_receiving.action_report_coconut_sorting_blank_form').report_action(self)
