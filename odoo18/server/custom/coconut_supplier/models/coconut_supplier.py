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
