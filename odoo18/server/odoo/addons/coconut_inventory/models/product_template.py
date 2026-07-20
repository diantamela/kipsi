from odoo import api, fields, models

class ProductTemplate(models.Model):
    _inherit = 'product.template'

    inventory_card_type = fields.Char(compute='_compute_inventory_card_type', store=False)
    inventory_status_label = fields.Char(compute='_compute_inventory_status', store=False)
    wip_production_stage = fields.Char(compute='_compute_wip_data', store=False)
    wip_work_center = fields.Char(compute='_compute_wip_data', store=False)
    wip_process_status = fields.Char(compute='_compute_wip_data', store=False)
    wip_last_processed = fields.Datetime(compute='_compute_wip_data', store=False)
    
    fg_location_name = fields.Char(compute='_compute_fg_data', store=False)
    fg_last_in = fields.Datetime(compute='_compute_fg_data', store=False)
    
    reject_qty = fields.Float(compute='_compute_reject_data', store=False)
    reject_location_name = fields.Char(compute='_compute_reject_data', store=False)
    reject_handling_status = fields.Char(default='Pending', string="Status Penanganan")
    reject_last_recorded = fields.Datetime(compute='_compute_reject_data', store=False)

    byproduct_location_name = fields.Char(compute='_compute_byproduct_data', store=False)

    @api.depends('categ_id.name')
    def _compute_inventory_card_type(self):
        for record in self:
            cat_name = (record.categ_id.name or '').lower()
            if 'bahan baku' in cat_name:
                record.inventory_card_type = 'bahan_baku'
            elif 'wip' in cat_name or 'setengah jadi' in cat_name or 'barang setengah jadi' in cat_name:
                record.inventory_card_type = 'wip'
            elif 'produk jadi' in cat_name or 'finished good' in cat_name:
                record.inventory_card_type = 'fg'
            elif 'reject' in cat_name:
                record.inventory_card_type = 'reject'
            elif 'samping' in cat_name or 'byproduct' in cat_name:
                record.inventory_card_type = 'byproduct'
            else:
                record.inventory_card_type = 'other'

    @api.depends('qty_available')
    def _compute_inventory_status(self):
        for record in self:
            if record.qty_available <= 0:
                record.inventory_status_label = 'Habis'
            elif record.qty_available < 20:
                record.inventory_status_label = 'Menipis'
            else:
                record.inventory_status_label = 'Normal'

    def _compute_wip_data(self):
        for record in self:
            if record.inventory_card_type == 'wip':
                # find active workorder
                wo = self.env['mrp.workorder'].search([
                    ('product_id.product_tmpl_id', '=', record.id), 
                    ('state', 'not in', ('done', 'cancel'))
                ], limit=1, order='date_start desc')
                if wo:
                    record.wip_production_stage = wo.name
                    record.wip_work_center = wo.workcenter_id.name
                    record.wip_process_status = dict(wo._fields['state'].selection).get(wo.state, wo.state) if wo.state else '-'
                    record.wip_last_processed = wo.write_date
                else:
                    record.wip_production_stage = 'Tidak ada proses aktif'
                    record.wip_work_center = '-'
                    record.wip_process_status = '-'
                    record.wip_last_processed = False
            else:
                record.wip_production_stage = ''
                record.wip_work_center = ''
                record.wip_process_status = ''
                record.wip_last_processed = False

    def _compute_fg_data(self):
        for record in self:
            if record.inventory_card_type == 'fg':
                quant = self.env['stock.quant'].search([
                    ('product_id.product_tmpl_id', '=', record.id), 
                    ('location_id.usage', '=', 'internal'), 
                    ('quantity', '>', 0)
                ], limit=1)
                record.fg_location_name = quant.location_id.display_name if quant else 'Gudang Utama'
                
                move = self.env['stock.move'].search([
                    ('product_id.product_tmpl_id', '=', record.id), 
                    ('state', '=', 'done'), 
                    ('location_dest_id.usage', '=', 'internal')
                ], limit=1, order='date desc')
                record.fg_last_in = move.date if move else False
            else:
                record.fg_location_name = ''
                record.fg_last_in = False

    def _compute_reject_data(self):
        for record in self:
            if record.inventory_card_type == 'reject':
                quants = self.env['stock.quant'].search([
                    ('product_id.product_tmpl_id', '=', record.id), 
                    ('location_id.scrap_location', '=', True)
                ])
                record.reject_qty = sum(quants.mapped('quantity'))
                record.reject_location_name = quants[0].location_id.display_name if quants else 'Lokasi Reject'
                
                move = self.env['stock.move'].search([
                    ('product_id.product_tmpl_id', '=', record.id), 
                    ('state', '=', 'done'), 
                    ('scrapped', '=', True)
                ], limit=1, order='date desc')
                record.reject_last_recorded = move.date if move else False
            else:
                record.reject_qty = 0.0
                record.reject_location_name = ''
                record.reject_last_recorded = False

    def _compute_byproduct_data(self):
        for record in self:
            if record.inventory_card_type == 'byproduct':
                quant = self.env['stock.quant'].search([
                    ('product_id.product_tmpl_id', '=', record.id), 
                    ('location_id.usage', '=', 'internal'), 
                    ('quantity', '>', 0)
                ], limit=1)
                record.byproduct_location_name = quant.location_id.display_name if quant else 'Gudang Sampingan'
            else:
                record.byproduct_location_name = ''
