/** @odoo-module **/
import { registry } from "@web/core/registry";
import { Component, onWillStart, useState } from "@odoo/owl";
import { useService } from "@web/core/utils/hooks";

class CoconutDashboard extends Component {
    setup() {
        this.orm = useService("orm");
        this.actionService = useService("action");
        this.state = useState({
            loading: true,
            kpi: {
                kelapa_masuk_hari_ini: 0,
                total_stok_kelapa: 0,
                supplier_hari_ini: 0,
                purchase_order_pending: 0,
                transfer_pending: 0,
                receiving_pending: 0,
            },
            recent: {
                receipts: [],
                transfers: [],
                adjustments: [],
                pos: [],
            },
            coconut_products_stock: [],
            charts: {
                receiving_7_days: [],
                stock_movement_7_days: [],
                top_suppliers: [],
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
                "coconut.receipt",
                "get_rmp_dashboard_data",
                []
            );
            if (data) {
                if (data.kpi) this.state.kpi = data.kpi;
                if (data.recent) this.state.recent = data.recent;
                if (data.coconut_products_stock) this.state.coconut_products_stock = data.coconut_products_stock;
                if (data.charts) this.state.charts = data.charts;
            }
        } catch (error) {
            console.error("Error loading RMP dashboard data:", error);
        } finally {
            this.state.loading = false;
        }
    }

    formatNumber(num) {
        if (num === undefined || num === null) return '0';
        return Number(num).toLocaleString('id-ID');
    }

    formatCurrency(num) {
        if (num === undefined || num === null) return 'Rp 0';
        return 'Rp ' + Number(num).toLocaleString('id-ID');
    }

    openAction(actionXmlId) {
        if (!actionXmlId) return;
        this.actionService.doAction(actionXmlId);
    }

    // Quick Actions / Shortcuts for all 11 RMP Menus
    openDashboard() {
        this.loadData();
    }

    openReceipts() {
        this.actionService.doAction("coconut_receiving.action_coconut_receipt");
    }

    createReceipt() {
        this.actionService.doAction({
            type: 'ir.actions.act_window',
            name: 'Penerimaan Kelapa Baru',
            res_model: 'coconut.receipt',
            views: [[false, 'form']],
            target: 'current',
        });
    }

    openSorting() {
        this.actionService.doAction("coconut_receiving.action_coconut_sorting");
    }

    openManufacturing() {
        this.actionService.doAction("coconut_receiving.action_coconut_manufacturing");
    }

    openStockReport() {
        this.actionService.doAction("coconut_receiving.action_coconut_daily_stock");
    }

    openProducts() {
        this.actionService.doAction({
            type: 'ir.actions.act_window',
            name: 'Produk Kelapa',
            res_model: 'product.product',
            views: [[false, 'kanban'], [false, 'list'], [false, 'form']],
            target: 'current',
        });
    }

    openInternalTransfers() {
        this.actionService.doAction({
            type: 'ir.actions.act_window',
            name: 'Transfer Internal',
            res_model: 'stock.picking',
            domain: [['picking_type_id.code', '=', 'internal']],
            views: [[false, 'list'], [false, 'form']],
            target: 'current',
        });
    }

    openStockAdjustment() {
        this.actionService.doAction({
            type: 'ir.actions.act_window',
            name: 'Stock Adjustment',
            res_model: 'stock.quant',
            views: [[false, 'list']],
            target: 'current',
        });
    }

    openPurchaseOrders() {
        this.actionService.doAction({
            type: 'ir.actions.act_window',
            name: 'Purchase Orders',
            res_model: 'purchase.order',
            views: [[false, 'list'], [false, 'form']],
            target: 'current',
        });
    }

    openSuppliers() {
        this.actionService.doAction({
            type: 'ir.actions.act_window',
            name: 'Supplier',
            res_model: 'res.partner',
            domain: [['supplier_rank', '>', 0]],
            views: [[false, 'list'], [false, 'form']],
            target: 'current',
        });
    }

    openReports() {
        this.actionService.doAction("coconut_receiving.action_coconut_daily_stock");
    }

    // Row / Card Click Handlers
    openProductRecord(productId) {
        if (!productId) {
            this.openProducts();
            return;
        }
        this.actionService.doAction({
            type: 'ir.actions.act_window',
            res_model: 'product.product',
            res_id: productId,
            views: [[false, 'form']],
            target: 'current',
        });
    }

    openReceiptRecord(id) {
        if (!id) return;
        this.actionService.doAction({
            type: 'ir.actions.act_window',
            res_model: 'coconut.receipt',
            res_id: id,
            views: [[false, 'form']],
            target: 'current',
        });
    }

    openTransferRecord(id) {
        if (!id) return;
        this.actionService.doAction({
            type: 'ir.actions.act_window',
            res_model: 'stock.picking',
            res_id: id,
            views: [[false, 'form']],
            target: 'current',
        });
    }

    openPoRecord(id) {
        if (!id) return;
        this.actionService.doAction({
            type: 'ir.actions.act_window',
            res_model: 'purchase.order',
            res_id: id,
            views: [[false, 'form']],
            target: 'current',
        });
    }
}

CoconutDashboard.template = "coconut_receiving.CoconutDashboard";

registry.category("actions").add("pt_coconut_dashboard_action", CoconutDashboard);
