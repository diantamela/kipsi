from odoo import models, fields, api, _
from odoo.exceptions import UserError, ValidationError

class CoconutSorting(models.Model):
    _name = 'coconut.sorting'
    _description = 'Sortir Kelapa'
    _order = 'id desc'

    name = fields.Char(string='Nomor Sortir', default='Baru', readonly=True, copy=False)
    receipt_id = fields.Many2one('coconut.receipt', string='Penerimaan Kelapa', required=True)
    date_sorting = fields.Date(string='Tanggal Sortir', default=fields.Date.context_today, required=True)
    
    supplier_id = fields.Many2one('res.partner', string='Pemasok', related='receipt_id.partner_id', store=True, readonly=True)
    coconut_origin = fields.Char(string='Asal Kelapa', related='receipt_id.origin', store=True, readonly=True)
    vehicle_plate = fields.Char(string='Nomor Polisi Kendaraan', related='receipt_id.vehicle_plate', store=True, readonly=True)
    
    broken_coconut_kg = fields.Float(string='Kelapa Pecah (Kg)', default=0.0)
    small_coconut_kg = fields.Float(string='Kelapa Kecil (Kg)', default=0.0)
    sprouted_coconut_kg = fields.Float(string='Kelapa Tunas (Kg)', default=0.0)
    rotten_coconut_kg = fields.Float(string='Kelapa Busuk (Kg)', default=0.0)
    young_coconut_kg = fields.Float(string='Kelapa Muda (Kg)', default=0.0)
    
    total_reject_kg = fields.Float(string='Total Sortiran Reject (Kg)', compute='_compute_totals', store=True)
    gross_weight_kg = fields.Float(string='Berat Kotor Penerimaan (Kg)', related='receipt_id.gross_weight', store=True, readonly=True)
    good_coconut_kg = fields.Float(string='Kelapa Layak Produksi (Kg)', compute='_compute_totals', store=True)
    
    notes = fields.Text(string='Keterangan')
    
    state = fields.Selection([
        ('draft', 'Draft'),
        ('confirmed', 'Dikonfirmasi'),
        ('done', 'Selesai'),
        ('cancelled', 'Dibatalkan')
    ], string='Status', default='draft')
    
    company_id = fields.Many2one('res.company', string='Perusahaan', default=lambda self: self.env.company, required=True)

    _sql_constraints = [
        ('receipt_id_uniq', 'unique(receipt_id)', 'Penerimaan Kelapa hanya dapat disortir satu kali!')
    ]

    @api.depends('broken_coconut_kg', 'small_coconut_kg', 'sprouted_coconut_kg', 'rotten_coconut_kg', 'young_coconut_kg', 'gross_weight_kg')
    def _compute_totals(self):
        for record in self:
            record.total_reject_kg = (record.broken_coconut_kg + record.small_coconut_kg + 
                                      record.sprouted_coconut_kg + record.rotten_coconut_kg + 
                                      record.young_coconut_kg)
            record.good_coconut_kg = record.gross_weight_kg - record.total_reject_kg

    @api.constrains('total_reject_kg', 'gross_weight_kg')
    def _check_total_reject(self):
        for record in self:
            if record.total_reject_kg > record.gross_weight_kg:
                raise ValidationError('Total Sortiran Reject (Kg) tidak boleh melebihi Berat Kotor Penerimaan (Kg).')

    @api.constrains('good_coconut_kg')
    def _check_good_coconut(self):
        for record in self:
            if record.good_coconut_kg < 0:
                raise ValidationError('Kelapa Layak Produksi (Kg) tidak boleh negatif.')

    @api.model_create_multi
    def create(self, vals_list):
        for vals in vals_list:
            if vals.get('name', 'Baru') == 'Baru':
                vals['name'] = self.env['ir.sequence'].next_by_code('coconut.sorting') or 'Baru'
        return super().create(vals_list)

    def action_confirm(self):
        for record in self:
            if not record.receipt_id:
                raise UserError('Penerimaan Kelapa harus dipilih sebelum konfirmasi.')
            if record.state != 'draft':
                raise UserError('Hanya dokumen draft yang dapat dikonfirmasi.')
            record.state = 'confirmed'

    def action_done(self):
        for record in self:
            if record.state != 'confirmed':
                raise UserError('Hanya dokumen yang dikonfirmasi yang dapat diselesaikan.')
            
            # Inventory Integration
            Product = self.env['product.product']
            
            # Use 'is_storable' instead of deprecated detailed_type
            good_product = Product.search([('name', '=', 'Kelapa Layak Produksi')], limit=1)
            if not good_product:
                good_product = Product.create({
                    'name': 'Kelapa Layak Produksi',
                    'is_storable': True,
                    'type': 'consu',
                })
                
            reject_product = Product.search([('name', '=', 'Kelapa Reject')], limit=1)
            if not reject_product:
                reject_product = Product.create({
                    'name': 'Kelapa Reject',
                    'is_storable': True,
                    'type': 'consu',
                })

            location_dest_id = self.env['stock.warehouse'].search([('company_id', '=', record.company_id.id)], limit=1).lot_stock_id
            if not location_dest_id:
                location_dest_id = self.env['stock.location'].search([('usage', '=', 'internal'), ('company_id', '=', record.company_id.id)], limit=1)
                
            location_src_id = self.env.ref('stock.location_inventory', raise_if_not_found=False)
            if not location_src_id:
                location_src_id = self.env['stock.location'].search([('usage', '=', 'inventory')], limit=1)

            moves = self.env['stock.move']
            uom_kg = self.env.ref('uom.product_uom_kgm', raise_if_not_found=False)
            
            if record.good_coconut_kg > 0:
                moves |= self.env['stock.move'].create({
                    'name': good_product.name,
                    'product_id': good_product.id,
                    'product_uom_qty': record.good_coconut_kg,
                    'product_uom': uom_kg.id if uom_kg else good_product.uom_id.id,
                    'location_id': location_src_id.id,
                    'location_dest_id': location_dest_id.id,
                    'company_id': record.company_id.id,
                })
            
            if record.total_reject_kg > 0:
                moves |= self.env['stock.move'].create({
                    'name': reject_product.name,
                    'product_id': reject_product.id,
                    'product_uom_qty': record.total_reject_kg,
                    'product_uom': uom_kg.id if uom_kg else reject_product.uom_id.id,
                    'location_id': location_src_id.id,
                    'location_dest_id': location_dest_id.id,
                    'company_id': record.company_id.id,
                })
            
            if moves:
                moves._action_confirm()
                moves._action_assign()
                for move in moves:
                    move.quantity = move.product_uom_qty
                    move.picked = True
                moves._action_done()
                
            record.state = 'done'

    def action_cancel(self):
        for record in self:
            if record.state == 'done':
                raise UserError('Tidak dapat membatalkan sortir yang sudah selesai.')
            record.state = 'cancelled'

    def action_reset_draft(self):
        for record in self:
            if record.state != 'cancelled':
                raise UserError('Hanya dokumen yang dibatalkan yang dapat dikembalikan ke draft.')
            record.state = 'draft'
