{
    "name": "Coconut Supplier Management",
    "version": "18.0.1.0.0",
    "category": "Contacts",
    "summary": "Coconut Factory ERP - Supplier Management",
    "description": """
        Enhanced supplier management for coconut suppliers
        - Supplier registration with coconut-specific data
        - Supplier performance tracking (quality, delivery)
        - Transaction history and evaluation
        - Supplier rating system
        - Coconut source tracking (regional origin)
    """,
    "author": "Your Company",
    "depends": ["coconut_base", "contacts"],
    "data": [
        "security/ir.model.access.csv",
        "views/res_partner_views.xml",
        "views/supplier_performance_views.xml",
        "data/supplier_rating_data.xml",
    ],
    "installable": True,
    "application": True,
    "auto_install": False,
    "license": "LGPL-3",
}
