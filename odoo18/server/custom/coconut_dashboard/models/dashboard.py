from odoo import models, fields, api, _
from odoo.addons.web.controllers.main import clean_action


class CoconutDashboard(models.Model):
    """Coconut Factory Dashboard"""
    _name = 'coconut.dashboard'
    _description = 'Coconut Factory Dashboard'
    _auto = False

    @api.model
    def get_dashboard_data(self):
        """Return aggregated dashboard metrics"""
        return {
            'inventory': self._get_inventory_metrics(),
            'production': self._get_production_metrics(),
            'purchases': self._get_purchase_metrics(),
            'suppliers': self._get_supplier_metrics(),
            'quality': self._get_quality_metrics(),
        }
    
    def _get_inventory_metrics(self):
        """Get inventory-related KPI"""
        StockQuant = self.env['stock.quant']
        CoconutBatch = self.env['coconut.batch']
        
        coconut_products = self.env['product.product'].search([
            ('coconut_product_ids', '!=', False)
        ])
        
        total_stock = sum(StockQuant.search([
            ('product_id', 'in', coconut_products.ids)
        ]).mapped('quantity'))
        
        low_stock_products = coconut_products.filtered(
            lambda p: p.virtual_available < p.coconut_minimum_stock
        )
        
        active_batches = CoconutBatch.search_count([
            ('inspection_completed', '=', True),
            ('current_stock', '>', 0)
        ])
        
        return {
            'total_stock_kg': total_stock,
            'low_stock_count': len(low_stock_products),
            'active_batches': active_batches,
        }
    
    def _get_production_metrics(self):
        """Get production-related KPI"""
        Production = self.env['coconut.production.order']
        WorkOrder = self.env['coconut.work.order']
        
        today = fields.Date.today()
        last_7_days = today - fields.timedelta(days=7)
        
        this_week_production = Production.search([
            ('state', '=', 'done'),
            ('create_date', '>=', last_7_days)
        ])
        
        total_produced = sum(this_week_production.mapped('actual_qty'))
        total_rejected = sum(this_week_production.mapped('rejected_qty'))
        
        avg_efficiency = 0.0
        if this_week_production:
            avg_efficiency = sum(this_week_production.mapped('efficiency')) / len(this_week_production)
        
        avg_yield = 0.0
        if this_week_production:
            avg_yield = sum(this_week_production.mapped('yield_rate')) / len(this_week_production)
        
        active_work_orders = WorkOrder.search_count([('state', '=', 'progress')])
        
        return {
            'weekly_production_kg': total_produced,
            'weekly_rejected_kg': total_rejected,
            'avg_efficiency': avg_efficiency,
            'avg_yield_rate': avg_yield,
            'active_work_orders': active_work_orders,
        }
    
    def _get_purchase_metrics(self):
        """Get purchase-related KPI"""
        Purchase = self.env['purchase.order']
        Requisition = self.env['coconut.purchase.requisition']
        
        pending_requisitions = Requisition.search_count([('state', '=', 'submitted')])
        pending_po_approval = Purchase.search_count([
            ('state', 'in', ['sent', 'draft']),
            ('partner_id.is_coconut_supplier', '=', True)
        ])
        
        this_month = fields.Date.today().replace(day=1)
        monthly_purchases = Purchase.search([
            ('date_order', '>=', this_month),
            ('partner_id.is_coconut_supplier', '=', True),
            ('state', '=', 'purchase')
        ])
        total_purchased = sum(monthly_purchases.mapped('amount_untaxed'))
        
        return {
            'pending_approvals': pending_requisitions,
            'pending_po': pending_po_approval,
            'monthly_purchases': total_purchased,
        }
    
    def _get_supplier_metrics(self):
        """Get supplier-related KPI"""
        Supplier = self.env['coconut.supplier']
        
        total_suppliers = Supplier.search_count([])
        active_suppliers = Supplier.search_count([('total_deliveries', '>', 0)])
        premium_suppliers = Supplier.search_count([('quality_grade', '=', 'premium')])
        
        avg_quality_score = 0.0
        suppliers = Supplier.search([])
        if suppliers:
            avg_quality_score = sum(suppliers.mapped('avg_quality_score')) / len(suppliers)
        
        return {
            'total_suppliers': total_suppliers,
            'active_suppliers': active_suppliers,
            'premium_suppliers': premium_suppliers,
            'avg_supplier_quality': avg_quality_score,
        }
    
    def _get_quality_metrics(self):
        """Get quality-related KPI"""
        Inspection = self.env['coconut.inspection']
        Batch = self.env['coconut.batch']
        
        this_month = fields.Date.today().replace(day=1)
        this_month_inspections = Inspection.search([
            ('inspection_date', '>=', this_month)
        ])
        
        total_inspected = len(this_month_inspections)
        approved = len(this_month_inspections.filtered(lambda i: i.approved))
        rejected = len(this_month_inspections.filtered(lambda i: not i.approved))
        
        approval_rate = (approved / total_inspected * 100) if total_inspected > 0 else 0
        
        avg_quality_score = 0.0
        if this_month_inspections:
            avg_quality_score = sum(this_month_inspections.mapped('overall_quality')) / len(this_month_inspections)
        
        return {
            'inspected_this_month': total_inspected,
            'approval_rate': approval_rate,
            'avg_quality_score': avg_quality_score,
        }
