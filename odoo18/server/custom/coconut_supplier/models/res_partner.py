from odoo import models, fields, api


class ResPartner(models.Model):
    """Extend res.partner to add coconut supplier fields"""
    _inherit = 'res.partner'

    coconut_supplier_id = fields.Many2one('coconut.supplier', string='Coconut Profile')
    is_coconut_supplier = fields.Boolean(string='Is Coconut Supplier', related='coconut_supplier_id.is_coconut_supplier', 
                                         store=True)
    coconut_supplier_type = fields.Selection(related='coconut_supplier_id.coconut_supplier_type', store=True)
    coconut_quality_grade = fields.Selection(related='coconut_supplier_id.quality_grade', store=True)
