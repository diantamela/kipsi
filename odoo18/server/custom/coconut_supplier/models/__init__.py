from odoo import models, fields, api, _
from odoo.exceptions import ValidationError


class CoconutSupplier(models.Model):
    """Enhanced supplier management for coconut suppliers"""
    _name = 'coconut.supplier'
    _description = 'Coconut Supplier Profile'
    _inherit = 'res.partner'
    _rec_name = 'name'

    # Coconut-specific supplier classification
    is_coconut_supplier = fields.Boolean(string='Is Coconut Supplier', default=False)
    coconut_supplier_type = fields.Selection([
        ('farmer', 'Individual Farmer'),
        ('cooperative', 'Farmer Cooperative'),
        ('trader', 'Local Trader'),
        ('exporter', 'Exporter'),
        ('processor', 'Raw Material Processor'),
    ], string='Supplier Type', default='farmer')
    
    # Geographic information
    village = fields.Char(string='Village')
    district = fields.Char(string='District')
    province = fields.Char(string='Province/State')
    country_coconut_origin = fields.Char(string='Country of Origin')
    distance_to_factory = fields.Float(string='Distance to Factory (km)')
    
    # Farming information
    farm_size_hectares = fields.Float(string='Farm Size (Hectares)')
    coconut_variety = fields.Selection([
        ('tall', 'Tall Variety'),
        ('dwarf', 'Dwarf Variety'),
        ('hybrid', 'Hybrid Variety'),
        ('mixed', 'Mixed Varieties'),
    ], string='Coconut Variety')
    annual_capacity = fields.Float(string='Annual Supply Capacity (tons)')
    harvest_season = fields.Selection([
        ('year_round', 'Year-round'),
        ('seasonal_q1', 'Seasonal Q1'),
        ('seasonal_q2', 'Seasonal Q2'),
        ('seasonal_q3', 'Seasonal Q3'),
        ('seasonal_q4', 'Seasonal Q4'),
    ], string='Harvest Season')
    
    # Quality & certification
    organic_certified = fields.Boolean(string='Organic Certified', default=False)
    fair_trade_certified = fields.Boolean(string='Fair Trade Certified', default=False)
    quality_grade = fields.Selection([
        ('premium', 'Premium Supplier'),
        ('standard', 'Standard Supplier'),
        ('basic', 'Basic Supplier'),
        ('trial', 'Trial/New Supplier'),
    ], string='Supplier Grade', default='trial')
    
    # Performance tracking
    total_deliveries = fields.Integer(string='Total Deliveries', readonly=True, default=0)
    total_quantity = fields.Float(string='Total Quantity Delivered (kg)', readonly=True, default=0.0)
    avg_quality_score = fields.Float(string='Average Quality Score', digits=(5,2), readonly=True)
    on_time_delivery_rate = fields.Float(string='On-Time Delivery Rate (%)', digits=(5,2))
    rejection_rate = fields.Float(string='Rejection Rate (%)', digits=(5,2), readonly=True)
    
    # Last transaction
    last_delivery_date = fields.Date(string='Last Delivery Date', readonly=True)
    last_quality_score = fields.Float(string='Last Quality Score', digits=(5,2))
    
    # Financial terms
    payment_terms = fields.Selection([
        ('cash', 'Cash on Delivery'),
        ('7_days', '7 Days'),
        ('15_days', '15 Days'),
        ('30_days', '30 Days'),
        ('45_days', '45 Days'),
        ('60_days', '60 Days'),
    ], string='Payment Terms', default='15_days')
    
    currency_id = fields.Many2one('res.currency', string='Currency',
                                 default=lambda self: self.env.company.currency_id)
    unit_price = fields.Monetary(string='Standard Unit Price',
                                help='Current agreed price per kg')
    
    # Notes
    special_requirements = fields.Text(string='Special Requirements')
    certifications = fields.Text(string='Certifications Held')
    notes = fields.Text(string='Internal Notes')


class SupplierPerformance(models.Model):
    """Track supplier performance metrics"""
    _name = 'coconut.supplier.performance'
    _description = 'Supplier Performance Record'
    _order = 'date desc'

    supplier_id = fields.Many2one('coconut.supplier', string='Supplier', required=True)
    date = fields.Date(string='Evaluation Date', required=True, 
                      default=fields.Date.today)
    
    # Purchase reference
    purchase_order_id = fields.Many2one('purchase.order', string='Related PO')
    delivery_id = fields.Many2one('stock.picking', string='Related Delivery')
    
    # KPI metrics
    delivery_score = fields.Integer(string='Delivery Timeliness (1-10)',
                                   help='On-time delivery performance')
    quality_score = fields.Integer(string='Quality Score (1-10)',
                                  help='Quality of delivered coconuts')
    quantity_score = fields.Integer(string='Quantity Accuracy (1-10)',
                                   help='Accuracy of delivered quantity')
    price_score = fields.Integer(string='Price Competitiveness (1-10)',
                                help='Price relative to market')
    service_score = fields.Integer(string='Service & Communication (1-10)')
    
    # Overall
    overall_score = fields.Float(string='Overall Score', digits=(5,2), 
                                compute='_compute_overall_score', store=True)
    grade = fields.Selection([
        ('a', 'A - Excellent'),
        ('b', 'B - Good'),
        ('c', 'C - Average'),
        ('d', 'D - Below Average'),
        ('f', 'F - Poor'),
    ], string='Grade', compute='_compute_grade', store=True)
    
    # Inspector
    evaluated_by = fields.Many2one('res.users', string='Evaluated By',
                                  default=lambda self: self.env.user)
    notes = fields.Text(string='Evaluation Notes')
    
    @api.depends('delivery_score', 'quality_score', 'quantity_score', 'price_score', 'service_score')
    def _compute_overall_score(self):
        for record in self:
            scores = [record.delivery_score, record.quality_score, 
                     record.quantity_score, record.price_score, record.service_score]
            record.overall_score = sum(scores) / len(scores) if scores else 0.0
    
    @api.depends('overall_score')
    def _compute_grade(self):
        for record in self:
            if record.overall_score >= 9:
                record.grade = 'a'
            elif record.overall_score >= 8:
                record.grade = 'b'
            elif record.overall_score >= 6:
                record.grade = 'c'
            elif record.overall_score >= 4:
                record.grade = 'd'
            else:
                record.grade = 'f'


class SupplierCoconutHistory(models.Model):
    """Detailed transaction history for coconut suppliers"""
    _name = 'coconut.supplier.history'
    _description = 'Supplier Transaction History'
    _order = 'transaction_date desc'

    supplier_id = fields.Many2one('coconut.supplier', string='Supplier', required=True)
    transaction_date = fields.Datetime(string='Date', required=True, 
                                      default=fields.Datetime.now)
    
    transaction_type = fields.Selection([
        ('purchase', 'Purchase Order'),
        ('delivery', 'Goods Receipt'),
        ('invoice', 'Invoice'),
        ('payment', 'Payment'),
        ('return', 'Return'),
        ('quality_issue', 'Quality Issue'),
        ('complaint', 'Complaint'),
        ('bonus', 'Bonus/Discount'),
    ], string='Type', required=True)
    
    reference = fields.Char(string='Reference Number')
    amount = fields.Monetary(string='Amount')
    quantity = fields.Float(string='Quantity (kg)')
    quality_grade = fields.Selection([
        ('excellent', 'Excellent'),
        ('good', 'Good'),
        ('acceptable', 'Acceptable'),
        ('poor', 'Poor'),
    ], string='Quality Grade')
    notes = fields.Text(string='Notes')
    
    currency_id = fields.Many2one('res.currency', string='Currency',
                                 default=lambda self: self.env.company.currency_id)
