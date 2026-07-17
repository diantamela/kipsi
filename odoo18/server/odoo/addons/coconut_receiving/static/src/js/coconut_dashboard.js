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

    openProductStock(productCode) {
        if (!productCode) return;
        this.actionService.doAction("coconut_receiving.action_coconut_daily_stock", {
            additionalContext: {
                selected_product_code: productCode,
            },
        });
    }
}

CoconutDashboard.template = "coconut_receiving.CoconutDashboard";

registry.category("actions").add("pt_coconut_dashboard_action", CoconutDashboard);
