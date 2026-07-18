# -*- coding: utf-8 -*-
import math
from odoo import api, fields, models, _
from odoo.exceptions import ValidationError, UserError

class CoconutPayrollPeriod(models.Model):
    _name = 'coconut.payroll.period'
    _description = 'Periode Penggajian'
    _order = 'date_start desc, id desc'

    name = fields.Char(
        string='Nama Periode',
        required=True,
    )

    date_start = fields.Date(
        string='Tanggal Mulai',
        required=True,
    )

    date_end = fields.Date(
        string='Tanggal Selesai',
        required=True,
    )

    state = fields.Selection([
        ('draft', 'Draft'),
        ('calculated', 'Calculated'),
        ('confirmed', 'Confirmed'),
        ('paid', 'Paid'),
        ('cancelled', 'Cancelled'),
    ], string='Status', default='draft', required=True, index=True, copy=False)

    payroll_line_ids = fields.One2many(
        'coconut.payroll.line',
        'period_id',
        string='Rincian Gaji',
    )

    company_id = fields.Many2one(
        'res.company',
        string='Perusahaan',
        required=True,
        default=lambda self: self.env.company,
        index=True,
    )

    currency_id = fields.Many2one(
        'res.currency',
        related='company_id.currency_id',
        store=True,
        readonly=True,
    )

    total_gross = fields.Monetary(
        string='Total Gross',
        currency_field='currency_id',
        compute='_compute_totals',
        store=True,
    )

    total_deduction = fields.Monetary(
        string='Total Deduction',
        currency_field='currency_id',
        compute='_compute_totals',
        store=True,
    )

    total_net = fields.Monetary(
        string='Total Net',
        currency_field='currency_id',
        compute='_compute_totals',
        store=True,
    )

    notes = fields.Text(
        string='Catatan',
    )

    @api.depends('payroll_line_ids.gross_income', 'payroll_line_ids.total_deduction', 'payroll_line_ids.net_income')
    def _compute_totals(self):
        for record in self:
            record.total_gross = sum(record.payroll_line_ids.mapped('gross_income'))
            record.total_deduction = sum(record.payroll_line_ids.mapped('total_deduction'))
            record.total_net = sum(record.payroll_line_ids.mapped('net_income'))

    @api.constrains('date_start', 'date_end', 'company_id')
    def _check_dates_and_overlap(self):
        for record in self:
            if record.date_start and record.date_end:
                if record.date_start > record.date_end:
                    raise ValidationError(_("Tanggal Mulai tidak boleh melebihi Tanggal Selesai."))
                
                overlap = self.search([
                    ('id', '!=', record.id),
                    ('company_id', '=', record.company_id.id),
                    ('state', '!=', 'cancelled'),
                    ('date_start', '<=', record.date_end),
                    ('date_end', '>=', record.date_start),
                ], limit=1)
                
                if overlap:
                    raise ValidationError(_(
                        "Periode penggajian tumpang tindih dengan periode '%s' (%s sampai %s) pada perusahaan yang sama."
                    ) % (overlap.name, overlap.date_start, overlap.date_end))

    def unlink(self):
        if not self.env.user.has_group('coconut_payroll.group_coconut_payroll_manager'):
            raise UserError(_("Hanya Manager Penggajian yang dapat menghapus periode penggajian."))
        for record in self:
            if record.state != 'draft':
                raise UserError(_("Hanya periode penggajian berstatus Draft yang dapat dihapus."))
        return super().unlink()

    def action_calculate(self):
        if not self.env.su and not (self.env.user.has_group('coconut_payroll.group_coconut_payroll_supervisor') or 
                                    self.env.user.has_group('coconut_payroll.group_coconut_payroll_manager')):
            raise UserError(_("Hanya Supervisor atau Manager Penggajian yang dapat menghitung payroll."))
        
        for period in self:
            if period.state not in ['draft', 'calculated']:
                raise UserError(_("Kalkulasi payroll hanya dapat dilakukan pada periode Draft atau Calculated."))

            # 1. Fetch eligible work results
            work_results = self.env['coconut.work.result'].search([
                ('company_id', '=', period.company_id.id),
                ('date', '>=', period.date_start),
                ('date', '<=', period.date_end),
                ('state', '=', 'validated'),
                '|',
                ('payroll_line_id', '=', False),
                ('payroll_period_id', '=', period.id),
            ])

            # 2. Group by employee
            employee_wr = {}
            for wr in work_results:
                employee_wr.setdefault(wr.employee_id, []).append(wr)

            # 3. Track processed lines to detect obsolete lines
            processed_lines = self.env['coconut.payroll.line']

            for employee, wr_list in employee_wr.items():
                line = period.payroll_line_ids.filtered(lambda l: l.employee_id == employee)
                wr_ids = [wr.id for wr in wr_list]
                
                if line:
                    # Update existing line
                    line.with_context(bypass_work_result_lock=True).write({
                        'work_result_ids': [(6, 0, wr_ids)]
                    })
                    processed_lines |= line
                    # Get worker type from work results if available, otherwise fallback to department-based mapping
                    w_type = wr_list[0].worker_type if wr_list else False
                    if not w_type:
                        dep_name = employee.department_id.name or ''
                        dep_display = employee.department_id.display_name or ''
                        if 'Parer' in dep_name or 'Parer' in dep_display:
                            w_type = 'parer'
                        elif 'Sheller Manual' in dep_name or 'Sheller Manual' in dep_display:
                            w_type = 'sheller_manual'
                        elif 'Sheller Mesin' in dep_name or 'Sheller Mesin' in dep_display:
                            w_type = 'sheller_mesin'
                        else:
                            w_type = employee.payroll_worker_type or 'parer'

                    new_line = self.env['coconut.payroll.line'].create({
                        'period_id': period.id,
                        'employee_id': employee.id,
                        'worker_type': w_type,
                        'work_result_ids': [(6, 0, wr_ids)],
                    })
                    processed_lines |= new_line

            # 4. Handle obsolete lines
            for line in period.payroll_line_ids - processed_lines:
                # Check if it has any manual inputs
                has_manual = (
                    line.target_premium != 0.0 or
                    line.additional_hours != 0.0 or
                    line.overtime_hours != 0.0 or
                    line.arrears != 0.0 or
                    line.other_income != 0.0 or
                    line.salary_overpayment_deduction != 0.0 or
                    line.tool_deduction != 0.0 or
                    line.axe_blade_deduction != 0.0 or
                    line.sack_deduction != 0.0 or
                    line.other_deduction != 0.0 or
                    line.notes
                )
                if not has_manual:
                    line.unlink()
                else:
                    # Keep the line, but clear its work results
                    line.with_context(bypass_work_result_lock=True).write({
                        'work_result_ids': [(5, 0, 0)]
                    })

            # Trigger recalculation for all lines
            period.payroll_line_ids._compute_all_fields()
            period.write({'state': 'calculated'})

    def action_confirm(self):
        if not self.env.su and not (self.env.user.has_group('coconut_payroll.group_coconut_payroll_supervisor') or 
                                    self.env.user.has_group('coconut_payroll.group_coconut_payroll_manager')):
            raise UserError(_("Hanya Supervisor atau Manager Penggajian yang dapat mengonfirmasi payroll."))
        for period in self:
            if period.state != 'calculated':
                raise UserError(_("Hanya payroll dengan status Calculated yang dapat dikonfirmasi."))
        self.write({'state': 'confirmed'})

    def action_paid(self):
        if not self.env.su and not self.env.user.has_group('coconut_payroll.group_coconut_payroll_manager'):
            raise UserError(_("Hanya Manager Penggajian yang dapat menandai payroll sebagai Lunas (Paid)."))
        for period in self:
            if period.state != 'confirmed':
                raise UserError(_("Hanya payroll dengan status Confirmed yang dapat ditandai sebagai Lunas."))
            
            # Set all linked work results state to paid
            for line in period.payroll_line_ids:
                line.work_result_ids.with_context(bypass_work_result_lock=True).write({'state': 'paid'})
                
        self.write({'state': 'paid'})

    def action_cancel(self):
        if not self.env.su and not self.env.user.has_group('coconut_payroll.group_coconut_payroll_manager'):
            raise UserError(_("Hanya Manager Penggajian yang dapat membatalkan payroll."))
        for period in self:
            if period.state != 'confirmed':
                raise UserError(_("Hanya payroll dengan status Confirmed yang dapat dibatalkan."))
                
            # Release work results and set back to validated
            for line in period.payroll_line_ids:
                line.work_result_ids.with_context(bypass_work_result_lock=True).write({
                    'state': 'validated',
                    'payroll_line_id': False
                })
        self.write({'state': 'cancelled'})

    def action_draft(self):
        if not self.env.su and not (self.env.user.has_group('coconut_payroll.group_coconut_payroll_supervisor') or 
                                    self.env.user.has_group('coconut_payroll.group_coconut_payroll_manager')):
            raise UserError(_("Hanya Supervisor atau Manager Penggajian yang dapat mengembalikan status ke Draft."))
        for period in self:
            if period.state not in ['calculated', 'confirmed']:
                raise UserError(_("Hanya payroll dengan status Calculated atau Confirmed yang dapat dikembalikan ke Draft."))
        self.write({'state': 'draft'})
