from odoo import Command, fields
from odoo.exceptions import UserError
from odoo.tests.common import TransactionCase


class TestStockBulkRepack(TransactionCase):

    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.warehouse = cls.env['stock.warehouse'].search(
            [('company_id', '=', cls.env.company.id)], limit=1)
        cls.location_stock = cls.warehouse.lot_stock_id
        uom_unit = cls.env.ref('uom.product_uom_unit')

        cls.bulk_product = cls.env['product.product'].create({
            'name': 'Café en Grano a Granel',
            'is_storable': True,
            'tracking': 'lot',
            'is_bulk_product': True,
            'standard_price': 20.0,
            'uom_id': uom_unit.id,
        })
        cls.presentation_1 = cls.env['product.product'].create({
            'name': 'Café 5lb',
            'is_storable': True,
            'tracking': 'lot',
            'bulk_product_id': cls.bulk_product.product_tmpl_id.id,
            'package_weight': 5.0,
            'uom_id': uom_unit.id,
        })
        cls.presentation_2 = cls.env['product.product'].create({
            'name': 'Café 2lb',
            'is_storable': True,
            'tracking': 'lot',
            'bulk_product_id': cls.bulk_product.product_tmpl_id.id,
            'package_weight': 2.0,
            'uom_id': uom_unit.id,
        })
        cls.source_lot = cls.env['stock.lot'].create({
            'name': 'LOTE-GRANEL-001',
            'product_id': cls.bulk_product.id,
        })

    def _seed_stock(self, quantity):
        self.env['stock.quant']._update_available_quantity(
            self.bulk_product, self.location_stock, quantity, lot_id=self.source_lot,
        )

    def _create_repack(self, lines_vals):
        return self.env['stock.bulk.repack'].create({
            'bulk_product_id': self.bulk_product.id,
            'source_lot_id': self.source_lot.id,
            'warehouse_id': self.warehouse.id,
            'source_location_id': self.location_stock.id,
            'destination_location_id': self.location_stock.id,
            'line_ids': [Command.create(vals) for vals in lines_vals],
        })

    def test_sufficient_stock_confirms(self):
        """Caso 1: 1000 lb disponibles / consumir 700 -> confirma correctamente."""
        self._seed_stock(1000)
        lot = self.env['stock.lot'].create(
            {'name': 'PRES-1', 'product_id': self.presentation_1.id})
        repack = self._create_repack([{
            'presentation_product_id': self.presentation_1.id,
            'qty_packages': 140,  # 140 * 5 lb = 700 lb
            'lot_id': lot.id,
            'expiration_date': fields.Date.today(),
        }])
        repack.action_confirm()
        self.assertEqual(repack.state, 'done')
        remaining = self.env['stock.quant']._get_available_quantity(
            self.bulk_product, self.location_stock, lot_id=self.source_lot)
        self.assertEqual(remaining, 300)
        bulk_move = repack.move_ids.filtered(lambda m: not m.bulk_repack_line_id)
        self.assertAlmostEqual(bulk_move.value, 700 * 20.0, places=2)

    def test_insufficient_stock_blocks(self):
        """Caso 2: 1000 lb disponibles / consumir 1100 -> bloquea la confirmación."""
        self._seed_stock(1000)
        lot = self.env['stock.lot'].create(
            {'name': 'PRES-2', 'product_id': self.presentation_1.id})
        repack = self._create_repack([{
            'presentation_product_id': self.presentation_1.id,
            'qty_packages': 220,  # 220 * 5 lb = 1100 lb > 1000 disponibles
            'lot_id': lot.id,
            'expiration_date': fields.Date.today(),
        }])
        with self.assertRaises(UserError):
            repack.action_confirm()
        self.assertEqual(repack.state, 'draft')
        self.assertFalse(repack.move_ids)

    def test_zero_quantity_line_generates_no_move(self):
        """Caso 3: línea con 0 paquetes -> no genera movimiento para esa línea."""
        self._seed_stock(1000)
        lot = self.env['stock.lot'].create(
            {'name': 'PRES-3', 'product_id': self.presentation_1.id})
        repack = self._create_repack([
            {
                'presentation_product_id': self.presentation_1.id,
                'qty_packages': 10,
                'lot_id': lot.id,
                'expiration_date': fields.Date.today(),
            },
            {
                'presentation_product_id': self.presentation_2.id,
                'qty_packages': 0,
            },
        ])
        repack.action_confirm()
        self.assertEqual(repack.state, 'done')
        line_zero = repack.line_ids.filtered(
            lambda line: line.presentation_product_id == self.presentation_2)
        self.assertFalse(line_zero.move_id)
        # 1 movimiento de salida del granel + 1 de entrada de la única línea activa
        self.assertEqual(len(repack.move_ids), 2)

    def test_missing_lot_blocks(self):
        """Caso 4: línea sin lote -> muestra error de validación."""
        self._seed_stock(1000)
        repack = self._create_repack([{
            'presentation_product_id': self.presentation_1.id,
            'qty_packages': 10,
            'expiration_date': fields.Date.today(),
        }])
        with self.assertRaises(UserError):
            repack.action_confirm()
        self.assertFalse(repack.move_ids)

    def test_average_cost_transferred_proportionally(self):
        """Caso 5: costo promedio Q20/lb -> se traslada proporcionalmente."""
        self._seed_stock(1000)
        lot = self.env['stock.lot'].create(
            {'name': 'PRES-5', 'product_id': self.presentation_1.id})
        repack = self._create_repack([{
            'presentation_product_id': self.presentation_1.id,
            'qty_packages': 140,  # 700 lb
            'lot_id': lot.id,
            'expiration_date': fields.Date.today(),
        }])
        line = repack.line_ids
        self.assertEqual(repack.bulk_unit_cost, 20.0)
        self.assertAlmostEqual(line.total_cost, 700 * 20.0, places=2)
        repack.action_confirm()
        # El move de entrada de la presentación debe llevar el costo trasladado,
        # no el standard_price propio de la presentación.
        self.assertAlmostEqual(line.move_id.value, line.total_cost, places=2)

    def test_generated_moves_are_picked_and_done(self):
        """Guarda: toda línea de movimiento debe quedar picked=True y todo move en state=done."""
        self._seed_stock(1000)
        lot = self.env['stock.lot'].create(
            {'name': 'PRES-6', 'product_id': self.presentation_1.id})
        repack = self._create_repack([{
            'presentation_product_id': self.presentation_1.id,
            'qty_packages': 50,
            'lot_id': lot.id,
            'expiration_date': fields.Date.today(),
        }])
        repack.action_confirm()
        for move in repack.move_ids:
            self.assertEqual(move.state, 'done')
            for move_line in move.move_line_ids:
                self.assertTrue(move_line.picked)

    def test_double_confirm_is_blocked(self):
        """Guarda: no se puede confirmar dos veces un registro ya en estado 'done'."""
        self._seed_stock(1000)
        lot = self.env['stock.lot'].create(
            {'name': 'PRES-7', 'product_id': self.presentation_1.id})
        repack = self._create_repack([{
            'presentation_product_id': self.presentation_1.id,
            'qty_packages': 50,
            'lot_id': lot.id,
            'expiration_date': fields.Date.today(),
        }])
        repack.action_confirm()
        with self.assertRaises(UserError):
            repack.action_confirm()
