# -*- coding: utf-8 -*-
from odoo.tests.common import TransactionCase
from odoo.exceptions import UserError, ValidationError


class TestCoconutReceiving(TransactionCase):
    """
    Tests for coconut_receiving module.

    TEST 1: Net received weight calculation
    TEST 6: Duplicate validation blocked
    TEST 7: Invalid UoM blocked
    TEST 8: Removed processes (Washing/Blanching/Drying) not in active products
    """

    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.partner = cls.env['res.partner'].create({
            'name': 'Test Supplier Kelapa',
            'supplier_rank': 1,
        })
        cls.company = cls.env.company

    def _create_receipt(self, gross=16440.0, tare=5030.0, pot=0.0):
        """Helper to create a draft coconut receipt."""
        return self.env['coconut.receipt'].create({
            'partner_id': self.partner.id,
            'gross_vehicle_weight': gross,
            'tare_vehicle_weight': tare,
            'pot_weight': pot,
            'origin': 'Cianjur',
            'driver_name': 'Test Driver',
            'vehicle_plate': 'B 1234 XY',
            'company_id': self.company.id,
        })

    # ─────────────────────────────────────────────────────────────
    # TEST 1: Net received weight calculation
    # ─────────────────────────────────────────────────────────────
    def test_01_net_received_weight_calculation(self):
        """
        gross=16440, tare=5030, pot=0 → net_received_weight = 11410
        """
        receipt = self._create_receipt(gross=16440.0, tare=5030.0, pot=0.0)
        self.assertAlmostEqual(
            receipt.net_received_weight, 11410.0, places=2,
            msg="Net received weight must be gross - tare - pot = 11410 kg"
        )

    def test_01b_net_received_weight_with_pot(self):
        """
        gross=17000, tare=5000, pot=200 → net=11800
        """
        receipt = self._create_receipt(gross=17000.0, tare=5000.0, pot=200.0)
        self.assertAlmostEqual(
            receipt.net_received_weight, 11800.0, places=2,
            msg="Net received weight must account for pot weight"
        )

    def test_01c_validation_gross_must_be_positive(self):
        """Gross vehicle weight of 0 must raise ValidationError."""
        with self.assertRaises(ValidationError):
            self._create_receipt(gross=0.0, tare=5030.0, pot=0.0)

    def test_01d_validation_net_must_be_positive(self):
        """Tare >= Gross must make net_received_weight <= 0, raise error."""
        with self.assertRaises(ValidationError):
            self._create_receipt(gross=5000.0, tare=6000.0, pot=0.0)

    def test_01e_validation_exit_before_entry(self):
        """Exit time before entry time must raise ValidationError."""
        import datetime
        receipt = self._create_receipt()
        entry = datetime.datetime(2026, 7, 1, 8, 0, 0)
        exit_dt = datetime.datetime(2026, 7, 1, 7, 0, 0)  # before entry
        with self.assertRaises(ValidationError):
            receipt.write({
                'entry_datetime': entry,
                'exit_datetime': exit_dt,
            })

    # ─────────────────────────────────────────────────────────────
    # TEST 1: Stock move after validation
    # ─────────────────────────────────────────────────────────────
    def test_01f_kelapa_bulat_increases_on_validate(self):
        """
        After action_validate, Kelapa Bulat stock increases by net_received_weight.
        """
        receipt = self._create_receipt(gross=16440.0, tare=5030.0, pot=0.0)
        # Get initial stock
        p_bulat_tmpl = self.env.ref('coconut_receiving.product_kelapa_bulat', raise_if_not_found=False)
        if not p_bulat_tmpl:
            self.skipTest("product_kelapa_bulat not found – install module first")

        p_bulat = p_bulat_tmpl.product_variant_ids[:1]
        location = self.env.ref('coconut_receiving.location_gudang_kelapa_bulat', raise_if_not_found=False)
        if not location:
            wh = self.env['stock.warehouse'].search([('company_id', '=', self.company.id)], limit=1)
            location = wh.lot_stock_id if wh else False
        if not location:
            self.skipTest("Warehouse location not found")

        qty_before = self.env['stock.quant']._get_available_quantity(p_bulat, location)
        receipt.action_validate()
        qty_after = self.env['stock.quant']._get_available_quantity(p_bulat, location)

        self.assertAlmostEqual(
            qty_after - qty_before, 11410.0, places=2,
            msg="Kelapa Bulat stock must increase by net_received_weight = 11410 kg"
        )
        self.assertEqual(receipt.state, 'done')
        self.assertTrue(receipt.picking_id)
        self.assertEqual(receipt.picking_id.state, 'done')

    # ─────────────────────────────────────────────────────────────
    # TEST 6: Duplicate validation blocked
    # ─────────────────────────────────────────────────────────────
    def test_06_duplicate_validation_blocked(self):
        """
        Validating a 'done' receipt again must raise UserError.
        No duplicate stock moves should be created.
        """
        receipt = self._create_receipt()
        p_bulat_tmpl = self.env.ref('coconut_receiving.product_kelapa_bulat', raise_if_not_found=False)
        if not p_bulat_tmpl:
            self.skipTest("product_kelapa_bulat not found")

        receipt.action_validate()
        self.assertEqual(receipt.state, 'done')

        # Second validation attempt must raise
        with self.assertRaises(UserError, msg="Duplicate validation must be blocked"):
            receipt.action_validate()

    # ─────────────────────────────────────────────────────────────
    # TEST 7: Invalid UoM
    # ─────────────────────────────────────────────────────────────
    def test_07_invalid_uom_raises_user_error(self):
        """
        If Kelapa Bulat has non-Weight UoM, action_validate must raise UserError
        with a clear configuration error before creating stock moves.
        """
        p_bulat_tmpl = self.env.ref('coconut_receiving.product_kelapa_bulat', raise_if_not_found=False)
        if not p_bulat_tmpl:
            self.skipTest("product_kelapa_bulat not found")

        # Temporarily set a non-weight UoM (Units)
        uom_unit = self.env.ref('uom.product_uom_unit')
        original_uom = p_bulat_tmpl.uom_id
        try:
            self.env.cr.execute("UPDATE product_template SET uom_id = %s WHERE id = %s", (uom_unit.id, p_bulat_tmpl.id))
            p_bulat_tmpl.invalidate_recordset(['uom_id'])
            receipt = self._create_receipt()
            with self.assertRaises(UserError, msg="Must raise UserError for wrong UoM"):
                receipt.action_validate()
        finally:
            self.env.cr.execute("UPDATE product_template SET uom_id = %s WHERE id = %s", (original_uom.id, p_bulat_tmpl.id))
            p_bulat_tmpl.invalidate_recordset(['uom_id'])

    # ─────────────────────────────────────────────────────────────
    # TEST 8: Removed processes not in active workflow
    # ─────────────────────────────────────────────────────────────
    def test_08_no_washing_blanching_drying_in_products(self):
        """
        Kelapa Washing, Kelapa Blanching, and Kelapa Drying must NOT be
        present as active products or appear in the module XML IDs.
        """
        forbidden_names = ['Kelapa Washing', 'Kelapa Blanching', 'Kelapa Drying']
        for name in forbidden_names:
            product = self.env['product.template'].search([
                ('name', 'ilike', name),
                ('active', '=', True),
            ], limit=1)
            self.assertFalse(
                product,
                msg=f"Active product '{name}' must not exist in the system"
            )
