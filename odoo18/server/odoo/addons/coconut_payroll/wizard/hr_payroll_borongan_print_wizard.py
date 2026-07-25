# -*- coding: utf-8 -*-
from odoo import api, fields, models, _

class HrPayrollBoronganPrintWizard(models.TransientModel):
    _name = 'hr.payroll.borongan.print.wizard'
    _description = 'Print Form Hasil Kerja Borongan Wizard'

    date = fields.Date(
        string='Tanggal',
        default=fields.Date.context_today,
        required=True
    )

    jenis_pekerjaan = fields.Selection([
        ('parer', 'Parer'),
        ('sheller_manual', 'Sheller Manual'),
        ('sheller_mesin', 'Sheller Mesin'),
    ], string='Jenis Pekerjaan', default='parer', required=True)

    def get_employees(self):
        self.ensure_one()
        # Build domain filtering by payroll_job_type and active status
        domain = [
            ('active', '=', True),
            ('payroll_job_type', '=', self.jenis_pekerjaan)
        ]
        return self.env['hr.employee'].search(domain, order='name asc')

    def print_pdf(self):
        self.ensure_one()
        return self.env.ref('coconut_payroll.action_report_hasil_kerja_borongan').report_action(self)
