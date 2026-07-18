# -*- coding: utf-8 -*-
from odoo import api, fields, models, _
from odoo.exceptions import ValidationError

class CoconutEmployeeLoan(models.Model):
    _name = 'coconut.employee.loan'
    _description = 'Pinjaman Karyawan'
    _order = 'id desc'

    employee_id = fields.Many2one(
        'hr.employee',
        string='Karyawan',
        required=True,
        index=True,
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

    loan_amount = fields.Monetary(
        string='Jumlah Pinjaman',
        currency_field='currency_id',
        required=True,
        default=0.0,
    )

    installment_amount = fields.Monetary(
        string='Cicilan Per Periode',
        currency_field='currency_id',
        required=True,
        default=0.0,
    )

    remaining_amount = fields.Monetary(
        string='Sisa Pinjaman',
        currency_field='currency_id',
        compute='_compute_remaining_amount',
        store=True,
    )

    state = fields.Selection([
        ('draft', 'Draft'),
        ('active', 'Aktif'),
        ('paid', 'Lunas'),
        ('cancelled', 'Batal'),
    ], string='Status', default='draft', required=True, index=True)

    installment_line_ids = fields.One2many(
        'coconut.loan.installment',
        'loan_id',
        string='Histori Cicilan',
    )

    @api.depends('loan_amount', 'installment_line_ids.amount', 'installment_line_ids.state')
    def _compute_remaining_amount(self):
        for record in self:
            posted_payments = sum(record.installment_line_ids.filtered(lambda l: l.state == 'posted').mapped('amount'))
            record.remaining_amount = max(0.0, record.loan_amount - posted_payments)
            if record.state == 'active' and record.remaining_amount <= 0.0:
                record.state = 'paid'

    def action_active(self):
        for record in self:
            if record.state != 'draft':
                raise ValidationError(_("Hanya pinjaman draf yang dapat diaktifkan."))
            if record.loan_amount <= 0:
                raise ValidationError(_("Jumlah pinjaman harus lebih besar dari 0."))
            if record.installment_amount <= 0:
                raise ValidationError(_("Jumlah cicilan harus lebih besar dari 0."))
            record.state = 'active'

    def action_draft(self):
        for record in self:
            if record.installment_line_ids.filtered(lambda l: l.state == 'posted'):
                raise ValidationError(_("Pinjaman tidak dapat diubah ke draf karena sudah ada cicilan terbayar."))
            record.state = 'draft'

    def action_cancel(self):
        for record in self:
            if record.installment_line_ids.filtered(lambda l: l.state == 'posted'):
                raise ValidationError(_("Pinjaman tidak dapat dibatalkan karena sudah ada cicilan terbayar."))
            record.state = 'cancelled'


class CoconutLoanInstallment(models.Model):
    _name = 'coconut.loan.installment'
    _description = 'Cicilan Pinjaman Karyawan'
    _order = 'date desc, id desc'

    loan_id = fields.Many2one(
        'coconut.employee.loan',
        string='Pinjaman',
        required=True,
        ondelete='restrict',
        index=True,
    )

    recap_line_id = fields.Many2one(
        'coconut.payroll.line',
        string='Slip Gaji Terkait',
        ondelete='restrict',
        index=True,
    )

    date = fields.Date(
        string='Tanggal',
        required=True,
        default=fields.Date.context_today,
    )

    company_id = fields.Many2one(
        'res.company',
        related='loan_id.company_id',
        store=True,
        readonly=True,
    )

    currency_id = fields.Many2one(
        'res.currency',
        related='loan_id.currency_id',
        store=True,
        readonly=True,
    )

    amount = fields.Monetary(
        string='Jumlah Cicilan',
        currency_field='currency_id',
        required=True,
        default=0.0,
    )

    state = fields.Selection([
        ('draft', 'Draft'),
        ('posted', 'Posted'),
        ('cancelled', 'Batal'),
    ], string='Status', default='draft', required=True, index=True)
