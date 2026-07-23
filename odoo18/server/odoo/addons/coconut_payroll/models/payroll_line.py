# -*- coding: utf-8 -*-
from odoo import api, fields, models, tools, _
from odoo.exceptions import ValidationError, UserError

class CoconutPayrollLine(models.Model):
    _name = 'coconut.payroll.line'
    _description = 'Slip Gaji Karyawan'
    _order = 'employee_id'

    recap_id = fields.Many2one(
        'coconut.payroll.recap',
        string='Rekapitulasi Penggajian',
        required=False,
        ondelete='restrict',
        index=True,
    )

    rmp_recap_id = fields.Many2one(
        'coconut.payroll.rmp',
        string='Rekapitulasi Penggajian RMP',
        required=False,
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

    department_id = fields.Many2one(
        'hr.department',
        related='employee_id.department_id',
        string='Departemen',
        store=True,
        readonly=True,
    )

    worker_type = fields.Selection([
        ('parer', 'Parer'),
        ('sheller_manual', 'Sheller Manual'),
        ('sheller_mesin', 'Sheller Mesin'),
        ('rmp', 'RMP'),
    ], string='Jenis Pekerja', required=True)

    payroll_type = fields.Selection([
        ('harian', 'Harian'),
        ('borongan', 'Borongan'),
    ], string='Jenis Payroll', compute='_compute_payroll_type', store=True)

    @api.depends('worker_type')
    def _compute_payroll_type(self):
        for record in self:
            if record.worker_type == 'rmp':
                record.payroll_type = 'harian'
            else:
                record.payroll_type = 'borongan'

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

    hari_hadir = fields.Integer(string='Hari Hadir', default=0)
    hari_alpha = fields.Integer(string='Hari Alpha', default=0)
    jam_kerja = fields.Float(string='Jam Kerja', default=0.0)
    jam_lembur = fields.Float(string='Jam Lembur', default=0.0)
    terlambat = fields.Integer(string='Terlambat (Hari)', default=0)
    pulang_cepat = fields.Integer(string='Pulang Cepat (Hari)', default=0)
    wage_pokok = fields.Monetary(string='Gaji Pokok', currency_field='currency_id', default=0.0)
    wage_lembur = fields.Monetary(string='Total Lembur', currency_field='currency_id', default=0.0)
    premi_kehadiran = fields.Monetary(string='Premi Kehadiran', currency_field='currency_id', default=0.0)
    premi_disiplin = fields.Monetary(string='Premi Disiplin', currency_field='currency_id', default=0.0)
    uang_makan = fields.Monetary(string='Uang Makan', currency_field='currency_id', default=0.0)
    potongan = fields.Monetary(string='Potongan', currency_field='currency_id', default=0.0)

    period_display = fields.Char(string='Periode', compute='_compute_period_display')

    @api.depends('recap_id.date_start', 'recap_id.date_end', 'rmp_recap_id.date_start', 'rmp_recap_id.date_end')
    def _compute_period_display(self):
        for line in self:
            if line.recap_id and line.recap_id.date_start and line.recap_id.date_end:
                line.period_display = f"{line.recap_id.date_start} - {line.recap_id.date_end}"
            elif line.rmp_recap_id and line.rmp_recap_id.date_start and line.rmp_recap_id.date_end:
                line.period_display = f"{line.rmp_recap_id.date_start} - {line.rmp_recap_id.date_end}"
            else:
                line.period_display = ""

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
        ('recap_employee_unique', 'unique(recap_id, employee_id)', 'Karyawan hanya boleh memiliki satu slip gaji dalam satu rekapitulasi Borongan!'),
        ('rmp_recap_employee_unique', 'unique(rmp_recap_id, employee_id)', 'Karyawan hanya boleh memiliki satu slip gaji dalam satu rekapitulasi Harian!')
    ]

    def unlink(self):
        for line in self:
            if line.recap_id and line.recap_id.state in ['approved', 'paid']:
                raise UserError(_("Slip gaji tidak dapat dihapus karena rekapitulasi terkait sudah disetujui atau lunas."))
            if line.rmp_recap_id and line.rmp_recap_id.state in ['approved', 'paid']:
                raise UserError(_("Slip gaji tidak dapat dihapus karena rekapitulasi terkait sudah disetujui atau lunas."))
        return super().unlink()

    def action_print_payslip(self):
        self.ensure_one()
        return self.env.ref('coconut_payroll.action_report_payslip').report_action(self)


class CoconutPayrollLineHarian(models.Model):
    _name = 'coconut.payroll.line.harian'
    _inherit = 'coconut.payroll.line'
    _description = 'Slip Gaji Harian'
    _auto = False

    def init(self):
        tools.drop_view_if_exists(self.env.cr, self._table)
        self.env.cr.execute("""
            CREATE or REPLACE VIEW %s as (
                SELECT * FROM coconut_payroll_line WHERE payroll_type = 'harian'
            )
        """ % self._table)

    def action_print_payslip(self):
        self.ensure_one()
        return self.env.ref('coconut_payroll.action_report_payslip_harian').report_action(self)


class CoconutPayrollLineBorongan(models.Model):
    _name = 'coconut.payroll.line.borongan'
    _inherit = 'coconut.payroll.line'
    _description = 'Slip Gaji Borongan'
    _auto = False

    def init(self):
        tools.drop_view_if_exists(self.env.cr, self._table)
        self.env.cr.execute("""
            CREATE or REPLACE VIEW %s as (
                SELECT * FROM coconut_payroll_line WHERE payroll_type = 'borongan'
            )
        """ % self._table)

    def action_print_payslip(self):
        self.ensure_one()
        return self.env.ref('coconut_payroll.action_report_payslip_borongan').report_action(self)
