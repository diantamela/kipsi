from odoo import models, fields, api, _
from odoo.tools import html_escape
from odoo.addons.mail.models.mail_template import format_date


class CoconutNotificationSettings(models.Model):
    """Notification settings"""
    _name = 'coconut.notification.settings'
    _description = 'Coconut Notification Configuration'

    name = fields.Char(string='Name', required=True, default='Factory Alerts')
    company_id = fields.Many2one('res.company', string='Company', 
                                default=lambda self: self.env.company)
    
    # Stock alert settings
    enable_low_stock_alerts = fields.Boolean(string='Enable Low Stock Alerts', default=True)
    low_stock_threshold_days = fields.Integer(string='Alert Days Before Stockout', default=3)
    notify_stock_manager = fields.Boolean(string='Notify Stock Manager', default=True)
    notify_purchase_manager = fields.Boolean(string='Notify Purchase Manager', default=True)
    
    # Production alerts
    enable_production_delay_alerts = fields.Boolean(string='Production Delay Alerts', default=True)
    notify_production_manager = fields.Boolean(string='Notify Production Manager', default=True)
    
    # Quality alerts
    enable_quality_alerts = fields.Boolean(string='Quality Rejection Alerts', default=True)
    rejection_threshold_percent = fields.Float(string='Alert on Rejection Rate > %', default=10.0)
    
    # Email settings
    email_from = fields.Char(string='From Email', 
                            default=lambda self: self.env.company.email or 'noreply@factory.com')
    notification_recipients = fields.Many2many('res.users', string='Additional Recipients')
    
    # Schedule
    notification_frequency = fields.Selection([
        ('immediate', 'Immediate'),
        ('hourly', 'Hourly Summary'),
        ('daily', 'Daily Summary'),
        ('weekly', 'Weekly Summary'),
    ], string='Notification Frequency', default='immediate')


class CoconutNotificationQueue(models.Model):
    """Queue for notification sending"""
    _name = 'coconut.notification.queue'
    _description = 'Coconut Notification Queue'
    _order = 'create_date desc'

    name = fields.Char(string='Notification Reference', readonly=True)
    notification_type = fields.Selection([
        ('low_stock', 'Low Stock Alert'),
        ('over_stock', 'Over Stock Alert'),
        ('production_delay', 'Production Delay'),
        ('quality_issue', 'Quality Issue'),
        ('supplier_performance', 'Supplier Performance'),
        ('daily_summary', 'Daily Summary'),
        ('weekly_summary', 'Weekly Summary'),
    ], string='Type', required=True)
    
    message = fields.Html(string='Message', required=True)
    recipients = fields.Many2many('res.users', string='Recipients')
    sent = fields.Boolean(string='Sent', default=False)
    sent_date = fields.Datetime(string='Sent Date')
    error_message = fields.Text(string='Error Message')
    
    priority = fields.Selection([
        ('low', 'Low'),
        ('normal', 'Normal'),
        ('high', 'High'),
        ('urgent', 'Urgent'),
    ], string='Priority', default='normal')
    
    related_model = fields.Char(string='Related Model')
    related_id = fields.Integer(string='Related Record ID')
    
    @api.model_create_multi
    def create(self, vals_list):
        for vals in vals_list:
            if vals.get('name', _('New')) == _('New'):
                vals['name'] = self.env['ir.sequence'].next_by_code('coconut.notification') or _('New')
        return super().create(vals_list)
    
    def send(self):
        """Send notification emails"""
        for notification in self:
            try:
                template = self._get_email_template()
                if template:
                    template.sudo().send_mail(notification.id, force_send=True)
                notification.write({
                    'sent': True,
                    'sent_date': fields.Datetime.now()
                })
            except Exception as e:
                notification.write({
                    'error_message': str(e)
                })
    
    def _get_email_template(self):
        """Get appropriate email template"""
        template_map = {
            'low_stock': 'coconut_notification.email_template_low_stock',
            'production_delay': 'coconut_notification.email_template_production_delay',
            'quality_issue': 'coconut_notification.email_template_quality_issue',
        }
        template_ref = template_map.get(self.notification_type)
        if template_ref:
            return self.env.ref(template_ref, raise_if_not_found=False)
        return None


class CoconutStockAlertMonitor(models.Model):
    """Monitor stock levels and trigger alerts"""
    _name = 'coconut.stock.monitor'
    _description = 'Coconut Stock Level Monitor'

    @api.model
    def check_all_stock_levels(self):
        """Cron job to check stock levels"""
        StockQuant = self.env['stock.quant']
        CoconutProduct = self.env['coconut.product']
        
        # Get all coconut products
        coconut_products = CoconutProduct.search([])
        
        alerts_to_send = []
        
        for product in coconut_products:
            total_qty = sum(StockQuant.search([
                ('product_id', '=', product.id),
                ('location_id.usage', '=', 'internal')
            ]).mapped('quantity'))
            
            # Check minimum stock
            if total_qty <= product.coconut_minimum_stock:
                alert = self._create_low_stock_alert(product, total_qty)
                alerts_to_send.append(alert)
            
            # Check max stock (overstock)
            if product.coconut_maximum_stock and total_qty >= product.coconut_maximum_stock:
                alert = self._create_overstock_alert(product, total_qty)
                alerts_to_send.append(alert)
        
        # Send notifications
        if alerts_to_send:
            self._send_batch_alerts(alerts_to_send)
    
    def _create_low_stock_alert(self, product, current_qty):
        """Create low stock alert record"""
        # Find existing alert
        existing = self.env['coconut.stock.alert'].search([
            ('product_id', '=', product.id),
            ('alert_type', '=', 'low'),
            ('is_active', '=', True)
        ], limit=1)
        
        if existing:
            existing.write({'current_stock': current_qty})
            return existing
        
        # Create new alert
        alert = self.env['coconut.stock.alert'].create({
            'product_id': product.id,
            'location_id': product.coconut_default_location_id.id if product.coconut_default_location_id else None,
            'minimum_stock': product.coconut_minimum_stock,
            'maximum_stock': product.coconut_maximum_stock or (current_qty * 2),
        })
        return alert
    
    def _create_overstock_alert(self, product, current_qty):
        """Create overstock alert"""
        return self.env['coconut.stock.alert'].create({
            'product_id': product.id,
            'location_id': product.coconut_default_location_id.id if product.coconut_default_location_id else None,
            'minimum_stock': product.coconut_minimum_stock,
            'maximum_stock': product.coconut_maximum_stock,
        })
    
    def _send_batch_alerts(self, alerts):
        """Send batch notification for all alerts"""
        if not alerts:
            return
        
        # Group alerts by type
        low_stock_alerts = [a for a in alerts if a.alert_type == 'low']
        
        if low_stock_alerts:
            self._send_stock_alert_email(low_stock_alerts, 'low')
    
    def _send_stock_alert_email(self, alerts, alert_type):
        """Send stock alert email to configured recipients"""
        settings = self.env['coconut.notification.settings'].search([], limit=1)
        if not settings or not settings.enable_low_stock_alerts:
            return
        
        # Prepare email content
        company = self.env.company
        subject = f"Coconut Factory - Low Stock Alert - {fields.Date.today()}"
        
        body = f"""
        <h3>Low Stock Alert - {company.name}</h3>
        <p>The following coconut products are below minimum stock levels:</p>
        <table border="1" cellpadding="5">
            <tr>
                <th>Product</th>
                <th>Current Stock (kg)</th>
                <th>Minimum Stock (kg)</th>
                <th>Location</th>
            </tr>
        """
        
        for alert in alerts:
            body += f"""
            <tr>
                <td>{alert.product_id.name}</td>
                <td>{alert.current_stock:.2f}</td>
                <td>{alert.minimum_stock:.2f}</td>
                <td>{alert.location_id.name or 'N/A'}</td>
            </tr>
            """
        
        body += "</table>"
        body += "<p>Please review and create purchase requisitions as needed.</p>"
        
        # Create notification queue
        notification = self.env['coconut.notification.queue'].create({
            'notification_type': 'low_stock',
            'message': body,
            'priority': 'high',
        })
        
        # Add recipients
        if settings.notify_stock_manager:
            stock_managers = self.env.ref('stock.group_stock_manager').users
            notification.write({'recipients': [(6, 0, stock_managers.ids)]})
        
        if settings.notify_purchase_manager:
            purchase_managers = self.env.ref('purchase.group_purchase_manager').users
            notification.write({'recipients': [(6, 0, purchase_managers.ids)]})
        
        # Send
        notification.send()
