# -*- coding: utf-8 -*-
{
    'name': 'Penerimaan Kelapa',
    'version': '18.0.3.0.0',
    'summary': 'Mengelola proses penerimaan bahan baku kelapa – data timbangan, kualitas, dan stok',
    'description': """
        Modul kustom untuk PT Coco Murni Prima Jaya.

        Mengelola penerimaan kelapa bulat dari pemasok:
        - Pencatatan data timbangan (bruto, tara, pot → berat bersih diterima)
        - Penilaian kualitas (informasional)
        - Validasi → stok Kelapa Bulat bertambah sesuai berat bersih diterima
        - Lampiran: surat jalan, slip timbangan

        Alur: Supplier → Kelapa Bulat (stok gudang)
    """,
    'author': 'PT Coco Murni Prima Jaya / Custom',
    'category': 'Inventaris',
    'depends': ['base', 'stock', 'hr', 'mail', 'uom', 'purchase'],
    'data': [
        'security/ir.model.access.csv',
        'data/sequence.xml',
        'data/product_data.xml',
        'views/coconut_receipt_views.xml',
    ],
    'installable': True,
    'application': True,
    'license': 'LGPL-3',
    'tests': [
        'tests/test_coconut_receiving.py',
    ],
}
