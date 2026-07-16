/** @odoo-module **/
import { registry } from "@web/core/registry";
import { Component, xml } from "@odoo/owl";

class CocoDashboard extends Component {
    static template = xml`<div class="o_action">Coco Dashboard Stub</div>`;
}

registry.category("actions").add("pt_coco_dashboard_action", CocoDashboard);
