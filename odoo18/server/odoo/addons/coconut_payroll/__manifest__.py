# -*- coding: utf-8 -*-
{
    'name': 'Coconut Payroll',
    'version': '18.0.1.0.0',
    'summary': 'Sistem Penggajian Mingguan PT Coco Murni Prima Jaya',
    'description': """
        Modul kustom untuk mengelola penggajian mingguan pekerja Sheller dan Parer.
        Mendukung perhitungan berbasis hasil kerja, tambahan jam kerja, lembur, dan potongan.
    """,
    'author': 'PT Coco Murni Prima Jaya / Custom',
    'category': 'Human Resources/Payroll',
    'depends': ['base', 'hr'],
    'data': [
        'security/payroll_security.xml',
        'security/ir.model.access.csv',
        'data/payroll_sequence.xml',
        'data/payroll_tariff_data.xml',
        'data/salary_rule_data.xml',
        'data/premium_rule_data.xml',
        'views/res_config_settings_views.xml',
        'views/hr_employee_views.xml',
        'views/work_result_views.xml',
        'views/work_sheet_views.xml',
        'views/payroll_tariff_views.xml',
        'views/premium_rule_views.xml',
        'views/payroll_period_views.xml',
        'views/payroll_recap_views.xml',
        'views/employee_loan_views.xml',
        'views/salary_rule_views.xml',
        'views/payroll_line_report.xml',
        'views/payroll_menu.xml',
    ],
    'installable': True,
    'application': True,
    'license': 'LGPL-3',
}
