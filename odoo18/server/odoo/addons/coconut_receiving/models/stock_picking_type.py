# -*- coding: utf-8 -*-
from odoo import models, fields, api, _


class PickingType(models.Model):
    _inherit = 'stock.picking.type'

    def _get_action(self, action_xmlid):
        if self.code == 'incoming':
            # Redirect incoming (Receipts) card clicks to Penerimaan Kelapa (coconut.receipt)
            action = self.env["ir.actions.actions"]._for_xml_id('coconut_receiving.action_coconut_receipt')
            # Set the context to maintain default values
            context = dict(self.env.context)
            context.update({
                'default_company_id': self.company_id.id,
            })
            action['context'] = context
            return action
        return super(PickingType, self)._get_action(action_xmlid)

    def get_stock_picking_action_picking_type(self):
        if self.code == 'incoming':
            return self._get_action('coconut_receiving.action_coconut_receipt')
        return super(PickingType, self).get_stock_picking_action_picking_type()

    def get_action_picking_tree_ready(self):
        if self.code == 'incoming':
            return self._get_action('coconut_receiving.action_coconut_receipt')
        return super(PickingType, self).get_action_picking_tree_ready()

    def get_action_picking_tree_waiting(self):
        if self.code == 'incoming':
            return self._get_action('coconut_receiving.action_coconut_receipt')
        return super(PickingType, self).get_action_picking_tree_waiting()

    def get_action_picking_tree_late(self):
        if self.code == 'incoming':
            return self._get_action('coconut_receiving.action_coconut_receipt')
        return super(PickingType, self).get_action_picking_tree_late()

    def get_action_picking_tree_backorder(self):
        if self.code == 'incoming':
            return self._get_action('coconut_receiving.action_coconut_receipt')
        return super(PickingType, self).get_action_picking_tree_backorder()

    def get_action_picking_type_ready_moves(self):
        if self.code == 'incoming':
            return self._get_action('coconut_receiving.action_coconut_receipt')
        return super(PickingType, self).get_action_picking_type_ready_moves()

    def _get_aggregated_records_by_date(self):
        """
        Adjust the bar chart on the incoming picking type card
        to reflect pending/draft Penerimaan Kelapa (coconut.receipt) records.
        """
        incoming_picking_types = self.filtered(lambda p: p.code == 'incoming')
        other_picking_types = self - incoming_picking_types
        res = []
        if other_picking_types:
            res.extend(super(PickingType, other_picking_types)._get_aggregated_records_by_date())
        
        if incoming_picking_types:
            # Retrieve dates of draft coconut receipts
            receipts = self.env['coconut.receipt'].search([
                ('state', '=', 'draft')
            ])
            picking_type_id_to_dates = {pt.id: [] for pt in incoming_picking_types}
            for rec in receipts:
                for pt in incoming_picking_types:
                    if pt.company_id == rec.company_id:
                        picking_type_id_to_dates[pt.id].append(rec.entry_datetime)
            for pt in incoming_picking_types:
                res.append((pt.id, picking_type_id_to_dates[pt.id], _('Penerimaan')))
        return res

    def _compute_picking_count(self):
        super(PickingType, self)._compute_picking_count()
        for record in self:
            if record.code == 'incoming':
                draft_count = self.env['coconut.receipt'].search_count([
                    ('state', '=', 'draft'),
                    ('company_id', '=', record.company_id.id)
                ])
                record.count_picking_ready = draft_count
                record.count_picking_draft = draft_count
                record.count_picking = draft_count
                record.count_picking_waiting = 0
                record.count_picking_late = 0
                record.count_picking_backorders = 0

    def _compute_move_count(self):
        super(PickingType, self)._compute_move_count()
        for record in self:
            if record.code == 'incoming':
                record.count_move_ready = 0


class StockPicking(models.Model):
    _inherit = 'stock.picking'

    @api.model
    def get_action_click_graph(self):
        picking_type_id = self.env.context.get('picking_type_id')
        if picking_type_id:
            picking_type = self.env['stock.picking.type'].browse(picking_type_id)
            if picking_type.code == 'incoming':
                action = self.env["ir.actions.actions"]._for_xml_id('coconut_receiving.action_coconut_receipt')
                context = dict(self.env.context)
                context.update({
                    'default_company_id': picking_type.company_id.id,
                })
                action['context'] = context
                return action
        return super(StockPicking, self).get_action_click_graph()
