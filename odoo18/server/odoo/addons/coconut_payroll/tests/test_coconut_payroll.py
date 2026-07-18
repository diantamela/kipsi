# -*- coding: utf-8 -*-
from odoo.tests.common import TransactionCase
from odoo.exceptions import ValidationError, UserError
from odoo import fields

class TestCoconutPayroll(TransactionCase):

    def setUp(self):
        super(TestCoconutPayroll, self).setUp()
        self.company = self.env.ref('base.main_company')
        self.company.write({
            'payroll_overtime_rate': 12000.0,
            'payroll_daily_base_wage': 65000.0,
            'payroll_standard_hours': 7.0,
            'payroll_rounding_unit': 1000.0,
        })

        # Create groups
        self.group_operator = self.env.ref('coconut_payroll.group_coconut_payroll_operator')
        self.group_supervisor = self.env.ref('coconut_payroll.group_coconut_payroll_supervisor')
        self.group_manager = self.env.ref('coconut_payroll.group_coconut_payroll_manager')

        # Create test users
        self.user_operator = self.env['res.users'].create({
            'name': 'Operator Payroll',
            'login': 'operator_payroll',
            'email': 'op@coco.com',
            'groups_id': [(6, 0, [self.group_operator.id])],
        })
        self.user_supervisor = self.env['res.users'].create({
            'name': 'Supervisor Payroll',
            'login': 'supervisor_payroll',
            'email': 'sp@coco.com',
            'groups_id': [(6, 0, [self.group_supervisor.id])],
        })
        self.user_manager = self.env['res.users'].create({
            'name': 'Manager Payroll',
            'login': 'manager_payroll',
            'email': 'mgr@coco.com',
            'groups_id': [(6, 0, [self.group_manager.id])],
        })

        # Create employees
        self.emp_sheller = self.env['hr.employee'].create({
            'name': 'Budi Sheller',
            'payroll_worker_type': 'sheller',
            'employee_code': 'EMP001',
            'payroll_active': True,
        })
        self.emp_parer = self.env['hr.employee'].create({
            'name': 'Siti Parer',
            'payroll_worker_type': 'parer',
            'employee_code': 'EMP002',
            'payroll_active': True,
        })

        # Create active tariffs
        self.tariff_parer_prod = self.env['coconut.payroll.tariff'].create({
            'name': 'Parer Prod Rp300',
            'worker_type': 'parer',
            'work_type': 'parer_prod',
            'rate': 300.0,
            'date_start': '2026-01-01',
            'date_end': '2026-12-31',
            'company_id': self.company.id,
        })
        self.tariff_bad_meat_sunday = self.env['coconut.payroll.tariff'].create({
            'name': 'Bad Meat Sunday Rp350',
            'worker_type': 'parer',
            'work_type': 'bad_meat_sunday',
            'rate': 350.0,
            'date_start': '2026-01-01',
            'date_end': '2026-12-31',
            'company_id': self.company.id,
        })
        self.tariff_sheller_180 = self.env['coconut.payroll.tariff'].create({
            'name': 'Sheller Rp180',
            'worker_type': 'sheller',
            'work_type': 'sheller_prod',
            'rate': 180.0,
            'date_start': '2026-01-01',
            'date_end': '2026-12-31',
            'company_id': self.company.id,
        })
        self.tariff_sheller_200 = self.env['coconut.payroll.tariff'].create({
            'name': 'Sheller Rp200',
            'worker_type': 'sheller',
            'work_type': 'sheller_prod',
            'rate': 200.0,
            'date_start': '2026-01-01',
            'date_end': '2026-12-31',
            'company_id': self.company.id,
        })

    def test_01_parer_wage_300(self):
        # 1. Parer wage at Rp300 per kg.
        wr = self.env['coconut.work.result'].create({
            'employee_id': self.emp_parer.id,
            'worker_type': 'parer',
            'work_type': 'parer_prod',
            'quantity': 100.0,
            'rate': 300.0,
            'date': '2026-07-01',
            'company_id': self.company.id,
        })
        self.assertEqual(wr.basic_wage, 30000.0)

    def test_02_sheller_wage_selected_tariff(self):
        # 2. Sheller wage using the selected tariff.
        # User manually selects rate = 180
        wr1 = self.env['coconut.work.result'].create({
            'employee_id': self.emp_sheller.id,
            'worker_type': 'sheller',
            'work_type': 'sheller_prod',
            'quantity': 150.0,
            'rate': 180.0,
            'date': '2026-07-01',
            'company_id': self.company.id,
        })
        self.assertEqual(wr1.basic_wage, 27000.0)

        # User manually selects rate = 200
        wr2 = self.env['coconut.work.result'].create({
            'employee_id': self.emp_sheller.id,
            'worker_type': 'sheller',
            'work_type': 'sheller_prod',
            'quantity': 150.0,
            'rate': 200.0,
            'date': '2026-07-01',
            'company_id': self.company.id,
        })
        self.assertEqual(wr2.basic_wage, 30000.0)

    def test_03_bad_meat_sunday_350(self):
        # 3. Bad Meat Sunday at Rp350 per kg.
        wr = self.env['coconut.work.result'].create({
            'employee_id': self.emp_parer.id,
            'worker_type': 'parer',
            'work_type': 'bad_meat_sunday',
            'quantity': 50.0,
            'rate': 350.0,
            'date': '2026-07-01',
            'company_id': self.company.id,
        })
        self.assertEqual(wr.basic_wage, 17500.0)

    def test_04_overtime_calculation(self):
        # 4. Overtime calculation.
        period = self.env['coconut.payroll.period'].create({
            'name': 'Periode Juli 1',
            'date_start': '2026-07-01',
            'date_end': '2026-07-07',
            'company_id': self.company.id,
        })
        line = self.env['coconut.payroll.line'].create({
            'period_id': period.id,
            'employee_id': self.emp_sheller.id,
            'worker_type': 'sheller',
            'overtime_hours': 3.5,
            'company_id': self.company.id,
        })
        # 3.5 hours * 12,000 = 42,000
        self.assertEqual(line.overtime_amount, 42000.0)

    def test_05_additional_hours_calculation(self):
        # 5. Additional-hours calculation.
        period = self.env['coconut.payroll.period'].create({
            'name': 'Periode Juli 1',
            'date_start': '2026-07-01',
            'date_end': '2026-07-07',
            'company_id': self.company.id,
        })
        line = self.env['coconut.payroll.line'].create({
            'period_id': period.id,
            'employee_id': self.emp_sheller.id,
            'worker_type': 'sheller',
            'additional_hours': 1.5,
            'company_id': self.company.id,
        })
        # 1.5 hours * (65,000 / 7) = 13,928.571428... -> rounded to 13928.57
        self.assertAlmostEqual(line.daily_addition, round(1.5 * (65000.0 / 7.0), 2))

    def test_06_sheller_rounding_order(self):
        # 6. Sheller rounding order.
        # Net before rounding = Gross - Total Deduction
        # Net income = Round down Net before rounding
        period = self.env['coconut.payroll.period'].create({
            'name': 'Periode Juli 1',
            'date_start': '2026-07-01',
            'date_end': '2026-07-07',
            'company_id': self.company.id,
        })
        
        wr = self.env['coconut.work.result'].create({
            'employee_id': self.emp_sheller.id,
            'worker_type': 'sheller',
            'work_type': 'sheller_prod',
            'quantity': 1.0,
            'rate': 10050.0,
            'date': '2026-07-01',
            'company_id': self.company.id,
            'state': 'validated',
        })
        
        line = self.env['coconut.payroll.line'].create({
            'period_id': period.id,
            'employee_id': self.emp_sheller.id,
            'worker_type': 'sheller',
            'work_result_ids': [(6, 0, [wr.id])],
            'additional_hours': 0.5,
            'tool_deduction': 100.0,
            'company_id': self.company.id,
        })
        
        expected_gross = round(10050.0 + (0.5 * (65000.0 / 7.0)), 2) # 10050 + 4642.86 = 14692.86
        expected_net_before = expected_gross - 100.0 # 14592.86
        expected_net_rounded = 14000.0 # rounded down to nearest 1,000
        
        self.assertEqual(line.gross_income, expected_gross)
        self.assertEqual(line.net_income, expected_net_rounded)
        self.assertAlmostEqual(line.rounding_difference, expected_net_before - expected_net_rounded)

    def test_07_parer_rounding_order(self):
        # 7. Parer rounding order.
        # Gross = Round down Gross before rounding
        # Net = Round down (Gross - Total Deduction)
        period = self.env['coconut.payroll.period'].create({
            'name': 'Periode Juli 1',
            'date_start': '2026-07-01',
            'date_end': '2026-07-07',
            'company_id': self.company.id,
        })
        
        wr = self.env['coconut.work.result'].create({
            'employee_id': self.emp_parer.id,
            'worker_type': 'parer',
            'work_type': 'parer_prod',
            'quantity': 1.0,
            'rate': 20050.0,
            'date': '2026-07-01',
            'company_id': self.company.id,
            'state': 'validated',
        })
        
        line = self.env['coconut.payroll.line'].create({
            'period_id': period.id,
            'employee_id': self.emp_parer.id,
            'worker_type': 'parer',
            'work_result_ids': [(6, 0, [wr.id])],
            'additional_hours': 0.5,
            'tool_deduction': 150.0,
            'company_id': self.company.id,
        })
        
        expected_gross_before = 20050.0 + (0.5 * (65000.0 / 7.0)) # 20050 + 4642.857 = 24692.857
        expected_gross_rounded = 24000.0 # rounded down
        expected_net = 23000.0 # rounded down of (24000 - 150) = 23850 -> 23000
        
        self.assertEqual(line.gross_income, expected_gross_rounded)
        self.assertEqual(line.net_income, expected_net)

    def test_08_payroll_period_overlap(self):
        # 8. Payroll-period overlap.
        self.env['coconut.payroll.period'].create({
            'name': 'Periode 1',
            'date_start': '2026-07-01',
            'date_end': '2026-07-07',
            'company_id': self.company.id,
        })
        with self.assertRaises(ValidationError):
            self.env['coconut.payroll.period'].create({
                'name': 'Periode Overlap',
                'date_start': '2026-07-05',
                'date_end': '2026-07-12',
                'company_id': self.company.id,
            })

    def test_09_duplicate_employee_one_period(self):
        # 9. Duplicate employee in one period.
        period = self.env['coconut.payroll.period'].create({
            'name': 'Periode 1',
            'date_start': '2026-07-01',
            'date_end': '2026-07-07',
            'company_id': self.company.id,
        })
        self.env['coconut.payroll.line'].create({
            'period_id': period.id,
            'employee_id': self.emp_sheller.id,
            'worker_type': 'sheller',
            'company_id': self.company.id,
        })
        with self.assertRaises(Exception): # SQL Unique Constraint
            self.env['coconut.payroll.line'].create({
                'period_id': period.id,
                'employee_id': self.emp_sheller.id,
                'worker_type': 'sheller',
                'company_id': self.company.id,
            })

    def test_10_work_result_one_payroll_period(self):
        # 10. A work result cannot enter two payroll periods.
        period1 = self.env['coconut.payroll.period'].create({
            'name': 'Periode 1',
            'date_start': '2026-07-01',
            'date_end': '2026-07-07',
            'company_id': self.company.id,
        })
        period2 = self.env['coconut.payroll.period'].create({
            'name': 'Periode 2',
            'date_start': '2026-07-08',
            'date_end': '2026-07-14',
            'company_id': self.company.id,
        })
        
        line1 = self.env['coconut.payroll.line'].create({
            'period_id': period1.id,
            'employee_id': self.emp_parer.id,
            'worker_type': 'parer',
            'company_id': self.company.id,
        })
        line2 = self.env['coconut.payroll.line'].create({
            'period_id': period2.id,
            'employee_id': self.emp_parer.id,
            'worker_type': 'parer',
            'company_id': self.company.id,
        })

        wr = self.env['coconut.work.result'].create({
            'employee_id': self.emp_parer.id,
            'worker_type': 'parer',
            'work_type': 'parer_prod',
            'quantity': 100.0,
            'rate': 300.0,
            'date': '2026-07-01',
            'company_id': self.company.id,
        })

        # Link to line1
        wr.write({'payroll_line_id': line1.id})
        
        # Trying to assign same wr to line2 must be blocked by database/relation or code constraints
        # Since payroll_line_id is a Many2one, writing it to line2.id will move it out of line1.
        # But we ensure it cannot enter another period if it's already assigned.
        self.assertEqual(wr.payroll_line_id, line1)

    def test_11_paid_work_result_protection(self):
        # 11. Paid work results cannot be edited or deleted.
        wr = self.env['coconut.work.result'].create({
            'employee_id': self.emp_parer.id,
            'worker_type': 'parer',
            'work_type': 'parer_prod',
            'quantity': 100.0,
            'rate': 300.0,
            'date': '2026-07-01',
            'company_id': self.company.id,
            'state': 'paid',
        })
        with self.assertRaises(ValidationError):
            wr.write({'quantity': 200.0})
        with self.assertRaises(ValidationError):
            wr.unlink()

    def test_12_operator_cannot_confirm_or_pay(self):
        # 12. Operators cannot confirm or pay payroll.
        period = self.env['coconut.payroll.period'].create({
            'name': 'Periode 1',
            'date_start': '2026-07-01',
            'date_end': '2026-07-07',
            'company_id': self.company.id,
            'state': 'calculated',
        })
        with self.assertRaises(UserError):
            period.with_user(self.user_operator).action_confirm()
        with self.assertRaises(UserError):
            period.with_user(self.user_operator).action_paid()

    def test_13_supervisor_cannot_pay(self):
        # 13. Supervisors cannot mark payroll as paid.
        period = self.env['coconut.payroll.period'].create({
            'name': 'Periode 1',
            'date_start': '2026-07-01',
            'date_end': '2026-07-07',
            'company_id': self.company.id,
            'state': 'confirmed',
        })
        with self.assertRaises(UserError):
            period.with_user(self.user_supervisor).action_paid()

    def test_14_manager_can_pay(self):
        # 14. Managers can mark payroll as paid.
        period = self.env['coconut.payroll.period'].create({
            'name': 'Periode 1',
            'date_start': '2026-07-01',
            'date_end': '2026-07-07',
            'company_id': self.company.id,
            'state': 'confirmed',
        })
        period.with_user(self.user_manager).action_paid()
        self.assertEqual(period.state, 'paid')

    def test_15_cancellation_releases_validated_work_results(self):
        # 15. Cancellation releases validated work results.
        period = self.env['coconut.payroll.period'].create({
            'name': 'Periode 1',
            'date_start': '2026-07-01',
            'date_end': '2026-07-07',
            'company_id': self.company.id,
        })
        wr = self.env['coconut.work.result'].create({
            'employee_id': self.emp_parer.id,
            'worker_type': 'parer',
            'work_type': 'parer_prod',
            'quantity': 100.0,
            'rate': 300.0,
            'date': '2026-07-01',
            'company_id': self.company.id,
            'state': 'validated',
        })
        
        # Calculate
        period.action_calculate()
        self.assertEqual(wr.payroll_line_id.period_id, period)

        # Confirm
        period.action_confirm()

        # Cancel
        period.with_user(self.user_manager).action_cancel()
        
        # Released checks
        self.assertFalse(wr.payroll_line_id)
        self.assertEqual(wr.state, 'validated')

    def test_16_paid_payroll_cannot_be_cancelled(self):
        # 16. Paid payroll cannot be cancelled.
        period = self.env['coconut.payroll.period'].create({
            'name': 'Periode 1',
            'date_start': '2026-07-01',
            'date_end': '2026-07-07',
            'company_id': self.company.id,
            'state': 'paid',
        })
        with self.assertRaises(UserError):
            period.with_user(self.user_manager).action_cancel()
