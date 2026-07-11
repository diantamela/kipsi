{
    'name': 'Sortir Kelapa',
    'version': '18.0.2.0.0',
    'summary': 'Modul untuk mensortir kelapa setelah penerimaan',
    'description': """
        Modul untuk mensortir kelapa berdasarkan Laporan Hasil Sortiran Kelapa.

        Proses:
          Kelapa Bulat Belum Sortir
            → Kelapa Layak Produksi
            → Kelapa Reject
            → Susut Sortir (scrap)

        Modul ini meng-extend coconut.receipt untuk menampilkan ringkasan sortir.
    """,
    'author': 'PT Coco Murni Prima Jaya',
    'category': 'Manufacturing',
    'depends': ['base', 'stock', 'product', 'mail', 'coconut_receiving'],
    'data': [
        'security/ir.model.access.csv',
        'data/sequence.xml',
        'data/product_data.xml',
        'data/location_data.xml',
        'views/coconut_sorting_views.xml',
    ],
    'installable': True,
    'application': True,
    'license': 'LGPL-3',
}
