# -*- coding: utf-8 -*-
from odoo import api, fields, models, _
from odoo.exceptions import ValidationError, UserError

class CoconutPayrollLine(models.Model):
    _name = 'coconut.payroll.line'
    _description = 'Slip Gaji Karyawan'
    _order = 'employee_id'

    recap_id = fields.Many2one(
        'coconut.payroll.recap',
        string='Rekapitulasi Penggajian',
        required=True,
        ondelete='restrict',
        index=True,
    )

    period_id = fields.Many2one(
        'coconut.payroll.period',
        string='Periode Penggajian (Deprecated)',
        ondelete='restrict',
        index=True,
    )

    employee_id = fields.Many2one(
        'hr.employee',
        string='Karyawan',
        required=True,
        ondelete='restrict',
    )

    worker_type = fields.Selection([
        ('sheller', 'Sheller'),
        ('parer', 'Parer'),
    ], string='Jenis Pekerja', required=True)

    company_id = fields.Many2one(
        'res.company',
        string='Perusahaan',
        required=True,
        default=lambda self: self.env.company,
        index=True,
    )

    currency_id = fields.Many2one(
        'res.currency',
        related='company_id.currency_id',
        store=True,
        readonly=True,
    )

    work_result_ids = fields.One2many(
        'coconut.work.result',
        'recap_line_id',
        string='Hasil Kerja Harian',
    )

    total_quantity_kg = fields.Float(
        string='Total KG',
        default=0.0,
    )

    basic_wage = fields.Monetary(
        string='Upah Dasar',
        currency_field='currency_id',
        default=0.0,
    )

    premium = fields.Monetary(
        string='Premi',
        currency_field='currency_id',
        default=0.0,
    )

    gross_salary = fields.Monetary(
        string='Gaji Kotor',
        currency_field='currency_id',
        default=0.0,
    )

    loan_deduction = fields.Monetary(
        string='Potongan Pinjaman',
        currency_field='currency_id',
        default=0.0,
    )

    net_salary = fields.Monetary(
        string='Gaji Bersih',
        currency_field='currency_id',
        default=0.0,
    )

    # Deprecated fields kept to prevent period dependency crashes
    total_quantity = fields.Float(string='Total Qty (Deprecated)')
    gross_income = fields.Monetary(string='Gross (Deprecated)', currency_field='currency_id')
    total_deduction = fields.Monetary(string='Deduction (Deprecated)', currency_field='currency_id')
    net_income = fields.Monetary(string='Net (Deprecated)', currency_field='currency_id')
    premium_method = fields.Selection([('manual', 'Manual'), ('automatic', 'Automatic')], string='Metode Premi (Deprecated)', default='manual')
    target_premium = fields.Monetary(string='Premi Target (Deprecated)', currency_field='currency_id')
    additional_hours = fields.Float(string='Jam Tambahan (Deprecated)')
    daily_addition = fields.Monetary(string='Tambahan Harian (Deprecated)', currency_field='currency_id')
    overtime_hours = fields.Float(string='Jam Lembur (Deprecated)')
    overtime_amount = fields.Monetary(string='Upah Lembur (Deprecated)', currency_field='currency_id')
    arrears = fields.Monetary(string='Rapel (Deprecated)', currency_field='currency_id')
    other_income = fields.Monetary(string='Pendapatan Lain (Deprecated)', currency_field='currency_id')
    salary_overpayment_deduction = fields.Monetary(string='Potongan Kelebihan (Deprecated)', currency_field='currency_id')
    tool_deduction = fields.Monetary(string='Potongan Alat (Deprecated)', currency_field='currency_id')
    axe_blade_deduction = fields.Monetary(string='Potongan Kapak (Deprecated)', currency_field='currency_id')
    sack_deduction = fields.Monetary(string='Potongan Karung (Deprecated)', currency_field='currency_id')
    other_deduction = fields.Monetary(string='Potongan Lain (Deprecated)', currency_field='currency_id')
    rounding_difference = fields.Monetary(string='Selisih Pembulatan (Deprecated)', currency_field='currency_id')
    notes = fields.Text(string='Catatan (Deprecated)')

    _sql_constraints = [
        ('recap_employee_unique', 'unique(recap_id, employee_id)', 'Karyawan hanya boleh memiliki satu slip gaji dalam satu rekapitulasi!')
    ]

    def unlink(self):
        for line in self:
            if line.recap_id.state in ['approved', 'paid']:
                raise UserError(_("Slip gaji tidak dapat dihapus karena rekapitulasi terkait sudah disetujui atau lunas."))
        return super().unlink()
