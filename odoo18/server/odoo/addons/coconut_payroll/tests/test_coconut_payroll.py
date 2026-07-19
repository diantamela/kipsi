# -*- coding: utf-8 -*-
from odoo.tests.common import TransactionCase
from odoo.exceptions import ValidationError, UserError
from odoo import fields

class TestCoconutPayroll(TransactionCase):

    def setUp(self):
        super(TestCoconutPayroll, self).setUp()
        self.company = self.env.ref('base.main_company')

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

        # Create departments
        self.dep_sheller = self.env['hr.department'].create({'name': 'MP / Sheller Manual'})
        self.dep_parer = self.env['hr.department'].create({'name': 'MP / Parer'})

        # Create employees
        self.emp_sheller = self.env['hr.employee'].create({
            'name': 'Budi Sheller',
            'department_id': self.dep_sheller.id,
            'employee_code': 'EMP001',
            'payroll_active': True,
        })
        self.emp_parer = self.env['hr.employee'].create({
            'name': 'Siti Parer',
            'department_id': self.dep_parer.id,
            'employee_code': 'EMP002',
            'payroll_active': True,
        })

        # Clear existing rules for testing to avoid conflicts
        self.env['coconut.salary.rule'].search([]).unlink()
        self.env['coconut.premium.rule'].search([]).unlink()

        # Create Salary Rules for Sheller
        self.rule_sheller_biasa_low = self.env['coconut.salary.rule'].create({
            'worker_type': 'sheller_manual',
            'day_type': 'biasa',
            'min_quantity': 0.0,
            'max_quantity': 424.99,
            'wage_rate': 180.0,
            'start_date': '2026-01-01',
            'end_date': '2026-12-31',
            'company_id': self.company.id,
        })
        self.rule_sheller_biasa_high = self.env['coconut.salary.rule'].create({
            'worker_type': 'sheller_manual',
            'day_type': 'biasa',
            'min_quantity': 425.0,
            'max_quantity': 999999.0,
            'wage_rate': 225.0,
            'start_date': '2026-01-01',
            'end_date': '2026-12-31',
            'company_id': self.company.id,
        })
        self.rule_sheller_merah_low = self.env['coconut.salary.rule'].create({
            'worker_type': 'sheller_manual',
            'day_type': 'merah',
            'min_quantity': 0.0,
            'max_quantity': 424.99,
            'wage_rate': 230.0,
            'start_date': '2026-01-01',
            'end_date': '2026-12-31',
            'company_id': self.company.id,
        })
        self.rule_sheller_merah_high = self.env['coconut.salary.rule'].create({
            'worker_type': 'sheller_manual',
            'day_type': 'merah',
            'min_quantity': 425.0,
            'max_quantity': 999999.0,
            'wage_rate': 275.0,
            'start_date': '2026-01-01',
            'end_date': '2026-12-31',
            'company_id': self.company.id,
        })

        # Create Salary Rules for Parer
        self.rule_parer_biasa = self.env['coconut.salary.rule'].create({
            'worker_type': 'parer',
            'day_type': 'biasa',
            'min_quantity': 0.0,
            'max_quantity': 999999.0,
            'wage_rate': 340.0,
            'start_date': '2026-01-01',
            'end_date': '2026-12-31',
            'company_id': self.company.id,
        })
        self.rule_parer_merah = self.env['coconut.salary.rule'].create({
            'worker_type': 'parer',
            'day_type': 'merah',
            'min_quantity': 0.0,
            'max_quantity': 999999.0,
            'wage_rate': 390.0,
            'start_date': '2026-01-01',
            'end_date': '2026-12-31',
            'company_id': self.company.id,
        })

        # Create Premium Rules
        self.premium_sheller_biasa_500 = self.env['coconut.premium.rule'].create({
            'worker_type': 'sheller_manual',
            'day_type': 'biasa',
            'min_quantity': 500.0,
            'max_quantity': 599.99,
            'premium_amount': 25000.0,
            'start_date': '2026-01-01',
            'end_date': '2026-12-31',
            'company_id': self.company.id,
        })
        self.premium_parer_biasa_250 = self.env['coconut.premium.rule'].create({
            'worker_type': 'parer',
            'day_type': 'biasa',
            'min_quantity': 250.0,
            'max_quantity': 299.99,
            'premium_amount': 20000.0,
            'start_date': '2026-01-01',
            'end_date': '2026-12-31',
            'company_id': self.company.id,
        })

    def test_01_sheller_biasa_wage_calculation(self):
        # 1. Sheller normal day calculation (< 425 kg vs >= 425 kg)
        sheet = self.env['coconut.work.sheet'].create({
            'date': '2026-07-01',
            'worker_type': 'sheller_manual',
            'day_type': 'biasa',
            'total_production_qty': 900.0,
            'company_id': self.company.id,
        })

        # Low qty worker (Budi = 400kg, rate = 180, basic = 72000)
        # High qty worker (Siti, wait, Siti is parer, we need another employee)
        emp_sheller2 = self.env['hr.employee'].create({
            'name': 'Andi Sheller',
            'department_id': self.dep_sheller.id,
            'employee_code': 'EMP003',
        })

        res1 = self.env['coconut.work.result'].create({
            'work_sheet_id': sheet.id,
            'employee_id': self.emp_sheller.id,
            'quantity_kg': 400.0,
        })
        res2 = self.env['coconut.work.result'].create({
            'work_sheet_id': sheet.id,
            'employee_id': emp_sheller2.id,
            'quantity_kg': 500.0,
        })

        sheet.action_validate()

        self.assertEqual(res1.wage_rate, 180.0)
        self.assertEqual(res1.basic_wage, 72000.0)
        self.assertEqual(res1.premium, 0.0)

        # High qty: 500kg >= 425kg -> rate = 225, basic = 112500, premium = 25000
        self.assertEqual(res2.wage_rate, 225.0)
        self.assertEqual(res2.basic_wage, 112500.0)
        self.assertEqual(res2.premium, 25000.0)
        self.assertEqual(res2.total_wage, 137500.0)

    def test_02_production_validation_mismatch(self):
        # 2. Production quantity validation (ValidationError when empty or total is <= 0)
        sheet = self.env['coconut.work.sheet'].create({
            'date': '2026-07-01',
            'worker_type': 'sheller_manual',
            'day_type': 'biasa',
            'company_id': self.company.id,
        })
        with self.assertRaises(ValidationError):
            sheet.action_validate()

    def test_03_loan_deductions_in_recap(self):
        # 3. Employee loan creation and automated deduction calculation in recap
        loan = self.env['coconut.employee.loan'].create({
            'employee_id': self.emp_sheller.id,
            'loan_amount': 100000.0,
            'installment_amount': 30000.0,
            'company_id': self.company.id,
        })
        loan.action_active()

        sheet = self.env['coconut.work.sheet'].create({
            'date': '2026-07-01',
            'worker_type': 'sheller_manual',
            'day_type': 'biasa',
            'total_production_qty': 500.0,
            'company_id': self.company.id,
        })
        res = self.env['coconut.work.result'].create({
            'work_sheet_id': sheet.id,
            'employee_id': self.emp_sheller.id,
            'quantity_kg': 500.0,
        })
        sheet.action_validate()

        recap = self.env['coconut.payroll.recap'].create({
            'date_start': '2026-07-01',
            'date_end': '2026-07-07',
            'worker_type': 'sheller_manual',
            'company_id': self.company.id,
        })
        recap.action_generate()

        line = recap.line_ids.filtered(lambda l: l.employee_id == self.emp_sheller)
        self.assertTrue(line)
        self.assertEqual(line.loan_deduction, 30000.0)
        self.assertEqual(line.net_salary, line.gross_salary - 30000.0)

        # Approve and pay recap
        recap.action_approve()
        recap.action_paid()

        # Sisa loan should be updated: 100k - 30k = 70k
        self.assertEqual(loan.remaining_amount, 70000.0)
        self.assertEqual(len(loan.installment_line_ids), 1)
        self.assertEqual(loan.installment_line_ids[0].amount, 30000.0)
        self.assertEqual(loan.installment_line_ids[0].state, 'posted')

    def test_04_rule_overlap_validation(self):
        # 4. Try to create overlapping salary rule (should fail)
        with self.assertRaises(ValidationError):
            self.env['coconut.salary.rule'].create({
                'worker_type': 'sheller_manual',
                'day_type': 'biasa',
                'min_quantity': 100.0,
                'max_quantity': 200.0,
                'wage_rate': 200.0,
                'start_date': '2026-06-01',
                'end_date': '2026-07-15',
                'company_id': self.company.id,
            })

    def test_05_onchange_worker_type(self):
        # 5. Test auto-population of work results when worker_type is selected
        sheet = self.env['coconut.work.sheet'].new({
            'date': '2026-07-01',
            'worker_type': 'sheller_manual',
            'company_id': self.company.id,
        })
        sheet._onchange_worker_type()
        
        # Budi Sheller has sheller_manual worker type, Siti Parer has parer.
        # Only Budi Sheller should be populated.
        employees_populated = [res.employee_id for res in sheet.work_result_ids]
        self.assertIn(self.emp_sheller, employees_populated)
        self.assertNotIn(self.emp_parer, employees_populated)
