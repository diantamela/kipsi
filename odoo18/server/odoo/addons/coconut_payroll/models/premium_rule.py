# -*- coding: utf-8 -*-
from odoo import api, fields, models, _
from odoo.exceptions import ValidationError, UserError

class CoconutPayrollPremiumRule(models.Model):
    _name = 'coconut.payroll.premium.rule'
    _description = 'Aturan Premi'

    name = fields.Char(
        string='Nama Aturan Premi',
        required=True,
    )

    worker_type = fields.Selection([
        ('sheller', 'Sheller'),
        ('parer', 'Parer'),
    ], string='Jenis Pekerja', required=True)

    minimum_quantity = fields.Float(
        string='Jumlah Minimal (Kg)',
        required=True,
    )

    maximum_quantity = fields.Float(
        string='Jumlah Maksimal (Kg)',
        required=True,
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

    premium_amount = fields.Monetary(
        string='Jumlah Premi (Rp)',
        currency_field='currency_id',
        required=True,
    )

    date_start = fields.Date(
        string='Tanggal Mulai',
        required=True,
    )

    date_end = fields.Date(
        string='Tanggal Selesai',
        required=True,
    )

    active = fields.Boolean(
        string='Aktif',
        default=True,
    )

    @api.constrains('minimum_quantity', 'maximum_quantity')
    def _check_quantities(self):
        for record in self:
            if record.minimum_quantity < 0 or record.maximum_quantity < 0:
                raise ValidationError(_("Jumlah minimal dan maksimal tidak boleh negatif."))
            if record.minimum_quantity > record.maximum_quantity:
                raise ValidationError(_("Jumlah minimal tidak boleh melebihi jumlah maksimal."))

    @api.constrains('premium_amount')
    def _check_premium_amount(self):
        for record in self:
            if record.premium_amount < 0:
                raise ValidationError(_("Jumlah premi tidak boleh negatif."))

    @api.constrains('date_start', 'date_end')
    def _check_dates(self):
        for record in self:
            if record.date_start and record.date_end and record.date_start > record.date_end:
                raise ValidationError(_("Tanggal mulai tidak boleh melebihi tanggal selesai."))

    @api.model_create_multi
    def create(self, vals_list):
        if not self.env.su and not self.env.user.has_group('coconut_payroll.group_coconut_payroll_manager'):
            raise UserError(_("Hanya Manager Penggajian yang dapat mengelola aturan premi."))
        return super().create(vals_list)

    def write(self, vals):
        if not self.env.su and not self.env.user.has_group('coconut_payroll.group_coconut_payroll_manager'):
            raise UserError(_("Hanya Manager Penggajian yang dapat mengelola aturan premi."))
        return super().write(vals)

    def unlink(self):
        if not self.env.su and not self.env.user.has_group('coconut_payroll.group_coconut_payroll_manager'):
            raise UserError(_("Hanya Manager Penggajian yang dapat mengelola aturan premi."))
        return super().unlink()
