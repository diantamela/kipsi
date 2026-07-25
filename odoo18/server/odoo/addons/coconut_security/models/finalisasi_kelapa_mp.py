# -*- coding: utf-8 -*-
from odoo import models, api

class FinalisasiKelapaMP(models.Model):
    _inherit = 'finalisasi.kelapa.mp'

    @api.model
    def get_dashboard_data(self):
        # Run the dashboard data fetcher as sudo to bypass model access checks on MRP/HR models for RMP users
        return super(FinalisasiKelapaMP, self.sudo()).get_dashboard_data()
