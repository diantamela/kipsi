# -*- coding: utf-8 -*-
from odoo.tests.common import TransactionCase
from odoo.exceptions import UserError, ValidationError
from odoo import fields


class TestCoconutManufacturing(TransactionCase):
    """
    Tests for coconut_receiving and coconut_payroll kustom PT Coco Murni Prima Jaya.
    """

    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.partner = cls.env['res.partner'].create({
            'name': 'Test Supplier Manufaktur',
            'supplier_rank': 1,
        })
        cls.company = cls.env.company
        cls.uom_kg = cls.env.ref('uom.product_uom_kgm')

        # Resolve products
        def _p(xml_id):
            tmpl = cls.env.ref(xml_id, raise_if_not_found=False)
            return tmpl.product_variant_ids[:1] if tmpl else None

        cls.p_bulat = _p('coconut_receiving.product_kelapa_bulat')
        cls.p_layak = _p('coconut_receiving.product_kelapa_layak')
        cls.p_reject = _p('coconut_receiving.product_kelapa_reject')
        cls.p_sheller = _p('coconut_receiving.product_kelapa_sheller')
        cls.p_parer = _p('coconut_receiving.product_kelapa_parer')

        # Warehouse location
        wh = cls.env['stock.warehouse'].search(
            [('company_id', '=', cls.company.id)], limit=1
        )
        cls.location_wh = wh.lot_stock_id if wh else False

    def _skip_if_no_products(self):
        if not all([self.p_bulat, self.p_layak, self.p_reject, self.p_sheller, self.p_parer]):
            self.skipTest("One or more required products not found. Install modules first.")
        if not self.location_wh:
            self.skipTest("Warehouse location not found.")

    def _get_qty(self, product, loc_xml=None):
        if loc_xml:
            loc = self.env.ref(loc_xml)
        else:
            loc_map = {
                'COCO-BULAT': 'coconut_receiving.location_gudang_kelapa_bulat',
                'COCO-LAYAK': 'coconut_receiving.location_stok_kelapa_layak',
                'COCO-REJECT': 'coconut_receiving.location_stok_kelapa_reject',
                'COCO-SHELLER': 'coconut_receiving.location_area_sheller',
                'COCO-PARER': 'coconut_receiving.location_area_parer',
            }
            loc_xml_id = loc_map.get(product.default_code)
            loc = self.env.ref(loc_xml_id, raise_if_not_found=False) if loc_xml_id else self.location_wh
        if not loc:
            loc = self.location_wh
        return self.env['stock.quant']._get_available_quantity(product, loc)

    def _adjust_stock(self, product, quantity, loc_xml=None):
        """Helper to set product stock in warehouse."""
        if loc_xml:
            loc = self.env.ref(loc_xml)
        else:
            loc_map = {
                'COCO-BULAT': 'coconut_receiving.location_gudang_kelapa_bulat',
                'COCO-LAYAK': 'coconut_receiving.location_stok_kelapa_layak',
                'COCO-REJECT': 'coconut_receiving.location_stok_kelapa_reject',
                'COCO-SHELLER': 'coconut_receiving.location_area_sheller',
                'COCO-PARER': 'coconut_receiving.location_area_parer',
            }
            loc_xml_id = loc_map.get(product.default_code)
            loc = self.env.ref(loc_xml_id, raise_if_not_found=False) if loc_xml_id else self.location_wh
        if not loc:
            loc = self.location_wh
        self.env['stock.quant'].with_context(inventory_mode=True).create({
            'product_id': product.id,
            'location_id': loc.id,
            'inventory_quantity': quantity,
        }).action_apply_inventory()

    def _create_mfg(self, **kwargs):
        """Create and confirm a transfer document."""
        mfg = self.env['coconut.manufacturing'].create({
            'company_id': self.company.id,
            **kwargs,
        })
        mfg.action_confirm()
        return mfg

    # ─────────────────────────────────────────────────────────────
    # TEST 1: Edit Done Blocker
    # ─────────────────────────────────────────────────────────────
    def test_01_edit_done_blocker(self):
        """
        Editing a completed transfer document must raise UserError.
        """
        self._skip_if_no_products()
        self._adjust_stock(self.p_layak, 100.0)
        mfg = self._create_mfg(
            sheller_mesin_qty=50.0,
        )
        mfg.action_validate()
        with self.assertRaises(UserError):
            mfg.write({'sheller_mesin_qty': 60.0})

    # ─────────────────────────────────────────────────────────────
    # TEST 2: Hasil Kerja Harian Validation and Stock Moves
    # ─────────────────────────────────────────────────────────────
    def test_02_hasil_kerja_harian_and_stock_moves(self):
        """
        Verify that:
        1. Operator inputs daily work result linked to transfer.
        2. Stock moves are generated upon validation.
        3. Cumulative validation prevents exceeding transfer quantities.
        """
        self._skip_if_no_products()
        
        # Adjust stocks
        self._adjust_stock(self.p_layak, 1000.0)
        self._adjust_stock(self.p_reject, 500.0)
        self._adjust_stock(self.p_sheller, 0.0, 'coconut_receiving.location_stok_hasil_sheller_mesin')
        
        # Create transfer
        mfg = self._create_mfg(
            sheller_mesin_qty=500.0,
            sheller_manual_qty=300.0,
        )
        mfg.action_validate()

        emp_vals = {'name': 'Test Worker'}
        if 'payroll_job_type' in self.env['hr.employee']._fields:
            emp_vals['payroll_job_type'] = 'sheller_mesin'
        employee = self.env['hr.employee'].create(emp_vals)

        # Input work results (sheller mesin)
        hkh = self.env['coconut.hasil.kerja.harian'].create({
            'transfer_id': mfg.id,
            'date': fields.Date.today(),
            'shift': 'shift_1',
            'operator_id': employee.id,
            'process_type': 'sheller_mesin',
            'qty_hasil': 400.0,
        })
        self.assertEqual(hkh.material_in_qty, 500.0)
        self.assertEqual(hkh.remaining_material, 100.0)

        # Validate HKH -> creates stock moves
        hkh.action_confirm()
        self.assertEqual(hkh.state, 'confirmed')

        # Check stock in destination location
        qty_mesin = self._get_qty(self.p_sheller, 'coconut_receiving.location_stok_hasil_sheller_mesin')
        self.assertEqual(qty_mesin, 400.0)

        mfg._compute_spk_stats()
        self.assertEqual(mfg.qty_hasil, 400.0)
        self.assertEqual(mfg.remaining_material, 400.0)
        self.assertEqual(mfg.status_produksi, 'progress')

        # Try to input second record that exceeds remaining (100.0 remaining, we try to put 101.0)
        hkh_exceed = self.env['coconut.hasil.kerja.harian'].create({
            'transfer_id': mfg.id,
            'date': fields.Date.today(),
            'shift': 'shift_2',
            'operator_id': employee.id,
            'process_type': 'sheller_mesin',
            'qty_hasil': 101.0,
        })
        with self.assertRaises(ValidationError):
            hkh_exceed.action_confirm()

    # ─────────────────────────────────────────────────────────────
    # TEST 3: Material Terbuang Stock Move and SPK updates
    # ─────────────────────────────────────────────────────────────
    def test_03_material_terbuang(self):
        """
        Verify that Material Terbuang successfully reduces area stock and updates SPK stats.
        """
        self._skip_if_no_products()
        self._adjust_stock(self.p_layak, 500.0)
        loc_area = self.env.ref('coconut_receiving.location_area_sheller_mesin')
        self._adjust_stock(self.p_layak, 100.0, 'coconut_receiving.location_area_sheller_mesin')

        mfg = self._create_mfg(
            sheller_mesin_qty=100.0,
        )
        mfg.action_validate()

        employee = self.env['hr.employee'].create({
            'name': 'Test Scrap Operator',
        })

        # Scrap 20 kg of COCO-LAYAK from Area Sheller Mesin
        scrap = self.env['coconut.material.terbuang'].create({
            'transfer_id': mfg.id,
            'product_id': self.p_layak.product_variant_id.id,
            'qty': 20.0,
            'operator_id': employee.id,
            'location_id': loc_area.id,
            'reason': 'rusak',
        })

        # Validate
        scrap.action_done()
        self.assertEqual(scrap.state, 'done')

        # Check stock reduced
        qty_left = self._get_qty(self.p_layak, 'coconut_receiving.location_area_sheller_mesin')
        self.assertEqual(qty_left, 180.0)

        # Check SPK computed values on the manufacturing document
        mfg._compute_spk_stats()
        self.assertEqual(mfg.material_wasted, 20.0)
        self.assertEqual(mfg.remaining_material, 80.0)

    # ─────────────────────────────────────────────────────────────
    # TEST 4: Payroll Worksheet Integration
    # ─────────────────────────────────────────────────────────────
    def test_04_payroll_worksheet_integration(self):
        """
        Verify that the Payroll Worksheet correctly computes its total_production_qty
        from the confirmed daily work results (HKH).
        """
        if 'coconut.work.sheet' not in self.env:
            self.skipTest("coconut_payroll module not loaded/installed.")
        self._skip_if_no_products()
        self._adjust_stock(self.p_layak, 500.0)
        mfg = self._create_mfg(
            sheller_mesin_qty=200.0,
        )
        mfg.action_validate()

        emp_vals = {'name': 'Sheller Worker'}
        if 'payroll_job_type' in self.env['hr.employee']._fields:
            emp_vals['payroll_job_type'] = 'sheller_mesin'
        employee = self.env['hr.employee'].create(emp_vals)

        # Confirm 150 kg of production in HKH
        hkh = self.env['coconut.hasil.kerja.harian'].create({
            'transfer_id': mfg.id,
            'operator_id': employee.id,
            'process_type': 'sheller_mesin',
            'qty_hasil': 150.0,
        })
        hkh.action_confirm()

        # Create payroll worksheet
        ws = self.env['coconut.work.sheet'].create({
            'date': fields.Date.today(),
            'worker_type': 'sheller_mesin',
            'day_type': 'biasa',
            'transfer_id': mfg.id,
        })
        ws.work_result_ids.unlink()

        # Distribute the 150 kg to the worker
        self.env['coconut.work.result'].create({
            'work_sheet_id': ws.id,
            'employee_id': employee.id,
            'quantity_kg': 150.0,
        })
        ws._compute_total_production_qty()
        self.assertEqual(ws.total_production_qty, 150.0)

        # Validate worksheet -> should succeed without creating duplicate stock moves
        ws.action_validate()
        self.assertEqual(ws.state, 'validated')
