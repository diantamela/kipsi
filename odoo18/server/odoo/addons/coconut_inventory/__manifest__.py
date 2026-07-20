{
    'name': 'Coconut Inventory',
    'version': '1.0',
    'category': 'Inventory',
    'summary': 'Custom Inventory Kanban for PT Coco Murni Prima Jaya',
    'description': 'Redesain Kanban Produk menjadi Product Inventory Card sesuai kategori manufaktur.',
    'depends': ['stock', 'mrp'],
    'data': [
        'views/product_kanban_view.xml',
    ],
    'assets': {
        'web.assets_backend': [
            'coconut_inventory/static/src/scss/inventory_card.scss',
        ],
    },
    'installable': True,
    'application': True,
}
