{
    "name": "Coconut Production Management",
    "version": "18.0.1.0.0",
    "category": "Manufacturing",
    "summary": "Coconut Factory ERP - Production & BoM",
    "description": """
        Production management for coconut processing
        - Bill of Materials (BoM) for coconut products
        - Production planning and scheduling
        - Work orders and job tracking
        - Material consumption tracking
        - Production yield and efficiency
    """,
    "author": "Your Company",
    "depends": ["coconut_base", "coconut_inventory", "mrp"],
    "data": [
        "security/ir.model.access.csv",
        "views/mrp_bom_views.xml",
        "views/mrp_production_views.xml",
        "views/mrp_workorder_views.xml",
        "views/coconut_production_views.xml",
        "data/coconut_bom_templates.xml",
        "reports/production_order_report.xml",
        "reports/production_efficiency_report.xml",
    ],
    "installable": True,
    "application": True,
    "auto_install": False,
    "license": "LGPL-3",
}
