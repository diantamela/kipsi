# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.
{
    'name': 'Coconut Purchase Customization',
    'version': '1.0',
    'category': 'Purchases',
    'summary': 'Custom purchase module for PT Coco Murni Prima Jaya - Coconut supplier management',
    'description': '''
        Customisasi modul Purchase untuk PT Coco Murni Prima Jaya:
        - Data supplier kelapa dengan detail kontak (nama CV, kontak, HP, alamat)
        - Penerimaan kelapa dengan data pengiriman (sopir, HP sopir, kendaraan)
        - Data penerimaan (nomor, tanggal, jam, berat total)
        - Sortir kualitas (cungkil mesin & manual) dengan validasi otomatis
        - Catatan penerimaan dan pegawai RMP
        - Integrasi inventory (auto-create stock picking)
    ''',
    'author': 'PT Coco Murni Prima Jaya',
    'website': '',
    'depends': ['purchase', 'stock', 'product'],
    'data': [
        'security/ir.model.access.csv',
        'security/coconut_security.xml',
        'data/sequence_data.xml',
        'data/product_data.xml',
        'views/coconut_supplier_receipt_views.xml',
        'views/res_partner_views.xml',
        'views/menu_views.xml',
        'report/coconut_receipt_report.xml',
    ],
    'installable': True,
    'application': True,
    'auto_install': False,
    'license': 'LGPL-3',
}