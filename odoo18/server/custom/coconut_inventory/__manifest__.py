{
    "name": "Coconut Inventory Management",
    "version": "18.0.1.0.0",
    "category": "Inventory",
    "summary": "Coconut Factory ERP - Inventory & Batch Tracking",
    "description": """
        Inventory management for coconut processing
        - Batch/lot tracking for coconuts
        - Real-time stock monitoring
        - Automatic stock updates
        - Stock alerts and notifications
    """,
    "author": "Your Company",
    "depends": ["coconut_base", "stock"],
    "data": [
        "security/ir.model.access.csv",
        "views/coconut_batch_views.xml",
        "views/stock_quant_views.xml",
        "views/stock_move_views.xml",
        "views/stock_picking_views.xml",
        "data/coconut_batch_sequence.xml",
        "reports/coconut_batch_report.xml",
        "reports/coconut_stock_report.xml",
    ],
    "installable": True,
    "application": True,
    "auto_install": False,
    "license": "LGPL-3",
}
