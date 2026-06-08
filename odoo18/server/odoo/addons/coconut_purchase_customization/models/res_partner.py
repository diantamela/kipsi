# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import api, fields, models, _


class ResPartner(models.Model):
    _inherit = 'res.partner'

    is_coconut_supplier = fields.Boolean(
        string='Coconut Supplier',
        help='Check if this partner is a coconut supplier for PT Coco Murni Prima Jaya.'
    )
    contact_person = fields.Char(
        string='Contact Person',
        help='Nama kontak pemasok kelapa.'
    )
    supplier_phone = fields.Char(
        string='Supplier Phone',
        help='Nomor HP pemasok kelapa.'
    )
    supplier_address = fields.Text(
        string='Supplier Address',
        help='Alamat lengkap pemasok kelapa.'
    )
    receipt_count = fields.Integer(
        string='Receipt Count',
        compute='_compute_receipt_count',
        groups='purchase.group_purchase_user',
    )

    @api.depends_context('uid')
    def _compute_receipt_count(self):
        """Compute the number of coconut receipts for this supplier."""
        for partner in self:
            if partner.is_coconut_supplier:
                partner.receipt_count = self.env['coconut.supplier.receipt'].search_count(
                    [('supplier_id', '=', partner.id)]
                )
            else:
                partner.receipt_count = 0