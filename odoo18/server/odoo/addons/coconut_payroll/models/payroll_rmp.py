# -*- coding: utf-8 -*-
import pytz
from datetime import datetime, time, timedelta
from odoo import api, fields, models, _
from odoo.exceptions import ValidationError, UserError

class CoconutPayrollRmp(models.Model):
    _name = 'coconut.payroll.rmp'
    _description = 'Rekapitulasi Penggajian RMP'
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
        'rmp_recap_id',
        string='Rincian Gaji RMP',
    )

    total_net_salary = fields.Monetary(
        string='Total Gaji Bersih',
        currency_field='currency_id',
        compute='_compute_total_net_salary',
        store=True,
    )

    @api.depends('line_ids.net_salary')
    def _compute_total_net_salary(self):
        for record in self:
            record.total_net_salary = sum(record.line_ids.mapped('net_salary'))

    @api.model_create_multi
    def create(self, vals_list):
        for vals in vals_list:
            if vals.get('name', _('New')) == _('New'):
                date_str = vals.get('date_start', fields.Date.context_today(self))
                seq = self.env['ir.sequence'].next_by_code('coconut.payroll.rmp') or '/'
                vals['name'] = f"REKAP/RMP/{date_str}/{seq}"
        return super(CoconutPayrollRmp, self).create(vals_list)

    @api.constrains('date_start', 'date_end')
    def _check_dates(self):
        for record in self:
            if record.date_start and record.date_end and record.date_start > record.date_end:
                raise ValidationError(_("Tanggal Mulai tidak boleh melebihi Tanggal Selesai."))

    def action_generate(self):
        self.ensure_one()
        if not self.env.su and not (self.env.user.has_group('coconut_payroll.group_coconut_payroll_supervisor') or 
                                    self.env.user.has_group('coconut_payroll.group_coconut_payroll_manager')):
            raise UserError(_("Hanya Supervisor atau Manager Penggajian yang dapat memproses rekapitulasi."))

        if self.state not in ['draft', 'generated']:
            raise UserError(_("Rekapitulasi hanya dapat diproses pada status Draft atau Generated."))

        # Clear old lines
        if self.line_ids:
            self.line_ids.unlink()

        # Find RMP employees based on their department in the employee module
        employees = self.env['hr.employee'].search([
            ('department_id.name', 'ilike', 'RMP'),
            ('active', '=', True),
        ])

        if not employees:
            raise UserError(_("Tidak ditemukan karyawan aktif untuk departemen/pekerjaan RMP."))

        tz = pytz.timezone('Asia/Jakarta')
        start_dt = datetime.combine(self.date_start, time.min)
        end_dt = datetime.combine(self.date_end, time.max)

        # Get all attendance records in the period
        attendances = self.env['hr.attendance'].search([
            ('employee_id', 'in', employees.ids),
            ('check_in', '>=', start_dt),
            ('check_in', '<=', end_dt),
        ])

        # Generate dates list excluding Sundays
        all_dates = []
        curr_date = self.date_start
        while curr_date <= self.date_end:
            if curr_date.weekday() != 6:  # 6 is Sunday
                all_dates.append(curr_date)
            curr_date += timedelta(days=1)

        # Calculate payroll for each employee
        for emp in employees:
            emp_attendances = attendances.filtered(lambda a: a.employee_id == emp)
            
            # Group attendances by local date
            attendances_by_date = {}
            for att in emp_attendances:
                local_check_in = pytz.utc.localize(att.check_in).astimezone(tz)
                local_date = local_check_in.date()
                attendances_by_date.setdefault(local_date, []).append(att)

            hari_hadir = 0
            hari_alpha = 0
            jam_kerja = 0.0
            jam_lembur = 0.0
            terlambat = 0
            pulang_cepat = 0
            wage_pokok = 0.0
            wage_lembur = 0.0
            premi_kehadiran = 0.0
            premi_disiplin = 0.0
            uang_makan = 0.0
            potongan = 0.0

            for d in all_dates:
                day_atts = attendances_by_date.get(d, [])
                if not day_atts:
                    # Alpha
                    hari_alpha += 1
                else:
                    # Present
                    hari_hadir += 1
                    valid_check_outs = [att for att in day_atts if att.check_out]
                    earliest_att = min(day_atts, key=lambda a: a.check_in)
                    check_in_local = pytz.utc.localize(earliest_att.check_in).astimezone(tz)
                    
                    if not valid_check_outs:
                        check_out_local = False
                    else:
                        latest_att = max(valid_check_outs, key=lambda a: a.check_out)
                        check_out_local = pytz.utc.localize(latest_att.check_out).astimezone(tz)

                    # Compute duration
                    total_dur = sum((pytz.utc.localize(a.check_out).astimezone(tz) - pytz.utc.localize(a.check_in).astimezone(tz)).total_seconds() / 3600.0 for a in day_atts if a.check_out)
                    
                    # Deduct 1 hour break if presence > 5 hours
                    if total_dur > 5.0:
                        jam_kerja_hari = total_dur - 1.0
                    else:
                        jam_kerja_hari = total_dur

                    jam_kerja += jam_kerja_hari

                    # Overtime
                    if jam_kerja_hari > 8.0:
                        jam_lembur_hari = jam_kerja_hari - 8.0
                        jam_lembur += jam_lembur_hari
                        wage_lembur += jam_lembur_hari * 10000.0
                        uang_makan += 20000.0

                    # Premi Kehadiran (hadir >= 8 jam)
                    if jam_kerja_hari >= 8.0:
                        premi_kehadiran += 15000.0

                    # Lateness & Early Departure check
                    day_late = check_in_local.time() > time(8, 0)
                    day_early = (not check_out_local) or (check_out_local.time() < time(17, 0))

                    if day_late:
                        terlambat += 1
                        potongan += 5000.0
                    if day_early:
                        pulang_cepat += 1
                        potongan += 5000.0

                    # Premi Disiplin
                    if not day_late and not day_early:
                        premi_disiplin += 5000.0

            # Gaji Pokok
            wage_pokok = hari_hadir * 140000.0
            
            # Net salary calculation
            net_salary = wage_pokok + wage_lembur + premi_kehadiran + premi_disiplin + uang_makan - potongan

            # Create payroll line
            self.env['coconut.payroll.line'].create({
                'rmp_recap_id': self.id,
                'employee_id': emp.id,
                'worker_type': 'rmp',
                'hari_hadir': hari_hadir,
                'hari_alpha': hari_alpha,
                'jam_kerja': jam_kerja,
                'jam_lembur': jam_lembur,
                'terlambat': terlambat,
                'pulang_cepat': pulang_cepat,
                'wage_pokok': wage_pokok,
                'wage_lembur': wage_lembur,
                'premi_kehadiran': premi_kehadiran,
                'premi_disiplin': premi_disiplin,
                'uang_makan': uang_makan,
                'potongan': potongan,
                'net_salary': net_salary,
            })

        self.state = 'generated'

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
        self.write({'state': 'paid'})

    def action_cancel(self):
        if not self.env.su and not self.env.user.has_group('coconut_payroll.group_coconut_payroll_manager'):
            raise UserError(_("Hanya Manager Penggajian yang dapat membatalkan rekapitulasi."))
        for record in self:
            if record.state == 'paid':
                raise UserError(_("Rekapitulasi yang sudah Lunas tidak dapat dibatalkan."))
        self.line_ids.unlink()
        self.write({'state': 'cancelled'})

    def action_draft(self):
        for record in self:
            if record.state not in ['generated', 'approved']:
                raise UserError(_("Hanya rekapitulasi dengan status Generated atau Disetujui yang dapat dikembalikan ke Draft."))
        self.write({'state': 'draft'})

    def unlink(self):
        for record in self:
            if record.state != 'draft':
                raise UserError(_("Hanya rekapitulasi dengan status Draft yang dapat dihapus."))
        return super(CoconutPayrollRmp, self).unlink()

    def action_print_all_payslips(self):
        self.ensure_one()
        return self.env.ref('coconut_payroll.action_report_payslip').report_action(self.line_ids)
