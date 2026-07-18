# -*- coding: utf-8 -*-
from odoo import api, fields, models, _
from odoo.exceptions import ValidationError

class HrEmployee(models.Model):
    _inherit = 'hr.employee'

    payroll_worker_type = fields.Selection([
        ('daily', 'Karyawan Harian'),
        ('sheller', 'Sheller Borongan'),
        ('parer', 'Parer Borongan'),
    ], string='Jenis Penggajian')

    employee_code = fields.Char(
        string='Kode Karyawan',
        index=True,
    )
    
    payroll_active = fields.Boolean(
        string='Payroll Aktif',
        default=True,
    )

    @api.constrains('employee_code')
    def _check_employee_code_unique(self):
        for record in self:
            if record.employee_code:
                domain = [
                    ('employee_code', '=', record.employee_code),
                    ('id', '!=', record.id)
                ]
                duplicate = self.search(domain, limit=1)
                if duplicate:
                    raise ValidationError(_("Kode Karyawan '%s' sudah digunakan oleh karyawan lain (%s).") % (record.employee_code, duplicate.name))
