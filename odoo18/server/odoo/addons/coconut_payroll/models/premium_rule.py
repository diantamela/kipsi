# -*- coding: utf-8 -*-
from odoo import api, fields, models, _
from odoo.exceptions import ValidationError, UserError

class CoconutPayrollPremiumRule(models.Model):
    _name = 'coconut.payroll.premium.rule'
    _description = 'Aturan Premi (Lama/Deprecated)'

    name = fields.Char(
        string='Nama Aturan Premi',
        required=True,
    )
    worker_type = fields.Selection([
        ('parer', 'Parer'),
        ('sheller_manual', 'Sheller Manual'),
        ('sheller_mesin', 'Sheller Mesin'),
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
    )
    currency_id = fields.Many2one(
        'res.currency',
        related='company_id.currency_id',
    )
    premium_amount = fields.Monetary(
        string='Jumlah Premi (Rp)',
        currency_field='currency_id',
        required=True,
    )
    date_start = fields.Date(string='Tanggal Mulai')
    date_end = fields.Date(string='Tanggal Selesai')
    active = fields.Boolean(string='Aktif', default=True)


class CoconutPremiumRule(models.Model):
    _name = 'coconut.premium.rule'
    _description = 'Aturan Premi Baru'
    _order = 'start_date desc, id desc'

    worker_type = fields.Selection([
        ('parer', 'Parer'),
        ('sheller_manual', 'Sheller Manual'),
        ('sheller_mesin', 'Sheller Mesin'),
    ], string='Jenis Pekerja', required=True)

    day_type = fields.Selection([
        ('biasa', 'Hari Biasa'),
        ('merah', 'Hari Merah'),
    ], string='Tipe Hari', required=True)

    min_quantity = fields.Float(
        string='Batas Kuantitas Minimal (Kg)',
        required=True,
        default=0.0,
    )

    max_quantity = fields.Float(
        string='Batas Kuantitas Maksimal (Kg)',
        required=True,
        default=999999.0,
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
        string='Jumlah Premi',
        currency_field='currency_id',
        required=True,
        default=0.0,
    )

    start_date = fields.Date(
        string='Tanggal Mulai',
        required=True,
    )

    end_date = fields.Date(
        string='Tanggal Selesai',
        required=True,
    )

    @api.constrains('worker_type', 'day_type', 'min_quantity', 'max_quantity', 'start_date', 'end_date', 'company_id')
    def _check_overlap(self):
        for record in self:
            if not record.start_date or not record.end_date:
                continue
            if record.start_date > record.end_date:
                raise ValidationError(_("Tanggal mulai tidak boleh melebihi tanggal selesai."))
            if record.min_quantity < 0 or record.max_quantity < 0:
                raise ValidationError(_("Batas kuantitas tidak boleh negatif."))
            if record.min_quantity > record.max_quantity:
                raise ValidationError(_("Batas kuantitas minimal tidak boleh melebihi batas maksimal."))

            # Search for overlapping rules
            overlap = self.search([
                ('id', '!=', record.id),
                ('company_id', '=', record.company_id.id),
                ('worker_type', '=', record.worker_type),
                ('day_type', '=', record.day_type),
                ('start_date', '<=', record.end_date),
                ('end_date', '>=', record.start_date),
                ('min_quantity', '<=', record.max_quantity),
                ('max_quantity', '>=', record.min_quantity),
            ], limit=1)

            if overlap:
                raise ValidationError(_(
                    "Aturan premi tumpang tindih dengan aturan lain (ID: %s, Tanggal: %s s.d %s, Qty: %s s.d %s)."
                ) % (
                    overlap.id,
                    overlap.start_date,
                    overlap.end_date,
                    overlap.min_quantity,
                    overlap.max_quantity
                ))
