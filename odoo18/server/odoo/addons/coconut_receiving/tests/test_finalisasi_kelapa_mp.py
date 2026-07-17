# -*- coding: utf-8 -*-
from odoo.tests.common import TransactionCase
from odoo.exceptions import ValidationError, UserError

class TestFinalisasiKelapaMP(TransactionCase):

    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.company = cls.env.company
        cls.uom_kg = cls.env.ref('uom.product_uom_kgm')

        # Resolve products
        cls.tmpl_parer = cls.env.ref('coconut_receiving.product_kelapa_parer')
        cls.p_parer = cls.tmpl_parer.product_variant_ids[:1]

        cls.tmpl_akhir_mp = cls.env.ref('coconut_receiving.product_kelapa_akhir_mp')
        cls.p_akhir_mp = cls.tmpl_akhir_mp.product_variant_ids[:1]

        # Resolve locations
        cls.loc_parer = cls.env.ref('coconut_receiving.location_area_parer')
        cls.loc_akhir_mp = cls.env.ref('coconut_receiving.location_gudang_kelapa_akhir_mp')
        cls.loc_prod = cls.env.ref('coconut_receiving.stock_location_coconut_manufacturing')

        # Set initial stock for Parer in Area Parer
        cls.env['stock.quant'].with_context(inventory_mode=True).create({
            'product_id': cls.p_parer.id,
            'location_id': cls.loc_parer.id,
            'inventory_quantity': 1000.0,
        }).action_apply_inventory()

    def test_01_validation_qty_zero(self):
        """Must raise ValidationError if quantities are zero or negative."""
        with self.assertRaises(ValidationError):
            self.env['finalisasi.kelapa.mp'].create({
                'batch_number': 'BATCH-001',
                'product_parer_id': self.p_parer.id,
                'parer_qty_used': 0.0,
                'akhir_mp_qty_produced': 100.0,
            }).action_confirm()

    def test_02_validation_exceed_input(self):
        """Must raise ValidationError if output > input."""
        with self.assertRaises(ValidationError):
            self.env['finalisasi.kelapa.mp'].create({
                'batch_number': 'BATCH-002',
                'product_parer_id': self.p_parer.id,
                'parer_qty_used': 100.0,
                'akhir_mp_qty_produced': 150.0,
            }).action_confirm()

    def test_03_validation_exceed_stock(self):
        """Must raise ValidationError if used quantity exceeds available stock."""
        with self.assertRaises(ValidationError):
            self.env['finalisasi.kelapa.mp'].create({
                'batch_number': 'BATCH-003',
                'product_parer_id': self.p_parer.id,
                'parer_qty_used': 1500.0,  # Exceeds 1000.0
                'akhir_mp_qty_produced': 800.0,
            }).action_confirm()

    def test_04_validation_duplicate_batch(self):
        """Must raise ValidationError if batch_number is already validated in done state."""
        tx1 = self.env['finalisasi.kelapa.mp'].create({
            'batch_number': 'BATCH-DUP',
            'product_parer_id': self.p_parer.id,
            'parer_qty_used': 100.0,
            'akhir_mp_qty_produced': 80.0,
        })
        tx1.action_done()

        tx2 = self.env['finalisasi.kelapa.mp'].create({
            'batch_number': 'BATCH-DUP',
            'product_parer_id': self.p_parer.id,
            'parer_qty_used': 50.0,
            'akhir_mp_qty_produced': 40.0,
        })
        with self.assertRaises(ValidationError):
            tx2.action_confirm()

    def test_05_stock_move_execution_and_cancel(self):
        """Verify stock moves are successfully generated on done and reversed on cancel."""
        tx = self.env['finalisasi.kelapa.mp'].create({
            'batch_number': 'BATCH-VALID',
            'product_parer_id': self.p_parer.id,
            'parer_qty_used': 200.0,
            'akhir_mp_qty_produced': 180.0,
        })
        
        # Check initial quantities in specific locations
        parer_qty_before = self.env['stock.quant']._get_available_quantity(self.p_parer, self.loc_parer)
        akhir_qty_before = self.env['stock.quant']._get_available_quantity(self.p_akhir_mp, self.loc_akhir_mp)

        # Process to done
        tx.action_done()
        self.assertEqual(tx.state, 'done')

        # Check stock changes
        parer_qty_after = self.env['stock.quant']._get_available_quantity(self.p_parer, self.loc_parer)
        akhir_qty_after = self.env['stock.quant']._get_available_quantity(self.p_akhir_mp, self.loc_akhir_mp)
        
        self.assertEqual(parer_qty_before - parer_qty_after, 200.0)
        self.assertEqual(akhir_qty_after - akhir_qty_before, 180.0)
        self.assertEqual(len(tx.stock_move_ids), 2)
        
        # Cancel the transaction
        tx.action_cancel()
        self.assertEqual(tx.state, 'cancelled')

        # Stock should be reversed back
        parer_qty_rev = self.env['stock.quant']._get_available_quantity(self.p_parer, self.loc_parer)
        akhir_qty_rev = self.env['stock.quant']._get_available_quantity(self.p_akhir_mp, self.loc_akhir_mp)
        
        self.assertEqual(parer_qty_rev, parer_qty_before)
        self.assertEqual(akhir_qty_rev, akhir_qty_before)
        self.assertEqual(len(tx.stock_move_ids), 4)  # 2 original + 2 reverse
