{
    "name": "Coconut Notifications & Alerts",
    "version": "18.0.1.0.0",
    "category": "Tools",
    "summary": "Coconut Factory ERP - Stock Alerts & Notifications",
    "description": """
        Notification system for coconut factory
        - Low stock alerts (minimum threshold)
        - Bahan baku hampir habis warnings
        - Production schedule reminders
        - Purchase order status alerts
        - Daily/weekly summary emails
        - In-app notifications
    """,
    "author": "Your Company",
    "depends": [
        "coconut_base", "coconut_inventory", "coconut_purchase",
        "coconut_production", "mail", "base"
    ],
    "data": [
        "security/ir.model.access.csv",
        "views/notification_template_views.xml",
        "views/res_config_settings_views.xml",
        "data/notification_data.xml",
        "data/cron_data.xml",
    ],
    "installable": True,
    "application": True,
    "auto_install": False,
    "license": "LGPL-3",
}
