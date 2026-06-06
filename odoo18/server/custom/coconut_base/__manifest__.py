{
    "name": "Coconut Factory Base",
    "version": "18.0.1.0.0",
    "category": "Manufacturing",
    "summary": "Coconut Factory ERP - Base Module",
    "description": """
        Base module for Coconut Processing Factory ERP
        - Coconut product definitions
        - Product categories
        - Base models for tracking
    """,
    "author": "Your Company",
    "depends": ["product", "stock", "mrp"],
    "data": [
        "views/product_template_views.xml",
        "views/coconut_product_views.xml",
        "security/ir.model.access.csv",
        "data/coconut_product_data.xml",
    ],
    "installable": True,
    "application": True,
    "auto_install": False,
    "license": "LGPL-3",
}
