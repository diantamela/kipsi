# -*- coding: utf-8 -*-
from odoo import api, fields, models, _
from odoo.exceptions import ValidationError

class HrEmployee(models.Model):
    _inherit = 'hr.employee'

    payroll_worker_type = fields.Selection([
        ('parer', 'Parer'),
        ('sheller_manual', 'Sheller Manual'),
        ('sheller_mesin', 'Sheller Mesin'),
        ('rmp', 'RMP'),
    ], string='Jenis Penggajian', compute='_compute_payroll_worker_type', store=True, readonly=False)

    payroll_job_type = fields.Selection([
        ('parer', 'Parer'),
        ('sheller_manual', 'Sheller Manual'),
        ('sheller_mesin', 'Sheller Mesin'),
        ('rmp', 'RMP'),
    ], string='Jenis Pekerjaan Payroll', store=True)

    @api.onchange('department_id')
    def _onchange_department_id_payroll_job_type(self):
        if self.department_id:
            dep_name = self.department_id.name or ''
            dep_display = self.department_id.display_name or ''
            if 'Parer' in dep_name or 'Parer' in dep_display:
                self.payroll_job_type = 'parer'
            elif 'Sheller Manual' in dep_name or 'Sheller Manual' in dep_display:
                self.payroll_job_type = 'sheller_manual'
            elif 'Sheller Mesin' in dep_name or 'Sheller Mesin' in dep_display:
                self.payroll_job_type = 'sheller_mesin'
            elif 'RMP' in dep_name or 'Raw Material Preparation' in dep_name or 'RMP' in dep_display or 'Raw Material Preparation' in dep_display:
                self.payroll_job_type = 'rmp'

    @api.model_create_multi
    def create(self, vals_list):
        for vals in vals_list:
            if not vals.get('payroll_job_type') and vals.get('department_id'):
                dep = self.env['hr.department'].browse(vals['department_id'])
                dep_name = dep.name or ''
                dep_display = dep.display_name or ''
                if 'Parer' in dep_name or 'Parer' in dep_display:
                    vals['payroll_job_type'] = 'parer'
                elif 'Sheller Manual' in dep_name or 'Sheller Manual' in dep_display:
                    vals['payroll_job_type'] = 'sheller_manual'
                elif 'Sheller Mesin' in dep_name or 'Sheller Mesin' in dep_display:
                    vals['payroll_job_type'] = 'sheller_mesin'
                elif 'RMP' in dep_name or 'Raw Material Preparation' in dep_name or 'RMP' in dep_display or 'Raw Material Preparation' in dep_display:
                    vals['payroll_job_type'] = 'rmp'
        return super(HrEmployee, self).create(vals_list)

    def write(self, vals):
        if 'department_id' in vals and 'payroll_job_type' not in vals:
            dep = self.env['hr.department'].browse(vals['department_id'])
            dep_name = dep.name or ''
            dep_display = dep.display_name or ''
            if 'Parer' in dep_name or 'Parer' in dep_display:
                vals['payroll_job_type'] = 'parer'
            elif 'Sheller Manual' in dep_name or 'Sheller Manual' in dep_display:
                vals['payroll_job_type'] = 'sheller_manual'
            elif 'Sheller Mesin' in dep_name or 'Sheller Mesin' in dep_display:
                vals['payroll_job_type'] = 'sheller_mesin'
            elif 'RMP' in dep_name or 'Raw Material Preparation' in dep_name or 'RMP' in dep_display or 'Raw Material Preparation' in dep_display:
                vals['payroll_job_type'] = 'rmp'
        return super(HrEmployee, self).write(vals)

    def init(self):
        super(HrEmployee, self).init()
        self.env.cr.execute("SELECT column_name FROM information_schema.columns WHERE table_name='hr_employee' AND column_name='payroll_job_type'")
        if self.env.cr.fetchone():
            employees = self.env['hr.employee'].search([('payroll_job_type', '=', False)])
            for employee in employees:
                dep_name = employee.department_id.name or ''
                dep_display = employee.department_id.display_name or ''
                if 'Parer' in dep_name or 'Parer' in dep_display:
                    employee.payroll_job_type = 'parer'
                elif 'Sheller Manual' in dep_name or 'Sheller Manual' in dep_display:
                    employee.payroll_job_type = 'sheller_manual'
                elif 'Sheller Mesin' in dep_name or 'Sheller Mesin' in dep_display:
                    employee.payroll_job_type = 'sheller_mesin'
                elif 'RMP' in dep_name or 'Raw Material Preparation' in dep_name or 'RMP' in dep_display or 'Raw Material Preparation' in dep_display:
                    employee.payroll_job_type = 'rmp'

    @api.depends('department_id')
    def _compute_payroll_worker_type(self):
        for employee in self:
            dep_name = employee.department_id.name or ''
            dep_display = employee.department_id.display_name or ''
            if 'Parer' in dep_name or 'Parer' in dep_display:
                employee.payroll_worker_type = 'parer'
            elif 'Sheller Manual' in dep_name or 'Sheller Manual' in dep_display:
                employee.payroll_worker_type = 'sheller_manual'
            elif 'Sheller Mesin' in dep_name or 'Sheller Mesin' in dep_display:
                employee.payroll_worker_type = 'sheller_mesin'
            elif 'RMP' in dep_name or 'Raw Material Preparation' in dep_name or 'RMP' in dep_display or 'Raw Material Preparation' in dep_display:
                employee.payroll_worker_type = 'rmp'
            else:
                employee.payroll_worker_type = False

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
