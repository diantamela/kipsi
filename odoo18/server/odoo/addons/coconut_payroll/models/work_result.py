# -*- coding: utf-8 -*-
from odoo import api, fields, models, _
from odoo.exceptions import ValidationError, UserError

class CoconutWorkResult(models.Model):
    _name = 'coconut.work.result'
    _description = 'Hasil Kerja Pekerja'
    _order = 'date desc, id desc'

    date = fields.Date(
        string='Tanggal',
        required=True,
        default=fields.Date.context_today,
    )

    employee_id = fields.Many2one(
        'hr.employee',
        string='Karyawan',
        required=True,
        index=True,
    )

    worker_type = fields.Selection([
        ('sheller', 'Sheller'),
        ('parer', 'Parer'),
    ], string='Jenis Pekerja', required=True)

    work_type = fields.Selection([
        ('sheller_prod', 'Sheller Production'),
        ('parer_prod', 'Parer Production'),
        ('white_meat', 'White Meat Kopra'),
        ('bad_meat', 'Bad Meat'),
        ('bad_meat_sunday', 'Bad Meat Sunday'),
        ('other', 'Other'),
    ], string='Jenis Pekerjaan', required=True)

    quantity = fields.Float(
        string='Kuantitas (Kg)',
        required=True,
        default=0.0,
    )

    uom_name = fields.Char(
        string='Satuan',
        default='Kg',
        readonly=True,
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

    rate = fields.Monetary(
        string='Tarif',
        currency_field='currency_id',
        required=True,
        default=0.0,
    )

    basic_wage = fields.Monetary(
        string='Upah Dasar',
        currency_field='currency_id',
        compute='_compute_basic_wage',
        store=True,
    )

    premium = fields.Monetary(
        string='Premi',
        currency_field='currency_id',
        default=0.0,
    )

    source_reference = fields.Char(
        string='Referensi Sumber',
    )

    payroll_line_id = fields.Many2one(
        'coconut.payroll.line',
        string='Slip Gaji Terkait',
        copy=False,
        readonly=True,
        index=True,
        ondelete='restrict',
    )

    payroll_period_id = fields.Many2one(
        comodel_name='coconut.payroll.period',
        string='Periode Penggajian',
        related='payroll_line_id.period_id',
        store=True,
        readonly=True,
    )

    state = fields.Selection([
        ('draft', 'Draft'),
        ('validated', 'Validated'),
        ('paid', 'Paid'),
        ('cancelled', 'Cancelled'),
    ], string='Status', default='draft', required=True, index=True)

    notes = fields.Text(
        string='Catatan',
    )

    @api.depends('quantity', 'rate')
    def _compute_basic_wage(self):
        for record in self:
            record.basic_wage = record.quantity * record.rate

    @api.constrains('quantity')
    def _check_quantity(self):
        for record in self:
            if record.quantity < 0:
                raise ValidationError(_("Kuantitas tidak boleh negatif."))

    @api.constrains('rate')
    def _check_rate(self):
        for record in self:
            if record.rate < 0:
                raise ValidationError(_("Tarif tidak boleh negatif."))

    @api.constrains('employee_id', 'worker_type')
    def _check_employee_worker_type(self):
        for record in self:
            if record.employee_id:
                emp_type = record.employee_id.payroll_worker_type
                if emp_type != record.worker_type:
                    raise ValidationError(_("Karyawan %s memiliki Jenis Penggajian '%s', tidak cocok dengan Jenis Pekerja '%s'.") % (
                        record.employee_id.name,
                        dict(record.employee_id._fields['payroll_worker_type'].selection).get(emp_type) or emp_type,
                        dict(record._fields['worker_type'].selection).get(record.worker_type) or record.worker_type
                    ))

    @api.onchange('worker_type', 'work_type', 'date', 'company_id')
    def _onchange_work_details(self):
        if self.worker_type and self.work_type and self.date:
            try:
                tariff = self.env['coconut.payroll.tariff'].get_applicable_tariff(
                    self.company_id, self.worker_type, self.work_type, self.date
                )
                if tariff:
                    self.rate = tariff.rate
                else:
                    self.rate = 0.0
            except UserError as e:
                raise e

    def write(self, vals):
        if self.env.context.get('bypass_work_result_lock'):
            return super().write(vals)
            
        for record in self:
            if record.state == 'paid':
                raise ValidationError(_("Hasil kerja yang sudah dibayar (Paid) tidak dapat diubah."))
            if record.payroll_line_id and record.payroll_line_id.period_id.state in ['confirmed', 'paid']:
                raise ValidationError(_("Hasil kerja tidak dapat diubah karena periode penggajian terkait sudah berstatus Confirmed atau Paid."))
        return super().write(vals)

    def unlink(self):
        for record in self:
            if record.state == 'paid':
                raise ValidationError(_("Hasil kerja yang sudah dibayar (Paid) tidak dapat dihapus."))
            if record.payroll_line_id and record.payroll_line_id.period_id.state in ['confirmed', 'paid']:
                raise ValidationError(_("Hasil kerja tidak dapat dihapus karena periode penggajian terkait sudah berstatus Confirmed atau Paid."))
        return super().unlink()

    def action_validate(self):
        if not self.env.su and not (self.env.user.has_group('coconut_payroll.group_coconut_payroll_supervisor') or 
                                    self.env.user.has_group('coconut_payroll.group_coconut_payroll_manager')):
            raise UserError(_("Hanya Supervisor atau Manager Penggajian yang dapat memvalidasi hasil kerja."))
        for record in self:
            if record.state != 'draft':
                raise UserError(_("Hanya hasil kerja berstatus Draft yang dapat divalidasi."))
            if record.quantity <= 0:
                raise ValidationError(_("Kuantitas harus lebih besar dari 0."))
        self.with_context(bypass_work_result_lock=True).write({'state': 'validated'})

    def action_draft(self):
        for record in self:
            if record.state == 'paid':
                raise UserError(_("Hasil kerja yang sudah dibayar (Paid) tidak dapat diubah ke Draft."))
            if record.payroll_line_id and record.payroll_line_id.period_id.state in ['confirmed', 'paid']:
                raise UserError(_("Hasil kerja tidak dapat diubah ke Draft karena periode penggajian terkait sudah berstatus Confirmed atau Paid."))
        self.with_context(bypass_work_result_lock=True).write({'state': 'draft'})

    def action_cancel(self):
        for record in self:
            if record.state == 'paid':
                raise UserError(_("Hasil kerja yang sudah dibayar tidak dapat dibatalkan."))
        self.with_context(bypass_work_result_lock=True).write({'state': 'cancelled'})
