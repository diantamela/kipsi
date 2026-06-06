{
    "name": "Coconut Dashboard & Reporting",
    "version": "18.0.1.0.0",
    "category": "Reporting",
    "summary": "Coconut Factory ERP - Dashboards & Reports",
    "description": """
        Comprehensive reporting and analytics for coconut factory
        - Stock level dashboards
        - Production metrics and KPIs
        - Purchase analytics
        - Supplier performance reports
        - Employee productivity statistics
        - Payroll cost analysis
    """,
    "author": "Your Company",
    "depends": [
        "coconut_base", "coconut_purchase", "coconut_inventory",
        "coconut_production", "coconut_supplier", "web"
    ],
    "data": [
        "security/ir.model.access.csv",
        "views/dashboard_views.xml",
        "views/report_views.xml",
        "views/coconut_report_templates.xml",
        "data/dashboard_templates.xml",
    ],
    "installable": True,
    "application": True,
    "auto_install": False,
    "license": "LGPL-3",
}
