{
    'name': 'Manufaktur Kelapa',
    'version': '18.0.3.1.0',
    'summary': 'Sortir Kelapa mandiri + Sheller + Parer (Pemakaian Kelapa Produksi)',
    'description': """
        Modul Manufaktur Kelapa untuk PT Coco Murni Prima Jaya.

        Proses yang tercakup dalam satu dokumen:
          1. Sortir Kelapa  : Kelapa Bulat → Kelapa Layak + Kelapa Reject
          2. Machine Sheller: Kelapa Layak → Kelapa Sheller
          3. Manual Sheller : Kelapa Reject → Kelapa Sheller
          4. Parer          : Kelapa Sheller → Kelapa Parer

        Laporan: Stok Kelapa Harian (Kelapa Bulat + Layak + Reject)

        Menyimpan data sortir lama (coconut.sorting) sebagai arsip read-only.
    """,
    'author': 'PT Coco Murni Prima Jaya',
    'category': 'Manufacturing',
    'depends': ['base', 'stock', 'product', 'mail', 'hr', 'uom', 'coconut_receiving'],
    'data': [
        'security/ir.model.access.csv',
        'data/sequence.xml',
        'data/location_data.xml',
        'views/coconut_manufacturing_report.xml',
        'views/coconut_stock_report_views.xml',
        'views/coconut_manufacturing_views.xml',
        'views/coconut_sorting_views.xml',
    ],
    'installable': True,
    'application': True,
    'license': 'LGPL-3',
    'tests': [
        'tests/test_coconut_manufacturing.py',
    ],
}
