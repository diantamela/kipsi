# -*- coding: utf-8 -*-
{
    'name': 'Penerimaan & Manufaktur Kelapa',
    'version': '18.0.4.0.0',
    'summary': 'Mengelola proses penerimaan, sortir, dan manufaktur kelapa terpadu',
    'description': """
        Modul kustom terpadu untuk PT Coco Murni Prima Jaya.

        Penerimaan Kelapa:
        - Pencatatan data timbangan (bruto, tara, pot → berat bersih)
        - Penilaian kualitas dan penambahan stok Kelapa Bulat
        
        Manufaktur Kelapa:
        - Sortir Kelapa  : Kelapa Bulat → Kelapa Layak + Kelapa Reject
        - Machine Sheller: Kelapa Layak → Kelapa Sheller
        - Manual Sheller : Kelapa Reject → Kelapa Sheller
        - Parer          : Kelapa Sheller → Kelapa Parer

        Laporan Stok Kelapa Harian terintegrasi.
    """,
    'author': 'PT Coco Murni Prima Jaya / Custom',
    'category': 'Manufacturing',
    'depends': ['base', 'stock', 'hr', 'mail', 'uom', 'purchase', 'product'],
    'data': [
        'security/ir.model.access.csv',
        'data/sequence.xml',
        'data/product_data.xml',
        'data/location_data.xml',
        'views/coconut_receipt_views.xml',
        'views/coconut_manufacturing_report.xml',
        'views/coconut_stock_report_views.xml',
        'views/coconut_sorting_views.xml',
        'views/coconut_manufacturing_views.xml',
        'views/custom_views.xml',
    ],
    'installable': True,
    'application': True,
    'license': 'LGPL-3',
    'tests': [
        'tests/test_coconut_receiving.py',
        'tests/test_coconut_manufacturing.py',
    ],
}
