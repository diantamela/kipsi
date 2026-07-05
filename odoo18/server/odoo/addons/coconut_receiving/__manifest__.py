# -*- coding: utf-8 -*-
{
    'name': 'Penerimaan Kelapa',
    'version': '18.0.1.0.0',
    'summary': 'Mengelola proses penerimaan bahan baku kelapa',
    'description': """
        Modul kustom untuk PT Coco Murni Prima Jaya untuk mengelola proses penerimaan
        kelapa bulat. Mencakup penimbangan, penyortiran, pemeriksaan kualitas,
        dan integrasi dengan modul Persediaan, Pembelian, dan SDM.
    """,
    'author': 'PT Coco Murni Prima Jaya / Custom',
    'category': 'Inventaris/Pembelian',
    'depends': ['base', 'purchase', 'stock', 'mrp', 'hr'],
    'data': [
        'security/ir.model.access.csv',
        'data/sequence.xml',
        'data/product_data.xml',
        'views/coconut_receipt_views.xml',
    ],
    'installable': True,
    'application': True,
    'license': 'LGPL-3',
}
