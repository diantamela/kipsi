from odoo import models, fields, api, _
from odoo.exceptions import ValidationError, UserError


class CoconutProductionOrder(models.Model):
    """Production orders for coconut processing"""
    _name = 'coconut.production.order'
    _description = 'Coconut Production Order'
    _inherit = ['mail.thread', 'mail.activity.mixin']
    _order = 'create_date desc'

    name = fields.Char(string='Production Order', required=True, copy=False,
                      default=lambda self: _('New'))
    production_id = fields.Many2one('mrp.production', string='Manufacturing Order')
    product_id = fields.Many2one('product.product', string='Finished Product', required=True,
                                domain="[('coconut_product_ids', '!=', False)]")
    
    # Production planning
    planned_start_date = fields.Datetime(string='Planned Start', required=True,
                                        default=fields.Datetime.now)
    planned_end_date = fields.Datetime(string='Planned End')
    actual_start_date = fields.Datetime(string='Actual Start')
    actual_end_date = fields.Datetime(string='Actual End')
    
    # Quantities
    planned_qty = fields.Float(string='Planned Quantity', required=True,
                              digits='Product Unit of Measure')
    actual_qty = fields.Float(string='Actual Produced', 
                             digits='Product Unit of Measure')
    rejected_qty = fields.Float(string='Rejected Quantity',
                               digits='Product Unit of Measure')
    
    # Batch tracking
    batch_ids = fields.Many2many('coconut.batch', string='Coconut Batches Used')
    total_raw_material = fields.Float(string='Total Raw Material Used (kg)', 
                                      compute='_compute_total_raw_material')
    
    # Work center
    workcenter_id = fields.Many2one('mrp.workcenter', string='Production Line')
    responsible_id = fields.Many2one('res.users', string='Production Manager',
                                    default=lambda self: self.env.user)
    
    # Status
    state = fields.Selection([
        ('draft', 'Draft'),
        ('planned', 'Planned'),
        ('in_progress', 'In Progress'),
        ('to_approve', 'To Approve'),
        ('done', 'Done'),
        ('cancel', 'Cancelled'),
    ], string='Status', default='draft', tracking=True)
    
    # Material requirements (calculated from BoM)
    bom_id = fields.Many2one('mrp.bom', string='Bill of Materials')
    material_requirements = fields.One2many('coconut.material.requirement', 
                                           'production_order_id', 
                                           string='Material Requirements')
    
    # Performance metrics
    planned_duration = fields.Float(string='Planned Duration (hours)')
    actual_duration = fields.Float(string='Actual Duration (hours)')
    efficiency = fields.Float(string='Efficiency %', compute='_compute_efficiency')
    yield_rate = fields.Float(string='Yield Rate %', compute='_compute_yield_rate')
    
    notes = fields.Text(string='Production Notes')
    
    @api.model_create_multi
    def create(self, vals_list):
        for vals in vals_list:
            if vals.get('name', _('New')) == _('New'):
                vals['name'] = self.env['ir.sequence'].next_by_code('coconut.production.order') or _('New')
        return super().create(vals_list)
    
    @api.depends('batch_ids', 'batch_ids.quantity_received')
    def _compute_total_raw_material(self):
        for order in self:
            order.total_raw_material = sum(order.batch_ids.mapped('quantity_received'))
    
    @api.depends('planned_qty', 'actual_qty')
    def _compute_efficiency(self):
        for order in self:
            if order.planned_qty > 0:
                order.efficiency = (order.actual_qty / order.planned_qty) * 100
            else:
                order.efficiency = 0.0
    
    @api.depends('actual_qty', 'rejected_qty', 'total_raw_material')
    def _compute_yield_rate(self):
        for order in self:
            total_output = order.actual_qty + order.rejected_qty
            if order.total_raw_material > 0:
                order.yield_rate = (total_output / order.total_raw_material) * 100
            else:
                order.yield_rate = 0.0
    
    def action_plan(self):
        self.ensure_one()
        self._generate_material_requirements()
        self.write({'state': 'planned'})
    
    def action_start(self):
        self.ensure_one()
        if not self.batch_ids:
            raise UserError(_('Must assign coconut batches before starting production.'))
        self.write({
            'state': 'in_progress',
            'actual_start_date': fields.Datetime.now()
        })
    
    def action_finish(self):
        self.ensure_one()
        self.write({
            'state': 'to_approve',
            'actual_end_date': fields.Datetime.now()
        })
    
    def action_approve(self):
        self.ensure_one()
        self.write({'state': 'done'})
        # Update batch consumption records
        for batch in self.batch_ids:
            batch.write({
                'consumed_by_production': [(4, self.production_id.id)]
            })
    
    def action_cancel(self):
        self.ensure_one()
        if self.state == 'done':
            raise UserError(_('Cannot cancel completed production order.'))
        self.write({'state': 'cancel'})
    
    def _generate_material_requirements(self):
        """Generate material requirements from Bill of Materials"""
        self.ensure_one()
        self.material_requirements.unlink()
        
        if not self.bom_id:
            # Auto-select BoM based on product
            bom = self.env['mrp.bom'].search([
                ('product_tmpl_id', '=', self.product_id.product_tmpl_id.id),
                ('company_id', '=', self.env.company.id),
            ], limit=1)
            if not bom:
                raise UserError(_('No Bill of Materials found for %s') % self.product_id.name)
            self.bom_id = bom.id
        
        # Calculate required quantities based on planned production
        for bom_line in self.bom_id.bom_line_ids:
            self.env['coconut.material.requirement'].create({
                'production_order_id': self.id,
                'bom_line_id': bom_line.id,
                'product_id': bom_line.product_id.id,
                'planned_qty': bom_line.product_qty * self.planned_qty,
                'uom_id': bom_line.product_uom_id.id,
            })


class CoconutMaterialRequirement(models.Model):
    """Material requirements for production"""
    _name = 'coconut.material.requirement'
    _description = 'Coconut Material Requirement'

    production_order_id = fields.Many2one('coconut.production.order', 
                                          string='Production Order', required=True)
    bom_line_id = fields.Many2one('mrp.bom.line', string='BoM Line')
    product_id = fields.Many2one('product.product', string='Material', required=True)
    
    planned_qty = fields.Float(string='Planned Qty', required=True)
    actual_qty = fields.Float(string='Actual Qty Used')
    uom_id = fields.Many2one('uom.uom', string='Unit')
    
    # Batches used
    batch_ids = fields.Many2many('coconut.batch', string='Batches Used')
    
    # Variance
    variance_qty = fields.Float(string='Variance', compute='_compute_variance')
    variance_percent = fields.Float(string='Variance %', compute='_compute_variance')
    
    @api.depends('planned_qty', 'actual_qty')
    def _compute_variance(self):
        for req in self:
            req.variance_qty = req.actual_qty - req.planned_qty
            if req.planned_qty > 0:
                req.variance_percent = (req.variance_qty / req.planned_qty) * 100
            else:
                req.variance_percent = 0.0


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
    
    # Labor
    employee_ids = fields.Many2many('hr.employee', string='Operators')
    total_labor_hours = fields.Float(string='Total Labor Hours')
    
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
                    SUM(wo.labor_hours) as labor_hours
                FROM coconut_production_order po
                LEFT JOIN mrp_production mpo ON po.production_id = mpo.id
                LEFT JOIN coconut_work_order wo ON wo.production_order_id = po.id
                WHERE po.state = 'done'
                GROUP BY DATE(mpo.date_planned_start), po.id, po.product_id, 
                         po.planned_qty, po.actual_qty, po.rejected_qty, 
                         po.yield_rate, po.efficiency, po.actual_duration
            )
        """)
