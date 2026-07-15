from odoo import Command, fields, models


class TextilRollo(models.Model):
    _name = 'textil.rollo'
    _description = 'Rollo de Tela Generado'
    _order = 'fabricacion_id, sequence, id'

    fabricacion_id = fields.Many2one(
        'textil.fabricacion', string='Fabricación',
        required=True, ondelete='cascade', index=True)
    sequence = fields.Integer(default=10)
    name = fields.Char(string='N° de Rollo', required=True, copy=False,
                        default=lambda self: self.env['ir.sequence'].next_by_code('textil.rollo'))
    peso_kg = fields.Float(string='Peso (kg)', required=True)
    origen = fields.Selection([
        ('auto', 'Automático'),
        ('cierre', 'Cierre'),
        ('manual', 'Manual'),
    ], default='manual', required=True)
    state = fields.Selection([
        ('pending', 'Pendiente'),
        ('invoiced', 'Facturado'),
    ], default='pending', required=True, copy=False)

    lot_id = fields.Many2one('stock.lot', string='Lote de Tela', readonly=True, copy=False)
    picking_id = fields.Many2one('stock.picking', string='Entrada de Stock', readonly=True, copy=False)
    sale_order_line_id = fields.Many2one('sale.order.line', string='Línea de Venta', readonly=True, copy=False)
    partner_id = fields.Many2one(related='fabricacion_id.partner_id', string='Cliente', store=True)

    def _generar_entrada_stock(self):
        self.ensure_one()
        fabricacion = self.fabricacion_id
        product = fabricacion._get_tela_product()
        dest_location = fabricacion._get_ubicacion_tela_terminada()
        source_location = self.env['stock.location'].search(
            [('usage', '=', 'production'), ('company_id', 'in', [fabricacion.company_id.id, False])], limit=1)
        picking_type = self.env['stock.picking.type'].search([
            ('code', '=', 'internal'),
            ('warehouse_id.company_id', '=', fabricacion.company_id.id),
        ], limit=1)

        picking = self.env['stock.picking'].create({
            'picking_type_id': picking_type.id,
            'partner_id': fabricacion.partner_id.id,
            'origin': fabricacion.name,
            'fabricacion_id': fabricacion.id,
            'location_id': source_location.id,
            'location_dest_id': dest_location.id,
        })
        move = self.env['stock.move'].create({
            'product_id': product.id,
            'product_uom_qty': self.peso_kg,
            'product_uom': product.uom_id.id,
            'picking_id': picking.id,
            'location_id': source_location.id,
            'location_dest_id': dest_location.id,
            'lot_ids': [Command.set([self.lot_id.id])],
            'restrict_partner_id': fabricacion.partner_id.id,
        })
        picking.action_confirm()
        picking.action_assign()
        for move_line in move.move_line_ids:
            move_line.quantity = move.product_uom_qty
            move_line.lot_id = self.lot_id.id
        picking.button_validate()
        self.picking_id = picking.id
