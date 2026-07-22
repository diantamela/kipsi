# -*- coding: utf-8 -*-
from odoo import api, fields, models, _
from odoo.exceptions import UserError, ValidationError

class CoconutMaterialTerbuang(models.Model):
    _name = 'coconut.material.terbuang'
    _description = 'Material Terbuang'
    _order = 'name desc'
    _inherit = ['mail.thread', 'mail.activity.mixin']

    name = fields.Char(
        string='Nomor Transaksi',
        required=True, copy=False, readonly=True,
        default=lambda self: _('Baru'),
    )
    transfer_id = fields.Many2one(
        'coconut.manufacturing',
        string='Transfer Kelapa',
        required=True,
        domain=[('state', '=', 'done')],
        tracking=True,
    )
    product_id = fields.Many2one(
        'product.product',
        string='Produk',
        required=True,
        tracking=True,
    )
    qty = fields.Float(
        string='Kuantitas (Kg)',
        required=True,
        default=0.0,
        tracking=True,
    )
    operator_id = fields.Many2one(
        'hr.employee',
        string='Operator',
        required=True,
        tracking=True,
    )
    location_id = fields.Many2one(
        'stock.location',
        string='Lokasi Asal / Area Produksi',
        required=True,
        domain=[('usage', '=', 'internal')],
        tracking=True,
    )
    reason = fields.Selection([
        ('rusak', 'Rusak / Busuk'),
        ('tumpah', 'Tumpah / Hancur'),
        ('lainnya', 'Lainnya'),
    ], string='Alasan', required=True, default='rusak', tracking=True)

    notes = fields.Text(string='Keterangan')
    state = fields.Selection([
        ('draft', 'Draft'),
        ('done', 'Selesai'),
        ('cancelled', 'Dibatalkan'),
    ], string='Status', default='draft', required=True, tracking=True)

    stock_move_id = fields.Many2one('stock.move', string='Move: Material Terbuang', readonly=True, copy=False)

    @api.model_create_multi
    def create(self, vals_list):
        for vals in vals_list:
            if vals.get('name', _('Baru')) in (_('Baru'), _('New'), 'Baru', 'New'):
                vals['name'] = (
                    self.env['ir.sequence'].next_by_code('coconut.material.terbuang')
                    or _('Baru')
                )
        return super().create(vals_list)

    def write(self, vals):
        for rec in self:
            if rec.state == 'done' and any(k in vals for k in ('qty', 'product_id', 'location_id', 'transfer_id')):
                raise UserError(_("Transaksi Material Terbuang yang sudah selesai tidak dapat diedit."))
        return super().write(vals)

    def action_done(self):
        for rec in self:
            if rec.state != 'draft':
                raise UserError(_("Hanya dokumen Draft yang dapat diselesaikan."))
            if rec.qty <= 0:
                raise UserError(_("Kuantitas harus lebih besar dari 0."))

            # Find scrap location
            scrap_loc = self.env['stock.location'].search([('scrap_location', '=', True)], limit=1)
            if not scrap_loc:
                scrap_loc = self.env.ref('stock.stock_location_scrapped', raise_if_not_found=False)
            if not scrap_loc:
                raise UserError(_("Lokasi scrap virtual tidak ditemukan."))

            uom_kg = self.env.ref('uom.product_uom_kgm')
            
            # Create stock move
            move = self.env['stock.move'].create({
                'name': f'{rec.name} – Material Terbuang',
                'origin': rec.name,
                'product_id': rec.product_id.id,
                'product_uom_qty': rec.qty,
                'product_uom': uom_kg.id,
                'location_id': rec.location_id.id,
                'location_dest_id': scrap_loc.id,
                'company_id': rec.transfer_id.company_id.id or self.env.company.id,
            })
            move._action_confirm()
            move._action_assign()
            move.quantity = move.product_uom_qty
            move.picked = True
            move._action_done()

            rec.write({
                'stock_move_id': move.id,
                'state': 'done',
            })

    def action_cancel(self):
        for rec in self:
            if rec.state != 'done':
                raise UserError(_("Hanya dokumen selesai yang dapat dibatalkan."))
            if rec.stock_move_id:
                rec.stock_move_id._action_cancel()
                rec.stock_move_id.unlink()
            rec.state = 'cancelled'

    def action_reset_draft(self):
        for rec in self:
            if rec.state != 'cancelled':
                raise UserError(_("Hanya dokumen dibatalkan yang dapat dikembalikan ke draft."))
            rec.state = 'draft'
