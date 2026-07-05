{
    'name': 'Sortir Kelapa',
    'version': '1.0',
    'summary': 'Modul untuk mensortir kelapa setelah penerimaan',
    'description': 'Modul untuk mensortir kelapa berdasarkan Laporan Hasil Sortiran Kelapa.',
    'author': 'PT Coco Murni Prima Jaya',
    'category': 'Manufacturing',
    'depends': ['base', 'stock', 'product', 'coconut_receiving'],
    'data': [
        'security/ir.model.access.csv',
        'data/sequence.xml',
        'views/coconut_sorting_views.xml',
    ],
    'installable': True,
    'application': True,
    'license': 'LGPL-3',
}
