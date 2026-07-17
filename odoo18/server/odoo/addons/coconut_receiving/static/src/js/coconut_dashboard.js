/** @odoo-module **/
import { registry } from "@web/core/registry";
import { Component, onWillStart, useState } from "@odoo/owl";
import { useService } from "@web/core/utils/hooks";

class CoconutDashboard extends Component {
    setup() {
        this.orm = useService("orm");
        this.actionService = useService("action");
        this.state = useState({
            products: [],
            isManager: false,
            loading: true,
        });

        onWillStart(async () => {
            await this.loadData();
        });
    }

    async loadData() {
        this.state.loading = true;
        try {
            const data = await this.orm.call(
                "finalisasi.kelapa.mp",
                "get_dashboard_data",
                []
            );
            this.state.products = data.products || [];
            this.state.isManager = data.is_manager || false;
        } catch (error) {
            console.error("Error loading dashboard data:", error);
        } finally {
            this.state.loading = false;
        }
    }

    openProductForm(productId) {
        if (!productId) return;
        this.actionService.doAction({
            type: "ir.actions.act_window",
            res_model: "product.template",
            res_id: productId,
            views: [[false, "form"]],
            target: "current",
        });
    }

    openAllProducts() {
        this.actionService.doAction("stock.product_template_action_product");
    }
}

CoconutDashboard.template = "coconut_receiving.CoconutDashboard";

registry.category("actions").add("pt_coconut_dashboard_action", CoconutDashboard);
