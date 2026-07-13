# -*- coding: utf-8 -*-
from odoo.tests.common import TransactionCase
from odoo.exceptions import UserError, ValidationError


class TestCoconutManufacturing(TransactionCase):
    """
    Tests for coconut_sorting module (coconut.manufacturing model).

    TEST 2: Sorting transformation (Kelapa Bulat → Layak + Reject)
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
        if not product or not self.location_wh:
            return 0.0
        return self.env['stock.quant']._get_available_quantity(product, self.location_wh)

    def _create_validated_receipt(self, gross, tare, pot=0.0):
        """Create and validate a coconut receipt, returning it."""
        receipt = self.env['coconut.receipt'].create({
            'partner_id': self.partner.id,
            'gross_vehicle_weight': gross,
            'tare_vehicle_weight': tare,
            'pot_weight': pot,
            'origin': 'Test Origin',
            'company_id': self.company.id,
        })
        receipt.action_validate()
        return receipt

    def _create_mfg(self, receipt, **kwargs):
        """Create and confirm a manufacturing document."""
        mfg = self.env['coconut.manufacturing'].create({
            'receipt_id': receipt.id,
            'company_id': self.company.id,
            **kwargs,
        })
        mfg.action_confirm()
        return mfg

    # ─────────────────────────────────────────────────────────────
    # TEST 2: Sorting transformation
    # ─────────────────────────────────────────────────────────────
    def test_02_sorting_transformation(self):
        """
        Kelapa Bulat available = 11410
        Sorting: good=10900, reject=510
        After validation:
          Kelapa Bulat: -11410
          Kelapa Layak Produksi: +10900
          Kelapa Reject: +510
        """
        self._skip_if_no_products()

        # Create receipt to add 11410 kg Kelapa Bulat
        receipt = self._create_validated_receipt(gross=16440.0, tare=5030.0)

        qty_bulat_before = self._get_qty(self.p_bulat)
        qty_layak_before = self._get_qty(self.p_layak)
        qty_reject_before = self._get_qty(self.p_reject)

        mfg = self._create_mfg(
            receipt,
            raw_coconut_processed=11410.0,
            good_coconut_weight=10900.0,
            reject_coconut_weight=510.0,
            total_coconut_count=0,
            machine_sheller_input=0.0,
            manual_sheller_input=0.0,
            machine_sheller_output=0.0,
            manual_sheller_output=0.0,
            parer_input=0.0,
            parer_output=0.0,
        )
        mfg.action_validate()
        self.assertEqual(mfg.state, 'done')

        qty_bulat_after = self._get_qty(self.p_bulat)
        qty_layak_after = self._get_qty(self.p_layak)
        qty_reject_after = self._get_qty(self.p_reject)

        self.assertAlmostEqual(
            qty_bulat_before - qty_bulat_after, 11410.0, places=2,
            msg="Kelapa Bulat must decrease by 11410 kg"
        )
        self.assertAlmostEqual(
            qty_layak_after - qty_layak_before, 10900.0, places=2,
            msg="Kelapa Layak Produksi must increase by 10900 kg"
        )
        self.assertAlmostEqual(
            qty_reject_after - qty_reject_before, 510.0, places=2,
            msg="Kelapa Reject must increase by 510 kg"
        )

    # ─────────────────────────────────────────────────────────────
    # TEST 3: Partial Machine Sheller consumption
    # ─────────────────────────────────────────────────────────────
    def test_03_partial_machine_sheller(self):
        """
        Kelapa Layak available ≥ 20000
        Machine Sheller Input = 18000
        Expected remaining Kelapa Layak = available - 18000 (i.e. ≥ 2000)
        """
        self._skip_if_no_products()

        # First, get enough Kelapa Layak by doing a sorting pass
        receipt = self._create_validated_receipt(gross=30000.0, tare=5000.0)
        mfg1 = self._create_mfg(
            receipt,
            raw_coconut_processed=25000.0,
            good_coconut_weight=24500.0,
            reject_coconut_weight=500.0,
            total_coconut_count=0,
            machine_sheller_input=0.0,
            manual_sheller_input=0.0,
            machine_sheller_output=0.0,
            manual_sheller_output=0.0,
            parer_input=0.0,
            parer_output=0.0,
        )
        mfg1.action_validate()

        qty_layak_before = self._get_qty(self.p_layak)
        self.assertGreaterEqual(qty_layak_before, 18000.0,
                                "Need at least 18000 kg Kelapa Layak for this test")

        # Now run sheller with partial consumption
        receipt2 = self._create_validated_receipt(gross=10000.0, tare=3000.0)
        mfg2 = self._create_mfg(
            receipt2,
            raw_coconut_processed=7000.0,
            good_coconut_weight=6800.0,
            reject_coconut_weight=200.0,
            total_coconut_count=0,
            machine_sheller_input=18000.0,
            manual_sheller_input=0.0,
            machine_sheller_output=17500.0,
            manual_sheller_output=0.0,
            parer_input=0.0,
            parer_output=0.0,
        )
        mfg2.action_validate()

        qty_layak_after = self._get_qty(self.p_layak)
        consumed = qty_layak_before - qty_layak_after
        self.assertAlmostEqual(consumed, 18000.0, places=2,
                               msg="18000 kg Kelapa Layak must be consumed by Machine Sheller")
        # Remaining must be correct
        remaining = qty_layak_after
        self.assertGreaterEqual(remaining, 0.0, "Remaining Kelapa Layak must not be negative")

    # ─────────────────────────────────────────────────────────────
    # TEST 4: Manual Sheller consumption
    # ─────────────────────────────────────────────────────────────
    def test_04_manual_sheller_consumption(self):
        """
        Kelapa Reject available ≥ 570
        Manual Sheller Input = 300
        Remaining Kelapa Reject = available - 300
        """
        self._skip_if_no_products()

        # Create reject stock
        receipt = self._create_validated_receipt(gross=10000.0, tare=2000.0)
        mfg1 = self._create_mfg(
            receipt,
            raw_coconut_processed=8000.0,
            good_coconut_weight=7430.0,
            reject_coconut_weight=570.0,
            total_coconut_count=0,
            machine_sheller_input=0.0,
            manual_sheller_input=0.0,
            machine_sheller_output=0.0,
            manual_sheller_output=0.0,
            parer_input=0.0,
            parer_output=0.0,
        )
        mfg1.action_validate()

        qty_reject_before = self._get_qty(self.p_reject)
        self.assertGreaterEqual(qty_reject_before, 300.0,
                                "Need at least 300 kg Kelapa Reject for this test")

        # Manual sheller: consume 300 kg
        receipt2 = self._create_validated_receipt(gross=5000.0, tare=2000.0)
        mfg2 = self._create_mfg(
            receipt2,
            raw_coconut_processed=3000.0,
            good_coconut_weight=2900.0,
            reject_coconut_weight=100.0,
            total_coconut_count=0,
            machine_sheller_input=0.0,
            manual_sheller_input=300.0,
            machine_sheller_output=0.0,
            manual_sheller_output=290.0,
            parer_input=0.0,
            parer_output=0.0,
        )
        mfg2.action_validate()

        qty_reject_after = self._get_qty(self.p_reject)
        consumed = qty_reject_before - qty_reject_after
        self.assertAlmostEqual(consumed, 300.0, places=2,
                               msg="300 kg Kelapa Reject must be consumed by Manual Sheller")

    # ─────────────────────────────────────────────────────────────
    # TEST 5: Parer validation – exceed stock blocked
    # ─────────────────────────────────────────────────────────────
    def test_05_parer_exceeds_sheller_stock_blocked(self):
        """
        Kelapa Sheller available = some amount
        Parer Input = available + 1 → must raise UserError
        """
        self._skip_if_no_products()

        qty_sheller = self._get_qty(self.p_sheller)
        parer_input_exceed = qty_sheller + 1.0  # exceeds stock by 1 kg

        receipt = self._create_validated_receipt(gross=10000.0, tare=3000.0)
        mfg = self._create_mfg(
            receipt,
            raw_coconut_processed=7000.0,
            good_coconut_weight=6900.0,
            reject_coconut_weight=100.0,
            total_coconut_count=0,
            machine_sheller_input=0.0,
            manual_sheller_input=0.0,
            machine_sheller_output=0.0,
            manual_sheller_output=0.0,
            parer_input=parer_input_exceed,
            parer_output=parer_input_exceed - 100.0,
        )
        with self.assertRaises(UserError, msg="Parer exceeding Kelapa Sheller stock must be blocked"):
            mfg.action_validate()

    def test_05b_parer_exactly_18001_blocked(self):
        """
        Spec example: Kelapa Sheller = 18000, Parer Input = 18001 → blocked.
        We inject exactly this scenario.
        """
        self._skip_if_no_products()

        # Set up 18000 kg Kelapa Sheller via a full manufacturing pass
        receipt = self._create_validated_receipt(gross=28000.0, tare=5000.0)
        mfg1 = self._create_mfg(
            receipt,
            raw_coconut_processed=23000.0,
            good_coconut_weight=22500.0,
            reject_coconut_weight=500.0,
            total_coconut_count=0,
            machine_sheller_input=22500.0,
            manual_sheller_input=500.0,
            machine_sheller_output=17500.0,
            manual_sheller_output=500.0,
            parer_input=0.0,
            parer_output=0.0,
        )
        mfg1.action_validate()

        qty_sheller = self._get_qty(self.p_sheller)
        # Now try to use 1 kg more than available
        receipt2 = self._create_validated_receipt(gross=5000.0, tare=2000.0)
        mfg2 = self._create_mfg(
            receipt2,
            raw_coconut_processed=3000.0,
            good_coconut_weight=2900.0,
            reject_coconut_weight=100.0,
            total_coconut_count=0,
            machine_sheller_input=0.0,
            manual_sheller_input=0.0,
            machine_sheller_output=0.0,
            manual_sheller_output=0.0,
            parer_input=qty_sheller + 1.0,
            parer_output=qty_sheller,
        )
        with self.assertRaises(UserError):
            mfg2.action_validate()

    # ─────────────────────────────────────────────────────────────
    # TEST 6: Duplicate validation blocked (manufacturing)
    # ─────────────────────────────────────────────────────────────
    def test_06_duplicate_manufacturing_validation_blocked(self):
        """
        Validating a 'done' manufacturing document again must raise UserError.
        """
        self._skip_if_no_products()

        receipt = self._create_validated_receipt(gross=10000.0, tare=3000.0)
        mfg = self._create_mfg(
            receipt,
            raw_coconut_processed=7000.0,
            good_coconut_weight=6800.0,
            reject_coconut_weight=200.0,
            total_coconut_count=0,
            machine_sheller_input=0.0,
            manual_sheller_input=0.0,
            machine_sheller_output=0.0,
            manual_sheller_output=0.0,
            parer_input=0.0,
            parer_output=0.0,
        )
        mfg.action_validate()
        self.assertEqual(mfg.state, 'done')

        # Reset to confirmed to attempt second validation
        # (Should raise because moves already exist)
        mfg.write({'state': 'confirmed'})
        with self.assertRaises(UserError, msg="Duplicate manufacturing validation must be blocked"):
            mfg.action_validate()

    # ─────────────────────────────────────────────────────────────
    # TEST 7: Invalid UoM (manufacturing)
    # ─────────────────────────────────────────────────────────────
    def test_07_invalid_uom_in_manufacturing_blocked(self):
        """
        If Kelapa Layak has non-Weight UoM, action_validate must raise UserError.
        """
        self._skip_if_no_products()

        p_layak_tmpl = self.env.ref('coconut_receiving.product_kelapa_layak')
        uom_unit = self.env.ref('uom.product_uom_unit')
        original_uom = p_layak_tmpl.uom_id
        try:
            p_layak_tmpl.write({'uom_id': uom_unit.id})
            receipt = self._create_validated_receipt(gross=10000.0, tare=3000.0)
            mfg = self._create_mfg(
                receipt,
                raw_coconut_processed=7000.0,
                good_coconut_weight=6800.0,
                reject_coconut_weight=200.0,
                total_coconut_count=0,
                machine_sheller_input=0.0,
                manual_sheller_input=0.0,
                machine_sheller_output=0.0,
                manual_sheller_output=0.0,
                parer_input=0.0,
                parer_output=0.0,
            )
            with self.assertRaises(UserError):
                mfg.action_validate()
        finally:
            p_layak_tmpl.write({'uom_id': original_uom.id})

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

    def test_08b_sorting_balance_validation(self):
        """
        good + reject ≠ raw_coconut_processed must raise UserError.
        """
        self._skip_if_no_products()

        receipt = self._create_validated_receipt(gross=10000.0, tare=3000.0)
        mfg = self._create_mfg(
            receipt,
            raw_coconut_processed=7000.0,
            good_coconut_weight=5000.0,  # intentionally wrong
            reject_coconut_weight=200.0,  # total = 5200 ≠ 7000
            total_coconut_count=0,
            machine_sheller_input=0.0,
            manual_sheller_input=0.0,
            machine_sheller_output=0.0,
            manual_sheller_output=0.0,
            parer_input=0.0,
            parer_output=0.0,
        )
        with self.assertRaises(UserError, msg="Imbalanced sorting must be blocked"):
            mfg.action_validate()
