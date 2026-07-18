# -*- coding: utf-8 -*-
from odoo import api, fields, models, _
from odoo.exceptions import ValidationError, UserError

class CoconutPayrollTariff(models.Model):
    _name = 'coconut.payroll.tariff'
    _description = 'Tarif Pekerjaan'

    name = fields.Char(
        string='Nama Tarif',
        required=True,
    )
    
    worker_type = fields.Selection([
        ('parer', 'Parer'),
        ('sheller_manual', 'Sheller Manual'),
        ('sheller_mesin', 'Sheller Mesin'),
    ], string='Jenis Pekerja', required=True)

    work_type = fields.Selection([
        ('sheller_prod', 'Sheller Production'),
        ('parer_prod', 'Parer Production'),
        ('white_meat', 'White Meat Kopra'),
        ('bad_meat', 'Bad Meat'),
        ('bad_meat_sunday', 'Bad Meat Sunday'),
        ('other', 'Other'),
    ], string='Jenis Pekerjaan', required=True)

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
        string='Tarif (Rp)',
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

    @api.constrains('rate')
    def _check_rate(self):
        for record in self:
            if record.rate < 0:
                raise ValidationError(_("Tarif tidak boleh negatif."))

    @api.constrains('date_start', 'date_end')
    def _check_dates(self):
        for record in self:
            if record.date_start and record.date_end and record.date_start > record.date_end:
                raise ValidationError(_("Tanggal mulai tidak boleh melebihi tanggal selesai."))

    @api.model
    def get_applicable_tariff(self, company, worker_type, work_type, date):
        domain = [
            ('worker_type', '=', worker_type),
            ('work_type', '=', work_type),
            ('date_start', '<=', date),
            ('date_end', '>=', date),
            ('active', '=', True),
        ]
        
        company_id = company.id if hasattr(company, 'id') else company
        
        # Prefer company tariff, then try fallback with false company (for global tariffs)
        tariffs = self.search(domain + [('company_id', '=', company_id)])
        if not tariffs:
            tariffs = self.search(domain + [('company_id', '=', False)])
            
        if not tariffs:
            return False

        if len(tariffs) > 1:
            raise UserError(_("Ditemukan beberapa tarif yang tumpang tindih untuk pekerjaan ini pada tanggal %s.") % date)
            
        return tariffs[0]

    @api.model_create_multi
    def create(self, vals_list):
        if not self.env.su and not self.env.user.has_group('coconut_payroll.group_coconut_payroll_manager'):
            raise UserError(_("Hanya Manager Penggajian yang dapat mengelola tarif pekerjaan."))
        return super().create(vals_list)

    def write(self, vals):
        if not self.env.su and not self.env.user.has_group('coconut_payroll.group_coconut_payroll_manager'):
            raise UserError(_("Hanya Manager Penggajian yang dapat mengelola tarif pekerjaan."))
        return super().write(vals)

    def unlink(self):
        if not self.env.su and not self.env.user.has_group('coconut_payroll.group_coconut_payroll_manager'):
            raise UserError(_("Hanya Manager Penggajian yang dapat mengelola tarif pekerjaan."))
        return super().unlink()
