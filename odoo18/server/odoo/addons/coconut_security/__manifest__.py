# -*- coding: utf-8 -*-
{
    'name': 'Coconut Security & Access Control',
    'version': '18.0.1.0.0',
    'category': 'Administration/Security',
    'summary': 'Role Based Access Control (RBAC) PT Coco Murni Prima Jaya',
    'description': """
        Mengelola hak akses, peranan (roles), dan visibilitas menu sesuai dengan kebutuhan:
        1. Administrator
        2. Pegawai RMP
        3. Kepala Divisi Produksi
        4. Manager (Read-Only)
    """,
    'author': 'PT Coco Murni Prima Jaya / Custom',
    'depends': [
        'base',
        'purchase',
        'stock',
        'mrp',
        'hr',
        'hr_attendance',
        'coconut_receiving',
        'coconut_payroll'
    ],
    'data': [
        'security/security.xml',
        'data/res_users_data.xml',
        'security/ir.model.access.csv',
        'views/menu_views.xml',
    ],
    'installable': True,
    'application': False,
    'auto_install': False,
    'license': 'LGPL-3',
}
