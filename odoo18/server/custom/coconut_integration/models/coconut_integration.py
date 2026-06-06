from odoo import models, fields, api, _
from odoo.exceptions import ValidationError


class CoconutFactoryConfig(models.Model):
    """Factory-wide configuration"""
    _name = 'coconut.factory.config'
    _description = 'Coconut Factory Configuration'
    _rec_name = 'name'

    name = fields.Char(string='Configuration Name', required=True, 
                      default=lambda self: self.env.company.name + ' Config')
    company_id = fields.Many2one('res.company', string='Company', 
                                default=lambda self: self.env.company, required=True)
    
    # Production settings
    default_workcenter_id = fields.Many2one('mrp.workcenter', string='Default Work Center')
    production_lead_time_days = fields.Integer(string='Production Lead Time (days)', default=5)
    
    # Inventory settings
    coconut_receipt_location = fields.Many2one('stock.location', string='Coconut Receiving Location',
                                              domain="[('location_type_coconut', '=', 'receiving')]")
    coconut_storage_location = fields.Many2one('stock.location', string='Coconut Storage Location',
                                              domain="[('location_type_coconut', '=', 'dry_storage')]")
    coconut_buffer_location = fields.Many2one('stock.location', string='Production Buffer',
                                             domain="[('location_type_coconut', '=', 'production_buffer')]")
    finished_goods_location = fields.Many2one('stock.location', string='Finished Goods Location',
                                             domain="[('location_type_coconut', '=', 'finished_goods')]")
    
    # Purchase settings
    default_purchase_approval_required = fields.Boolean(string='Purchase Approval Required', default=True)
    auto_generate_po_from_requisition = fields.Boolean(string='Auto-Generate PO from Requisition', default=True)
    
    # Notification settings
    notification_settings_id = fields.Many2one('coconut.notification.settings', 
                                              string='Notification Settings')
    
    # Integration flags
    enable_hr_integration = fields.Boolean(string='Enable HR Integration', default=True,
                                           help='Link production work orders to employee timesheets')
    enable_payroll_integration = fields.Boolean(string='Enable Payroll Integration', default=False,
                                                help='Calculate payroll based on production labor')
    
    # Quality settings
    auto_inspection_required = fields.Boolean(string='Auto-Create Inspection on Receipt', default=True)
    inspection_approval_required = fields.Boolean(string='Inspection Approval Required', default=True)
    
    @api.model_create_multi
    def create(self, vals_list):
        result = super().create(vals_list)
        # Configure stock locations in system parameters
        for config in result:
            if config.coconut_receipt_location:
                self.env['ir.config_parameter'].sudo().set_param(
                    'coconut_receipt_location_id', 
                    str(config.coconut_receipt_location.id)
                )
            if config.coconut_storage_location:
                self.env['ir.config_parameter'].sudo().set_param(
                    'coconut_storage_location_id',
                    str(config.coconut_storage_location.id)
                )
        return result


class CoconutProductionIntegration(models.Model):
    """Integration logic for production tracking"""
    _name = 'coconut.production.integration'
    _description = 'Coconut Production Integration Logic'

    @api.model
    def create_production_order(self, requisition_id):
        """Create production order from purchase requisition"""
        requisition = self.env['coconut.purchase.requisition'].browse(requisition_id)
        if not requisition.exists():
            raise ValidationError(_('Requisition not found'))
        
        # Create manufacturing order
        mo_vals = {
            'product_id': requisition.product_id.id,
            'product_uom_id': requisition.product_id.uom_id.id,
            'product_qty': requisition.quantity,
            'date_planned_start': requisition.required_date,
            'bom_id': self._find_bom(requisition.product_id),
            'origin': requisition.name,
        }
        
        production = self.env['mrp.production'].create(mo_vals)
        return production
    
    @api.model
    def _find_bom(self, product):
        """Find suitable BoM for product"""
        bom = self.env['mrp.bom'].search([
            ('product_tmpl_id', '=', product.product_tmpl_id.id),
            ('company_id', '=', self.env.company.id),
        ], limit=1)
        return bom.id if bom else False
    
    @api.model
    def sync_inventory_cache(self):
        """Update cached inventory values"""
        products = self.env['product.product'].search([
            ('coconut_product_ids', '!=', False)
        ])
        
        for product in products:
            total_qty = sum(self.env['stock.quant'].search([
                ('product_id', '=', product.id),
                ('location_id.usage', '=', 'internal')
            ]).mapped('quantity'))
            
            # Update custom cache if exists
            cache = self.env['coconut.stock.alert'].search([
                ('product_id', '=', product.id)
            ], limit=1)
            if cache:
                cache._compute_current_stock()
    
    @api.model
    def generate_daily_summary(self):
        """Generate daily production and inventory summary"""
        today = fields.Date.today()
        
        summary = {
            'date': today,
            'total_produced': self._get_today_production(),
            'total_consumed': self._get_today_consumption(),
            'stock_levels': self._get_current_stock_levels(),
            'pending_requisitions': self._get_pending_requisitions_count(),
            'quality_issues': self._get_quality_issues_count(),
        }
        
        return summary
    
    @api.model
    def _get_today_production(self):
        """Get today's production quantity"""
        productions = self.env['coconut.production.order'].search([
            ('state', '=', 'done'),
            ('actual_end_date', '>=', fields.Datetime.now().replace(hour=0, minute=0, second=0)),
        ])
        return sum(productions.mapped('actual_qty'))
    
    @api.model
    def _get_today_consumption(self):
        """Get today's raw material consumption"""
        moves = self.env['stock.move'].search([
            ('product_id.coconut_product_ids', '!=', False),
            ('state', '=', 'done'),
            ('date', '>=', fields.Datetime.now().replace(hour=0, minute=0, second=0)),
            ('location_dest_id.usage', '=', 'production'),
        ])
        return sum(moves.mapped('product_uom_qty'))
    
    @api.model
    def _get_current_stock_levels(self):
        """Get current stock levels by product"""
        products = self.env['product.product'].search([
            ('coconut_product_ids', '!=', False)
        ])
        return {p.name: sum(self.env['stock.quant'].search([
            ('product_id', '=', p.id),
            ('location_id.usage', '=', 'internal')
        ]).mapped('quantity')) for p in products}
    
    @api.model
    def _get_pending_requisitions_count(self):
        return self.env['coconut.purchase.requisition'].search_count([
            ('state', 'in', ['submitted', 'approved'])
        ])
    
    @api.model
    def _get_quality_issues_count(self):
        return self.env['coconut.inspection'].search_count([
            ('approved', '=', False),
            ('inspection_date', '>=', fields.Date.today())
        ])


class CoconutHRIntegration(models.Model):
    """Integration with HR/payroll module"""
    _name = 'coconut.hr.integration'
    _description = 'Coconut HR/Payroll Integration'

    @api.model
    def create_timesheet_from_work_order(self, work_order_id):
        """Create HR timesheet entry from work order"""
        work_order = self.env['coconut.work.order'].browse(work_order_id)
        if not work_order.exists():
            return
        
        for employee in work_order.employee_ids:
            self.env['hr.timesheet'].create({
                'employee_id': employee.id,
                'date': work_order.actual_start.date() if work_order.actual_start else fields.Date.today(),
                'project_id': self._get_production_project_id(),
                'unit_amount': work_order.total_labor_hours / len(work_order.employee_ids),
                'name': f'Work on {work_order.production_order_id.name} - {work_order.name}',
                'account_id': self._get_analytic_account_id(),
            })
    
    @api.model
    def _get_production_project_id(self):
        """Get or create production project"""
        project = self.env['project.project'].search([
            ('name', '=', 'Coconut Production')
        ], limit=1)
        if not project:
            project = self.env['project.project'].create({
                'name': 'Coconut Production',
                'allow_timesheets': True,
            })
        return project.id
    
    @api.model
    def _get_analytic_account_id(self):
        """Get analytic account for production"""
        account = self.env['account.analytic.account'].search([
            ('name', '=', 'Coconut Production')
        ], limit=1)
        if not account:
            account = self.env['account.analytic.account'].create({
                'name': 'Coconut Production',
                'code': 'COCONUT-PROD',
            })
        return account.id
    
    @api.model
    def sync_work_hours_to_payroll(self, date_from, date_to):
        """Sync work hours to payroll for payroll calculation"""
        timesheets = self.env['hr.timesheet'].search([
            ('date', '>=', date_from),
            ('date', '<=', date_to),
            ('project_id.name', '=', 'Coconut Production')
        ])
        
        # Group by employee
        employee_hours = {}
        for ts in timesheets:
            if ts.employee_id.id not in employee_hours:
                employee_hours[ts.employee_id.id] = {
                    'employee': ts.employee_id,
                    'hours': 0.0,
                }
            employee_hours[ts.employee_id.id]['hours'] += ts.unit_amount
        
        # This would ideally create payslip entries
        # Simplified for demo
        return employee_hours
