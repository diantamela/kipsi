# -*- coding: utf-8 -*-
{
    'name': 'Coconut Receiving',
    'version': '18.0.1.0.0',
    'summary': 'Manage coconut raw material receiving process',
    'description': """
        Custom module for PT Coco Murni Prima Jaya to manage the receiving process
        of coconuts with shell. Includes weighing, sorting, quality inspection,
        and integration with Inventory, Purchase, and HR modules.
    """,
    'author': 'PT Coco Murni Prima Jaya / Custom',
    'category': 'Inventory/Purchase',
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
