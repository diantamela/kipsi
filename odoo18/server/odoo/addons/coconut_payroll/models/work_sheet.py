import logging
import math
from odoo import api, fields, models, _
from odoo.exceptions import ValidationError, UserError

_logger = logging.getLogger(__name__)

class CoconutWorkSheet(models.Model):
    _name = 'coconut.work.sheet'
    _description = 'Lembar Kerja Harian'
    _order = 'date desc, id desc'

    name = fields.Char(
        string='No. Dokumen',
        required=True,
        copy=False,
        readonly=True,
        default=lambda self: _('New')
    )

    date = fields.Date(
        string='Tanggal',
        required=True,
        default=fields.Date.context_today,
        index=True,
    )

    worker_type = fields.Selection([
        ('parer', 'Parer'),
        ('sheller_manual', 'Sheller Manual'),
        ('sheller_mesin', 'Sheller Mesin'),
    ], string='Jenis Pekerjaan', required=True)

    day_type = fields.Selection([
        ('biasa', 'Hari Biasa'),
        ('merah', 'Hari Merah'),
    ], string='Tipe Hari', required=True)

    production_reference = fields.Char(
        string='Referensi Produksi',
    )

    total_production_qty = fields.Float(
        string='Total Produksi (Kg)',
        compute='_compute_total_production_qty',
        store=True,
        readonly=True,
    )

    @api.depends('work_result_ids.quantity_kg')
    def _compute_total_production_qty(self):
        for record in self:
            record.total_production_qty = sum(record.work_result_ids.mapped('quantity_kg'))

    state = fields.Selection([
        ('draft', 'Draft'),
        ('validated', 'Validated'),
        ('processed', 'Processed'),
        ('cancelled', 'Batal'),
    ], string='Status', default='draft', required=True, index=True, copy=False)

    work_result_ids = fields.One2many(
        'coconut.work.result',
        'work_sheet_id',
        string='Hasil Kerja Karyawan',
    )

    company_id = fields.Many2one(
        'res.company',
        string='Perusahaan',
        required=True,
        default=lambda self: self.env.company,
        index=True,
    )

    @api.model_create_multi
    def create(self, vals_list):
        for vals in vals_list:
            if vals.get('name', _('New')) == _('New'):
                date_str = vals.get('date', fields.Date.context_today(self))
                w_type = vals.get('worker_type', '').upper()
                seq = self.env['ir.sequence'].next_by_code('coconut.work.sheet') or '/'
                vals['name'] = f"WS/{date_str}/{w_type}/{seq}"
        return super().create(vals_list)

    @api.onchange('worker_type')
    def _onchange_worker_type(self):
        if self.worker_type:
            employees = self.env['hr.employee'].search([
                ('active', '=', True),
                ('payroll_job_type', '=', self.worker_type),
            ])

            _logger.info(
                "WORK SHEET %s FOUND EMPLOYEE %s",
                self.worker_type,
                len(employees)
            )
            self.work_result_ids = [(5, 0, 0)] + [
                (0, 0, {
                    'employee_id': employee.id,
                    'quantity_kg': 0
                })
                for employee in employees
            ]
        else:
            self.work_result_ids = [(5, 0, 0)]

    def action_validate(self):
        if not self.env.su and not (self.env.user.has_group('coconut_payroll.group_coconut_payroll_supervisor') or 
                                    self.env.user.has_group('coconut_payroll.group_coconut_payroll_manager')):
            raise UserError(_("Hanya Supervisor atau Manager Penggajian yang dapat memvalidasi hasil kerja."))

        for record in self:
            if record.state != 'draft':
                raise UserError(_("Hanya dokumen berstatus Draft yang dapat divalidasi."))

            # Unlink work results where quantity is 0 or less (they didn't work)
            zero_lines = record.work_result_ids.filtered(lambda r: r.quantity_kg <= 0)
            if zero_lines:
                zero_lines.unlink()
                record.invalidate_recordset(fnames=['work_result_ids', 'total_production_qty'])

            if not record.work_result_ids:
                raise ValidationError(_("Hasil kerja karyawan harus diisi."))
            if record.total_production_qty <= 0:
                raise ValidationError(_("Total produksi harus lebih besar dari 0."))

            total_worker_qty = sum(record.work_result_ids.mapped('quantity_kg'))
            if not math.isclose(total_worker_qty, record.total_production_qty, abs_tol=1e-2):
                raise ValidationError(_("Total hasil kerja karyawan tidak sama dengan total produksi."))

            # Ensure detail lines have correct rate, basic wage, and premium populated and stored as snapshot
            for res in record.work_result_ids:
                # Compute rules dynamically
                res._calculate_and_snapshot_wages()
                res.state = 'validated'

            record.state = 'validated'

    def action_draft(self):
        for record in self:
            if record.state == 'processed':
                raise UserError(_("Hasil kerja yang sudah diproses ke rekapitulasi tidak dapat diubah ke Draft."))
            if any(res.state in ['processed', 'paid'] for res in record.work_result_ids):
                raise UserError(_("Hasil kerja tidak dapat diubah ke Draft karena ada hasil kerja yang sudah diproses atau dibayar."))
            record.state = 'draft'
            record.work_result_ids.write({'state': 'draft'})

    def action_cancel(self):
        for record in self:
            if record.state == 'processed':
                raise UserError(_("Hasil kerja yang sudah diproses ke rekapitulasi tidak dapat dibatalkan."))
            record.state = 'cancelled'
            record.work_result_ids.write({'state': 'cancelled'})

    def write(self, vals):
        for record in self:
            if record.state in ['validated', 'processed'] and not self.env.context.get('bypass_work_sheet_lock'):
                raise ValidationError(_("Dokumen yang sudah divalidasi atau diproses tidak dapat diubah."))
        return super().write(vals)

    def unlink(self):
        for record in self:
            if record.state in ['validated', 'processed']:
                raise ValidationError(_("Dokumen yang sudah divalidasi atau diproses tidak dapat dihapus."))
        return super().unlink()
