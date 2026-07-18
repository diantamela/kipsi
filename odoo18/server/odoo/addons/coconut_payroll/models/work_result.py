# -*- coding: utf-8 -*-
from odoo import api, fields, models, _
from odoo.exceptions import ValidationError, UserError

class CoconutWorkResult(models.Model):
    _name = 'coconut.work.result'
    _description = 'Hasil Kerja Pekerja'
    _order = 'date desc, id desc'

    work_sheet_id = fields.Many2one(
        'coconut.work.sheet',
        string='Lembar Kerja',
        required=True,
        ondelete='restrict',
        index=True,
    )

    date = fields.Date(
        string='Tanggal',
        related='work_sheet_id.date',
        store=True,
        readonly=True,
    )

    employee_id = fields.Many2one(
        'hr.employee',
        string='Karyawan',
        required=True,
        index=True,
    )

    worker_type = fields.Selection(
        related='work_sheet_id.worker_type',
        store=True,
        readonly=True,
    )

    day_type = fields.Selection(
        related='work_sheet_id.day_type',
        store=True,
        readonly=True,
    )

    quantity_kg = fields.Float(
        string='Kuantitas (Kg)',
        required=True,
        default=0.0,
    )

    company_id = fields.Many2one(
        'res.company',
        related='work_sheet_id.company_id',
        store=True,
        readonly=True,
    )

    currency_id = fields.Many2one(
        'res.currency',
        related='company_id.currency_id',
        store=True,
        readonly=True,
    )

    wage_rate = fields.Float(
        string='Tarif Upah',
        readonly=True,
        default=0.0,
    )

    basic_wage = fields.Monetary(
        string='Upah Dasar',
        currency_field='currency_id',
        readonly=True,
        default=0.0,
    )

    premium = fields.Monetary(
        string='Premi',
        currency_field='currency_id',
        readonly=True,
        default=0.0,
    )

    total_wage = fields.Monetary(
        string='Total Upah',
        currency_field='currency_id',
        readonly=True,
        default=0.0,
    )

    recap_line_id = fields.Many2one(
        'coconut.payroll.line',
        string='Slip Gaji Terkait',
        copy=False,
        readonly=True,
        index=True,
        ondelete='restrict',
    )

    state = fields.Selection([
        ('draft', 'Draft'),
        ('validated', 'Validated'),
        ('processed', 'Processed'),
        ('paid', 'Paid'),
        ('cancelled', 'Cancelled'),
    ], string='Status', default='draft', required=True, index=True)

    @api.constrains('quantity_kg')
    def _check_quantity(self):
        for record in self:
            if record.quantity_kg < 0:
                raise ValidationError(_("Kuantitas tidak boleh negatif."))

    @api.constrains('employee_id', 'worker_type')
    def _check_employee_worker_type(self):
        for record in self:
            if record.employee_id and record.worker_type:
                dep_name = record.employee_id.department_id.name or ''
                dep_display = record.employee_id.department_id.display_name or ''
                dep_keyword = {
                    'parer': 'Parer',
                    'sheller_manual': 'Sheller Manual',
                    'sheller_mesin': 'Sheller Mesin',
                }.get(record.worker_type, '')

                if dep_keyword not in dep_name and dep_keyword not in dep_display:
                    labels = {
                        'parer': 'Parer',
                        'sheller_manual': 'Sheller Manual',
                        'sheller_mesin': 'Sheller Mesin',
                    }
                    raise ValidationError(_("Karyawan %s memiliki departemen '%s', tidak cocok dengan Jenis Pekerja lembar kerja '%s' (harus mengandung '%s').") % (
                        record.employee_id.name,
                        dep_display or dep_name or _('Tanpa Departemen'),
                        labels.get(record.worker_type, record.worker_type),
                        dep_keyword
                    ))

    def _calculate_and_snapshot_wages(self):
        for record in self:
            sheet = record.work_sheet_id
            if not sheet:
                continue

            # Match salary rule
            rule = self.env['coconut.salary.rule'].search([
                ('worker_type', '=', sheet.worker_type),
                ('day_type', '=', sheet.day_type),
                ('start_date', '<=', sheet.date),
                ('end_date', '>=', sheet.date),
                ('min_quantity', '<=', record.quantity_kg),
                ('max_quantity', '>=', record.quantity_kg),
                ('company_id', '=', record.company_id.id),
            ], limit=1)

            if not rule:
                raise ValidationError(_("Aturan upah tidak ditemukan untuk jenis pekerja dan jumlah produksi ini."))

            # Match premium rule (optional)
            p_rule = self.env['coconut.premium.rule'].search([
                ('worker_type', '=', sheet.worker_type),
                ('day_type', '=', sheet.day_type),
                ('start_date', '<=', sheet.date),
                ('end_date', '>=', sheet.date),
                ('min_quantity', '<=', record.quantity_kg),
                ('max_quantity', '>=', record.quantity_kg),
                ('company_id', '=', record.company_id.id),
            ], limit=1)

            record.wage_rate = rule.wage_rate
            record.basic_wage = record.quantity_kg * rule.wage_rate
            record.premium = p_rule.premium_amount if p_rule else 0.0
            record.total_wage = record.basic_wage + record.premium

    def write(self, vals):
        if self.env.context.get('bypass_work_result_lock'):
            return super().write(vals)

        for record in self:
            if record.state in ['validated', 'processed', 'paid']:
                raise ValidationError(_("Hasil kerja yang sudah divalidasi, diproses, atau dibayar tidak dapat diubah."))
        return super().write(vals)

    def unlink(self):
        for record in self:
            if record.state in ['validated', 'processed', 'paid']:
                raise ValidationError(_("Hasil kerja yang sudah divalidasi, diproses, atau dibayar tidak dapat dihapus."))
        return super().unlink()
