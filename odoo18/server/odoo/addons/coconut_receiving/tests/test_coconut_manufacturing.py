# -*- coding: utf-8 -*-
from odoo.tests.common import TransactionCase
from odoo.exceptions import UserError, ValidationError


class TestCoconutManufacturing(TransactionCase):
    """
    Tests for coconut_sorting module (coconut.manufacturing model).

    TEST 2: Edit Done Blocker
    TEST 3: Partial machine consumption (remaining Layak preserved)
    TEST 4: Manual sheller consumption (remaining Reject preserved)
    TEST 5: Parer validation (exceeding stock blocked)
    TEST 6: Duplicate validation blocked (manufacturing)
    TEST 7: Invalid UoM blocked
    TEST 8: No Washing/Blanching/Drying in any active flow
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

    def _get_qty(self, product):
        loc_map = {
            'COCO-BULAT': 'coconut_receiving.location_gudang_kelapa_bulat',
            'COCO-LAYAK': 'coconut_receiving.location_stok_kelapa_layak',
            'COCO-REJECT': 'coconut_receiving.location_stok_kelapa_reject',
            'COCO-SHELLER': 'coconut_receiving.location_area_sheller',
            'COCO-PARER': 'coconut_receiving.location_area_parer',
        }
        loc_xml = loc_map.get(product.default_code)
        loc = self.env.ref(loc_xml, raise_if_not_found=False) if loc_xml else self.location_wh
        if not loc:
            loc = self.location_wh
        return self.env['stock.quant']._get_available_quantity(product, loc)

    def _adjust_stock(self, product, quantity):
        """Helper to set product stock in warehouse."""
        loc_map = {
            'COCO-BULAT': 'coconut_receiving.location_gudang_kelapa_bulat',
            'COCO-LAYAK': 'coconut_receiving.location_stok_kelapa_layak',
            'COCO-REJECT': 'coconut_receiving.location_stok_kelapa_reject',
            'COCO-SHELLER': 'coconut_receiving.location_area_sheller',
            'COCO-PARER': 'coconut_receiving.location_area_parer',
        }
        loc_xml = loc_map.get(product.default_code)
        loc = self.env.ref(loc_xml, raise_if_not_found=False) if loc_xml else self.location_wh
        if not loc:
            loc = self.location_wh
        self.env['stock.quant'].with_context(inventory_mode=True).create({
            'product_id': product.id,
            'location_id': loc.id,
            'inventory_quantity': quantity,
        }).action_apply_inventory()

    def _create_mfg(self, **kwargs):
        """Create and confirm a manufacturing document."""
        mfg = self.env['coconut.manufacturing'].create({
            'company_id': self.company.id,
            **kwargs,
        })
        mfg.action_confirm()
        return mfg

    # ─────────────────────────────────────────────────────────────
    # TEST 2: Edit Done Blocker
    # ─────────────────────────────────────────────────────────────
    def test_02_edit_done_blocker(self):
        """
        Editing a completed transfer document must raise UserError.
        """
        self._skip_if_no_products()
        self._adjust_stock(self.p_layak, 100.0)

        mfg = self._create_mfg(
            machine_sheller_input=10.0,
        )
        # Edit in confirmed state
        mfg.write({'notes': 'Catatan Confirmed'})

        # Validate
        mfg.action_validate()
        self.assertEqual(mfg.state, 'done')

        # Edit in done state (should raise UserError)
        with self.assertRaises(UserError, msg="Completed transfer document must not be editable"):
            mfg.write({'notes': 'Catatan Baru Setelah Done'})

    # ─────────────────────────────────────────────────────────────
    # TEST 3: Partial Machine Sheller transfer
    # ─────────────────────────────────────────────────────────────
    def test_03_partial_machine_sheller(self):
        """
        Kelapa Layak available = 25000
        Machine Sheller Input = 18000
        Expected remaining Kelapa Layak = 7000 in Gudang Kelapa Layak
        Expected Kelapa Layak in Area Sheller = 18000
        """
        self._skip_if_no_products()

        self._adjust_stock(self.p_layak, 25000.0)

        qty_layak_before = self._get_qty(self.p_layak)
        self.assertEqual(qty_layak_before, 25000.0)

        mfg = self._create_mfg(
            machine_sheller_input=18000.0,
        )
        mfg.action_validate()

        qty_layak_after = self._get_qty(self.p_layak)
        self.assertAlmostEqual(qty_layak_after, 7000.0, places=2)
        
        # In the new flow, we moved p_layak from Gudang Kelapa Layak to Area Sheller.
        loc_sheller = self.env.ref('coconut_receiving.location_area_sheller')
        qty_layak_in_sheller = self.env['stock.quant']._get_available_quantity(self.p_layak, loc_sheller)
        self.assertAlmostEqual(qty_layak_in_sheller, 18000.0, places=2)

    # ─────────────────────────────────────────────────────────────
    # TEST 5: Transfer validation – exceed stock blocked
    # ─────────────────────────────────────────────────────────────
    def test_05_transfer_exceeds_stock_blocked(self):
        """
        Kelapa Layak available = 100
        Transfer Input = 101 → must raise UserError
        """
        self._skip_if_no_products()

        self._adjust_stock(self.p_layak, 100.0)

        mfg = self._create_mfg(
            machine_sheller_input=101.0,
        )
        with self.assertRaises(UserError):
            mfg.action_validate()

    # TEST 6: Duplicate validation blocked (manufacturing)
    # ─────────────────────────────────────────────────────────────
    def test_06_duplicate_manufacturing_validation_blocked(self):
        """
        Validating a 'done' transfer document again must raise UserError.
        """
        self._skip_if_no_products()
        self._adjust_stock(self.p_layak, 100.0)

        mfg = self._create_mfg(
            machine_sheller_input=10.0,
        )
        mfg.action_validate()
        self.assertEqual(mfg.state, 'done')

        # Reset state to confirmed to simulate duplicate validate trigger
        mfg.state = 'confirmed'
        with self.assertRaises(UserError, msg="Duplicate validation must be blocked"):
            mfg.action_validate()

    # TEST 7: Invalid UoM (manufacturing)
    # ─────────────────────────────────────────────────────────────
    def test_07_invalid_uom_in_manufacturing_blocked(self):
        """
        If Kelapa Layak has non-Weight UoM, action_validate must raise UserError.
        """
        self._skip_if_no_products()

        uom_unit = self.env.ref('uom.product_uom_unit')
        dummy_variant = self.env['product.product'].create({
            'name': 'Dummy Unit Variant',
            'type': 'consu',
            'uom_id': uom_unit.id,
            'uom_po_id': uom_unit.id,
        })

        xml_record = self.env['ir.model.data'].search([
            ('module', '=', 'coconut_receiving'),
            ('name', '=', 'product_kelapa_layak'),
        ], limit=1)
        original_res_id = xml_record.res_id

        try:
            xml_record.write({'res_id': dummy_variant.product_tmpl_id.id})
            mfg = self._create_mfg(
                machine_sheller_input=10.0,
            )
            with self.assertRaises(UserError):
                mfg.action_validate()
        finally:
            xml_record.write({'res_id': original_res_id})



    # ─────────────────────────────────────────────────────────────
    # TEST 8: Removed processes not in active manufacturing
    # ─────────────────────────────────────────────────────────────
    def test_08_no_washing_blanching_drying_in_manufacturing(self):
        """
        coconut.manufacturing model must NOT have fields for
        Kelapa Washing, Kelapa Blanching, or Kelapa Drying.
        """
        mfg_fields = self.env['coconut.manufacturing'].fields_get()
        forbidden_keywords = ['washing', 'blanching', 'drying']
        for field_name in mfg_fields:
            for kw in forbidden_keywords:
                self.assertNotIn(
                    kw, field_name.lower(),
                    msg=f"Field '{field_name}' referencing '{kw}' must not exist in coconut.manufacturing"
                )
