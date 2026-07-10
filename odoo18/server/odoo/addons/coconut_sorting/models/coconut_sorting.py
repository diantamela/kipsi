from odoo import models, fields, api, _
from odoo.exceptions import UserError, ValidationError
import logging
from odoo.tools.float_utils import float_compare, float_is_zero

_logger = logging.getLogger(__name__)

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
    
    raw_move_id = fields.Many2one('stock.move', string='Pergerakan Kelapa Bulat', readonly=True, copy=False)
    good_move_id = fields.Many2one('stock.move', string='Pergerakan Kelapa Layak Produksi', readonly=True, copy=False)
    reject_move_id = fields.Many2one('stock.move', string='Pergerakan Kelapa Reject', readonly=True, copy=False)
    
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
            
            if record.raw_move_id or record.good_move_id or record.reject_move_id:
                raise UserError('Transaksi sortir ini sudah selesai dan pergerakan stok telah dibuat.')

            uom_kg = self.env.ref('uom.product_uom_kgm')
            
            if float_is_zero(record.gross_weight_kg, precision_rounding=uom_kg.rounding):
                raise UserError('Berat yang diproses harus lebih besar dari nol.')

            if record.total_reject_kg < 0:
                raise UserError('Total reject tidak boleh negatif.')
                
            if record.good_coconut_kg < 0:
                raise UserError('Kelapa Layak Produksi tidak boleh negatif.')
                
            if float_compare(record.total_reject_kg, record.gross_weight_kg, precision_rounding=uom_kg.rounding) > 0:
                raise UserError('Total reject tidak boleh melebihi berat diproses.')
                
            if float_compare(record.gross_weight_kg, record.good_coconut_kg + record.total_reject_kg, precision_rounding=uom_kg.rounding) != 0:
                raise UserError('Keseimbangan inventaris tidak valid: Berat diproses harus sama dengan Kelapa Layak Produksi + Total Reject.')

            good_product = self.env.ref('coconut_sorting.product_kelapa_layak', raise_if_not_found=False)
            if not good_product:
                raise UserError('Data produk Kelapa Layak Produksi tidak ditemukan. Harap perbarui modul.')
                
            reject_product = self.env.ref('coconut_sorting.product_kelapa_reject', raise_if_not_found=False)
            if not reject_product:
                raise UserError('Data produk Kelapa Reject tidak ditemukan. Harap perbarui modul.')

            raw_template = self.env.ref('coconut_receiving.product_coconut_with_shell', raise_if_not_found=False)
            if not raw_template:
                raise UserError('Data produk Kelapa Bulat tidak ditemukan di modul penerimaan.')
            raw_product = raw_template.product_variant_id

            for prod, name in [(raw_product, 'Kelapa Bulat'), (good_product, 'Kelapa Layak Produksi'), (reject_product, 'Kelapa Reject')]:
                if prod.uom_id != uom_kg or prod.uom_id.category_id != uom_kg.category_id:
                    raise UserError(f'Produk {name} harus menggunakan satuan ukuran kg dalam kategori Berat. Silakan perbaiki konfigurasi produk terlebih dahulu.')

            location_src_id = self.env['stock.warehouse'].search([('company_id', '=', record.company_id.id)], limit=1).lot_stock_id
            if not location_src_id:
                location_src_id = self.env['stock.location'].search([('usage', '=', 'internal'), ('company_id', '=', record.company_id.id)], limit=1)
                if not location_src_id:
                    raise UserError('Lokasi stok internal (Warehouse) tidak ditemukan.')
                
            location_dest_id = self.env.ref('coconut_sorting.stock_location_coconut_sorting', raise_if_not_found=False)
            if not location_dest_id:
                location_dest_id = self.env['stock.location'].search([('usage', '=', 'production')], limit=1)
                if not location_dest_id:
                    raise UserError('Lokasi produksi untuk sortir kelapa tidak ditemukan.')

            available_qty = self.env['stock.quant']._get_available_quantity(raw_product, location_src_id)
            if float_compare(available_qty, record.gross_weight_kg, precision_rounding=uom_kg.rounding) < 0:
                raise UserError(f'Stok Kelapa Bulat tidak mencukupi.\n\nStok tersedia: {available_qty:,.2f} kg\nBerat yang akan disortir: {record.gross_weight_kg:,.2f} kg')

            move_vals_list = []
            
            # Stock Move 1: Consume Raw Coconut (Warehouse -> Production)
            move_vals_list.append({
                'name': record.name or 'Sortir Kelapa',
                'origin': record.name,
                'product_id': raw_product.id,
                'product_uom_qty': record.gross_weight_kg,
                'product_uom': raw_product.uom_id.id,
                'location_id': location_src_id.id,
                'location_dest_id': location_dest_id.id,
                'company_id': record.company_id.id,
            })
            
            # Stock Move 2: Produce Good Coconut (Production -> Warehouse)
            move_vals_list.append({
                'name': record.name or 'Sortir Kelapa',
                'origin': record.name,
                'product_id': good_product.id,
                'product_uom_qty': record.good_coconut_kg,
                'product_uom': good_product.uom_id.id,
                'location_id': location_dest_id.id,
                'location_dest_id': location_src_id.id,
                'company_id': record.company_id.id,
            })
            
            # Stock Move 3: Produce Reject Coconut (Production -> Warehouse)
            move_vals_list.append({
                'name': record.name or 'Sortir Kelapa',
                'origin': record.name,
                'product_id': reject_product.id,
                'product_uom_qty': record.total_reject_kg,
                'product_uom': reject_product.uom_id.id,
                'location_id': location_dest_id.id,
                'location_dest_id': location_src_id.id,
                'company_id': record.company_id.id,
            })

            moves = self.env['stock.move'].create(move_vals_list)
            moves._action_confirm()
            moves._action_assign()
            for move in moves:
                move.quantity = move.product_uom_qty
                move.picked = True
            moves._action_done()
            
            record.raw_move_id = moves[0].id
            record.good_move_id = moves[1].id
            record.reject_move_id = moves[2].id

            record.state = 'done'

    def action_cancel(self):
        for record in self:
            if record.state == 'done' or record.raw_move_id or record.good_move_id or record.reject_move_id:
                raise UserError('Transaksi sortir yang sudah menghasilkan pergerakan stok tidak dapat dikembalikan ke Draft. Lakukan proses pembalikan stok terlebih dahulu.')
            record.state = 'cancelled'

    def action_reset_draft(self):
        for record in self:
            if record.state != 'cancelled':
                raise UserError('Hanya dokumen yang dibatalkan yang dapat dikembalikan ke draft.')
            record.state = 'draft'
