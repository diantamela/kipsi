from odoo import models, fields, api

class CoconutWorkOrder(models.Model):
    """Work orders for coconut production lines"""
    _name = 'coconut.work.order'
    _description = 'Coconut Work Order'
    _inherit = ['mail.thread', 'mail.activity.mixin']

    name = fields.Char(string='Work Order', required=True, copy=False,
                      default=lambda self: _('New'))
    production_order_id = fields.Many2one('coconut.production.order', 
                                          string='Production Order', required=True)
    workcenter_id = fields.Many2one('mrp.workcenter', string='Work Center', required=True)
    responsible_id = fields.Many2one('res.users', string='Supervisor',
                                    default=lambda self: self.env.user)
    
    # Schedule
    scheduled_start = fields.Datetime(string='Scheduled Start', required=True)
    scheduled_end = fields.Datetime(string='Scheduled End')
    actual_start = fields.Datetime(string='Actual Start')
    actual_end = fields.Datetime(string='Actual End')
    
    # Labor tracking (HR integration)
    employee_ids = fields.Many2many('hr.employee', string='Operators')
    total_labor_hours = fields.Float(string='Total Labor Hours')
    labor_cost = fields.Monetary(string='Labor Cost', compute='_compute_labor_cost')
    currency_id = fields.Many2one('res.currency', string='Currency',
                                 default=lambda self: self.env.company.currency_id)
    
    # Output
    produced_qty = fields.Float(string='Quantity Produced')
    rejected_qty = fields.Float(string='Quantity Rejected')
    efficiency = fields.Float(string='Efficiency %', compute='_compute_efficiency')
    
    # Status
    state = fields.Selection([
        ('draft', 'Draft'),
        ('ready', 'Ready'),
        ('progress', 'In Progress'),
        ('done', 'Completed'),
        ('cancel', 'Cancelled'),
    ], string='Status', default='draft', tracking=True)
    
    notes = fields.Text(string='Work Notes')
    
    @api.model_create_multi
    def create(self, vals_list):
        for vals in vals_list:
            if vals.get('name', _('New')) == _('New'):
                vals['name'] = self.env['ir.sequence'].next_by_code('coconut.work.order') or _('New')
        return super().create(vals_list)
    
    @api.depends('employee_ids', 'total_labor_hours')
    def _compute_labor_cost(self):
        for wo in self:
            # Get average hourly rate from employees
            total_rate = sum(wo.employee_ids.mapped('hourly_rate'))
            emp_count = len(wo.employee_ids) if wo.employee_ids else 1
            avg_rate = total_rate / emp_count if emp_count > 0 else 0
            wo.labor_cost = avg_rate * wo.total_labor_hours
    
    @api.depends('scheduled_start', 'scheduled_end', 'actual_start', 'actual_end')
    def _compute_efficiency(self):
        for wo in self:
            if wo.scheduled_start and wo.scheduled_end and wo.actual_start and wo.actual_end:
                planned = (wo.scheduled_end - wo.scheduled_start).total_seconds() / 3600
                actual = (wo.actual_end - wo.actual_start).total_seconds() / 3600
                if planned > 0:
                    wo.efficiency = (planned / actual) * 100 if actual > 0 else 0
                else:
                    wo.efficiency = 0.0
            else:
                wo.efficiency = 0.0
    
    def action_start(self):
        self.write({'state': 'progress', 'actual_start': fields.Datetime.now()})
    
    def action_pause(self):
        self.write({'state': 'ready'})
    
    def action_resume(self):
        self.write({'state': 'progress'})
    
    def action_finish(self):
        self.write({'state': 'done', 'actual_end': fields.Datetime.now()})


class CoconutProductionReport(models.Model):
    """Production efficiency reporting"""
    _name = 'coconut.production.report'
    _description = 'Coconut Production Report'
    _auto = False
    _rec_name = 'date'

    date = fields.Date(string='Date')
    product_id = fields.Many2one('product.product', string='Product')
    batch_count = fields.Integer(string='Number of Batches')
    planned_qty = fields.Float(string='Planned Qty')
    actual_qty = fields.Float(string='Actual Qty')
    rejected_qty = fields.Float(string='Rejected Qty')
    yield_rate = fields.Float(string='Yield %')
    efficiency = fields.Float(string='Efficiency %')
    total_duration = fields.Float(string='Total Duration (hrs)')
    labor_hours = fields.Float(string='Labor Hours')
    
    def init(self):
        self._cr.execute("""
            CREATE OR REPLACE VIEW coconut_production_report AS (
                SELECT
                    row_number() OVER () as id,
                    DATE(mpo.date_planned_start) as date,
                    mpo.product_id as product_id,
                    COUNT(DISTINCT po.batch_id) as batch_count,
                    po.planned_qty as planned_qty,
                    po.actual_qty as actual_qty,
                    po.rejected_qty as rejected_qty,
                    po.yield_rate as yield_rate,
                    po.efficiency as efficiency,
                    po.actual_duration as total_duration,
                    SUM(wo.total_labor_hours) as labor_hours
                FROM coconut_production_order po
                LEFT JOIN mrp_production mpo ON po.production_id = mpo.id
                LEFT JOIN coconut_work_order wo ON wo.production_order_id = po.id
                WHERE po.state = 'done'
                GROUP BY DATE(mpo.date_planned_start), po.id, po.product_id, 
                         po.planned_qty, po.actual_qty, po.rejected_qty, 
                         po.yield_rate, po.efficiency, po.actual_duration
            )
        """)
