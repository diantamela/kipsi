# -*- coding: utf-8 -*-
import math
from odoo import api, fields, models, _
from odoo.exceptions import ValidationError, UserError

class CoconutPayrollLine(models.Model):
    _name = 'coconut.payroll.line'
    _description = 'Slip Gaji Karyawan'
    _order = 'employee_id'

    period_id = fields.Many2one(
        'coconut.payroll.period',
        string='Periode Penggajian',
        required=True,
        ondelete='cascade',
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

    work_result_ids = fields.One2many(
        'coconut.work.result',
        'payroll_line_id',
        string='Hasil Kerja',
    )

    total_quantity = fields.Float(
        string='Total Kuantitas (Kg)',
        compute='_compute_all_fields',
        store=True,
    )

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

    basic_wage = fields.Monetary(
        string='Upah Dasar',
        currency_field='currency_id',
        compute='_compute_all_fields',
        store=True,
    )

    premium_method = fields.Selection([
        ('manual', 'Manual'),
        ('automatic', 'Aturan Otomatis'),
    ], string='Metode Premi', default='manual', required=True)

    target_premium = fields.Monetary(
        string='Premi Target',
        currency_field='currency_id',
        default=0.0,
    )

    additional_hours = fields.Float(
        string='Jam Tambahan',
        default=0.0,
    )

    daily_addition = fields.Monetary(
        string='Tambahan Harian',
        currency_field='currency_id',
        compute='_compute_all_fields',
        store=True,
    )

    overtime_hours = fields.Float(
        string='Jam Lembur',
        default=0.0,
    )

    overtime_amount = fields.Monetary(
        string='Upah Lembur',
        currency_field='currency_id',
        compute='_compute_all_fields',
        store=True,
    )

    arrears = fields.Monetary(
        string='Rapel',
        currency_field='currency_id',
        default=0.0,
    )

    other_income = fields.Monetary(
        string='Pendapatan Lain',
        currency_field='currency_id',
        default=0.0,
    )

    gross_income_before_rounding = fields.Monetary(
        string='Gross Sebelum Pembulatan',
        currency_field='currency_id',
        compute='_compute_all_fields',
        store=True,
    )

    gross_income = fields.Monetary(
        string='Gross Akhir',
        currency_field='currency_id',
        compute='_compute_all_fields',
        store=True,
    )

    salary_overpayment_deduction = fields.Monetary(
        string='Potongan Kelebihan Gaji',
        currency_field='currency_id',
        default=0.0,
    )

    tool_deduction = fields.Monetary(
        string='Potongan Alat',
        currency_field='currency_id',
        default=0.0,
    )

    axe_blade_deduction = fields.Monetary(
        string='Potongan Mata Pisau/Kapak',
        currency_field='currency_id',
        default=0.0,
    )

    sack_deduction = fields.Monetary(
        string='Potongan Karung',
        currency_field='currency_id',
        default=0.0,
    )

    other_deduction = fields.Monetary(
        string='Potongan Lain',
        currency_field='currency_id',
        default=0.0,
    )

    total_deduction = fields.Monetary(
        string='Total Potongan',
        currency_field='currency_id',
        compute='_compute_all_fields',
        store=True,
    )

    net_before_rounding = fields.Monetary(
        string='Net Sebelum Pembulatan',
        currency_field='currency_id',
        compute='_compute_all_fields',
        store=True,
    )

    rounding_difference = fields.Monetary(
        string='Selisih Pembulatan',
        currency_field='currency_id',
        compute='_compute_all_fields',
        store=True,
    )

    net_income = fields.Monetary(
        string='Net Akhir',
        currency_field='currency_id',
        compute='_compute_all_fields',
        store=True,
    )

    notes = fields.Text(
        string='Catatan',
    )

    _sql_constraints = [
        ('period_employee_unique', 'unique(period_id, employee_id)', 'Karyawan hanya boleh memiliki satu slip gaji dalam satu periode!')
    ]

    def _round_down(self, amount, unit):
        if unit <= 0:
            return amount
        return math.floor(amount / unit) * unit

    @api.depends('work_result_ids.basic_wage', 'work_result_ids.quantity',
                 'target_premium', 'premium_method',
                 'additional_hours', 'overtime_hours', 'arrears', 'other_income',
                 'salary_overpayment_deduction', 'tool_deduction',
                 'axe_blade_deduction', 'sack_deduction', 'other_deduction',
                 'company_id', 'worker_type')
    def _compute_all_fields(self):
        for line in self:
            line.total_quantity = sum(line.work_result_ids.mapped('quantity'))
            line.basic_wage = sum(line.work_result_ids.mapped('basic_wage'))
            
            if line.premium_method == 'automatic':
                rule = self.env['coconut.payroll.premium.rule'].search([
                    ('worker_type', '=', line.worker_type),
                    ('company_id', '=', line.company_id.id),
                    ('minimum_quantity', '<=', line.total_quantity),
                    ('maximum_quantity', '>=', line.total_quantity),
                    ('date_start', '<=', line.period_id.date_start),
                    ('date_end', '>=', line.period_id.date_end),
                    ('active', '=', True)
                ], limit=1)
                if not rule:
                    raise ValidationError(_("Tidak ada aturan premi otomatis yang cocok untuk karyawan %s dengan kuantitas %s Kg.") % (line.employee_id.name, line.total_quantity))
                line.target_premium = rule.premium_amount

            daily_base = line.company_id.payroll_daily_base_wage or 65000.0
            std_hours = line.company_id.payroll_standard_hours or 7.0
            if std_hours > 0:
                line.daily_addition = line.additional_hours * (daily_base / std_hours)
            else:
                line.daily_addition = 0.0

            ot_rate = line.company_id.payroll_overtime_rate or 12000.0
            line.overtime_amount = line.overtime_hours * ot_rate

            line.total_deduction = (
                line.salary_overpayment_deduction +
                line.tool_deduction +
                line.axe_blade_deduction +
                line.sack_deduction +
                line.other_deduction
            )

            rounding_unit = line.company_id.payroll_rounding_unit or 1000.0

            if line.worker_type == 'sheller':
                line.gross_income_before_rounding = (
                    line.basic_wage +
                    line.target_premium +
                    line.daily_addition +
                    line.overtime_amount +
                    line.arrears +
                    line.other_income
                )
                line.gross_income = line.gross_income_before_rounding
                line.net_before_rounding = line.gross_income - line.total_deduction
                line.net_income = line._round_down(line.net_before_rounding, rounding_unit)
                line.rounding_difference = line.net_before_rounding - line.net_income
            else:  # parer
                line.gross_income_before_rounding = (
                    line.basic_wage +
                    line.target_premium +
                    line.daily_addition +
                    line.overtime_amount +
                    line.arrears +
                    line.other_income
                )
                line.gross_income = line._round_down(line.gross_income_before_rounding, rounding_unit)
                line.net_before_rounding = line.gross_income_before_rounding - line.total_deduction
                line.net_income = line._round_down(line.gross_income - line.total_deduction, rounding_unit)
                line.rounding_difference = line.net_before_rounding - line.net_income

    def write(self, vals):
        for line in self:
            if line.period_id.state in ['confirmed', 'paid', 'cancelled']:
                raise UserError(_("Slip gaji tidak dapat diubah karena periode penggajian terkait berstatus %s.") % line.period_id.state)
            if line.period_id.state == 'calculated':
                allowed_fields = {
                    'target_premium', 'premium_method', 'additional_hours',
                    'overtime_hours', 'arrears', 'other_income',
                    'salary_overpayment_deduction', 'tool_deduction',
                    'axe_blade_deduction', 'sack_deduction', 'other_deduction',
                    'notes'
                }
                if any(k not in allowed_fields for k in vals.keys()):
                    raise UserError(_("Pada status Calculated, hanya penambahan/potongan manual dan catatan yang dapat diubah."))
        res = super().write(vals)
        return res

    def unlink(self):
        for line in self:
            if line.period_id.state in ['confirmed', 'paid', 'cancelled']:
                raise UserError(_("Slip gaji tidak dapat dihapus karena periode penggajian terkait berstatus %s.") % line.period_id.state)
        return super().unlink()
