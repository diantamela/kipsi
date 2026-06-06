{
    "name": "Coconut Factory ERP Integration",
    "version": "18.0.1.0.0",
    "category": "Manufacturing",
    "summary": "Coconut Factory ERP - Main Integration Module",
    "description": """
        Main integration module for Coconut Processing Factory ERP
        This module depends on all other coconut modules and provides:
        - Auto-configuration of integrated workflows
        - Cross-module data synchronization
        - Unified menu structure
        - Factory-wide settings
    """,
    "author": "Your Company",
    "depends": [
        "coconut_base", "coconut_supplier", "coconut_purchase",
        "coconut_inventory", "coconut_production", "coconut_notification",
        "mrp", "purchase", "stock", "hr_payroll"
    ],
    "data": [
        "security/ir.model.access.csv",
        "views/coconut_factory_config_views.xml",
        "views/coconut_integration_menus.xml",
        "data/coconut_integration_data.xml",
    ],
    "installable": True,
    "application": True,
    "auto_install": False,
    "license": "LGPL-3",
}
