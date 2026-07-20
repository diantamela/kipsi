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
            metrics: {
                receiving_qty: 12500,
                receiving_count: 3,
                production_qty: 8750,
                ready_stock_qty: 35200,
                active_employees: 125,
                inventory: {
                    bulat: 12500,
                    layak: 8700,
                    reject: 1200,
                    parer: 2500,
                },
                production_status: {
                    mo_active: 12,
                    mo_running: 7,
                    mo_finished_today: 15,
                    efficiency: 92,
                },
                payroll: {
                    total_employees: 150,
                    daily_wage: 125450000,
                    production_bonus: 18750000,
                    status: 'Sudah Dihitung',
                }
            }
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
            if (data.metrics) {
                this.state.metrics = data.metrics;
            }
        } catch (error) {
            console.error("Error loading dashboard data:", error);
        } finally {
            this.state.loading = false;
        }
    }

    formatNumber(num) {
        if (num === undefined || num === null) return '0';
        return num.toLocaleString('id-ID');
    }

    formatCurrency(num) {
        if (num === undefined || num === null) return 'Rp 0';
        return 'Rp ' + num.toLocaleString('id-ID');
    }

    openAction(actionXmlId) {
        if (!actionXmlId) return;
        this.actionService.doAction(actionXmlId);
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
