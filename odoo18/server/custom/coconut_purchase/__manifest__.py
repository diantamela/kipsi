{
    "name": "Coconut Purchasing",
    "version": "18.0.1.0.0",
    "category": "Purchases",
    "summary": "Coconut Factory ERP - Purchase & Supplier Management",
    "description": """
        Purchase management for coconut raw materials
        - Supplier registration and evaluation
        - Purchase requisitions and approvals
        - Purchase order management
        - Quality inspection on receipt
        - Purchase status monitoring and reporting
    """,
    "author": "Your Company",
    "depends": ["coconut_base", "coconut_supplier", "purchase", "stock"],
    "data": [
        "security/ir.model.access.csv",
        "views/purchase_order_views.xml",
        "views/purchase_requisition_views.xml",
        "views/res_partner_views.xml",
        "views/coconut_purchase_templates.xml",
        "data/purchase_sequence.xml",
    ],
    "installable": True,
    "application": True,
    "auto_install": False,
    "license": "LGPL-3",
}
