# -*- coding: utf-8 -*-
from odoo import api, fields, models, _
from odoo.exceptions import ValidationError, UserError

class CoconutPayrollRecap(models.Model):
    _name = 'coconut.payroll.recap'
    _description = 'Rekapitulasi Penggajian'
    _order = 'date_start desc, id desc'

    name = fields.Char(
        string='No. Rekapitulasi',
        required=True,
        copy=False,
        readonly=True,
        default=lambda self: _('New')
    )

    date_start = fields.Date(
        string='Tanggal Mulai',
        required=True,
    )

    date_end = fields.Date(
        string='Tanggal Selesai',
        required=True,
    )

    worker_type = fields.Selection([
        ('parer', 'Parer'),
        ('sheller_manual', 'Sheller Manual'),
        ('sheller_mesin', 'Sheller Mesin'),
    ], string='Jenis Pekerja', required=True)

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

    state = fields.Selection([
        ('draft', 'Draft'),
        ('generated', 'Generated'),
        ('approved', 'Disetujui'),
        ('paid', 'Lunas'),
        ('cancelled', 'Batal'),
    ], string='Status', default='draft', required=True, index=True, copy=False)

    line_ids = fields.One2many(
        'coconut.payroll.line',
        'recap_id',
        string='Rincian Gaji',
    )

    @api.model_create_multi
    def create(self, vals_list):
        for vals in vals_list:
            if vals.get('name', _('New')) == _('New'):
                date_str = vals.get('date_start', fields.Date.context_today(self))
                w_type = vals.get('worker_type', '').upper()
                seq = self.env['ir.sequence'].next_by_code('coconut.payroll.recap') or '/'
                vals['name'] = f"REKAP/{date_str}/{w_type}/{seq}"
        return super().create(vals_list)

    def action_generate(self):
        if not self.env.su and not (self.env.user.has_group('coconut_payroll.group_coconut_payroll_supervisor') or 
                                    self.env.user.has_group('coconut_payroll.group_coconut_payroll_manager')):
            raise UserError(_("Hanya Supervisor atau Manager Penggajian yang dapat memproses rekapitulasi."))

        for record in self:
            if record.state not in ['draft', 'generated']:
                raise UserError(_("Rekapitulasi hanya dapat diproses pada status Draft atau Generated."))

            # Clear old lines if generated again
            if record.line_ids:
                # Release linked work results first
                for line in record.line_ids:
                    line.work_result_ids.write({
                        'recap_line_id': False,
                        'state': 'validated'
                    })
                record.line_ids.unlink()

            # Find matching validated and un-recapitulated work results
            work_results = self.env['coconut.work.result'].search([
                ('worker_type', '=', record.worker_type),
                ('date', '>=', record.date_start),
                ('date', '<=', record.date_end),
                ('state', '=', 'validated'),
                ('recap_line_id', '=', False),
                ('company_id', '=', record.company_id.id),
            ])

            if not work_results:
                raise ValidationError(_("Tidak ditemukan data hasil kerja harian tervalidasi yang belum diproses untuk periode ini."))

            # Group by employee
            employee_groups = {}
            for res in work_results:
                employee_groups.setdefault(res.employee_id, []).append(res)

            for employee, results in employee_groups.items():
                total_qty = sum(r.quantity_kg for r in results)
                basic_wage = sum(r.basic_wage for r in results)
                premium = sum(r.premium for r in results)
                gross = basic_wage + premium

                # Loan deduction calculation
                loan = self.env['coconut.employee.loan'].search([
                    ('employee_id', '=', employee.id),
                    ('state', '=', 'active'),
                    ('remaining_amount', '>', 0.0),
                ], order='id asc', limit=1)

                loan_deduction = 0.0
                if loan:
                    loan_deduction = min(loan.installment_amount, loan.remaining_amount)

                # Create recap line
                line_vals = {
                    'recap_id': record.id,
                    'employee_id': employee.id,
                    'worker_type': record.worker_type,
                    'total_quantity_kg': total_qty,
                    'basic_wage': basic_wage,
                    'premium': premium,
                    'gross_salary': gross,
                    'loan_deduction': loan_deduction,
                    'net_salary': gross - loan_deduction,
                }
                recap_line = self.env['coconut.payroll.line'].create(line_vals)

                # Link results to line and update state
                for r in results:
                    r.with_context(bypass_work_result_lock=True).write({
                        'recap_line_id': recap_line.id,
                        'state': 'processed'
                    })

            # Update related work sheets state to processed
            sheets = work_results.mapped('work_sheet_id')
            for sheet in sheets:
                sheet.with_context(bypass_work_sheet_lock=True).write({'state': 'processed'})

            record.state = 'generated'

    def action_approve(self):
        if not self.env.su and not self.env.user.has_group('coconut_payroll.group_coconut_payroll_manager'):
            raise UserError(_("Hanya Manager Penggajian yang dapat menyetujui rekapitulasi."))
        for record in self:
            if record.state != 'generated':
                raise UserError(_("Hanya rekapitulasi dengan status Generated yang dapat disetujui."))
        self.write({'state': 'approved'})

    def action_paid(self):
        if not self.env.su and not self.env.user.has_group('coconut_payroll.group_coconut_payroll_manager'):
            raise UserError(_("Hanya Manager Penggajian yang dapat memproses pembayaran rekapitulasi."))
        for record in self:
            if record.state != 'approved':
                raise UserError(_("Hanya rekapitulasi dengan status Disetujui yang dapat dibayar."))

            for line in record.line_ids:
                # Set work results state to paid
                line.work_result_ids.with_context(bypass_work_result_lock=True).write({'state': 'paid'})

                # Create loan installment history if deduction is applied
                if line.loan_deduction > 0.0:
                    loan = self.env['coconut.employee.loan'].search([
                        ('employee_id', '=', line.employee_id.id),
                        ('state', '=', 'active'),
                        ('remaining_amount', '>', 0.0),
                    ], order='id asc', limit=1)

                    if loan:
                        self.env['coconut.loan.installment'].create({
                            'loan_id': loan.id,
                            'recap_line_id': line.id,
                            'date': fields.Date.context_today(self),
                            'amount': line.loan_deduction,
                            'state': 'posted'
                        })

            record.state = 'paid'

    def action_cancel(self):
        if not self.env.su and not self.env.user.has_group('coconut_payroll.group_coconut_payroll_manager'):
            raise UserError(_("Hanya Manager Penggajian yang dapat membatalkan rekapitulasi."))
        for record in self:
            if record.state == 'paid':
                raise UserError(_("Rekapitulasi yang sudah Lunas tidak dapat dibatalkan."))

            # Revert work results and sheets status
            for line in record.line_ids:
                work_results = line.work_result_ids
                work_results.with_context(bypass_work_result_lock=True).write({
                    'recap_line_id': False,
                    'state': 'validated'
                })
                # Revert work sheets state if no other processed results remain on them
                sheets = work_results.mapped('work_sheet_id')
                for sheet in sheets:
                    if all(r.state == 'validated' for r in sheet.work_result_ids):
                        sheet.with_context(bypass_work_sheet_lock=True).write({'state': 'validated'})

            record.line_ids.unlink()
            record.state = 'cancelled'

    def action_draft(self):
        for record in self:
            if record.state not in ['generated', 'approved']:
                raise UserError(_("Hanya rekapitulasi dengan status Generated atau Disetujui yang dapat dikembalikan ke Draft."))
        self.write({'state': 'draft'})

    def unlink(self):
        for record in self:
            if record.state != 'draft':
                raise UserError(_("Hanya rekapitulasi dengan status Draft yang dapat dihapus."))
        return super().unlink()

    def action_print_all_payslips(self):
        self.ensure_one()
        return self.env.ref('coconut_payroll.action_report_payslip').report_action(self.line_ids)
