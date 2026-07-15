from odoo import api, fields, models
from odoo.exceptions import ValidationError


class TextilFabricacionLinea(models.Model):
    _name = 'textil.fabricacion.linea'
    _description = 'Línea de Hilo de Fabricación'
    _order = 'fabricacion_id, sequence, id'

    fabricacion_id = fields.Many2one(
        'textil.fabricacion', string='Fabricación',
        required=True, ondelete='cascade', index=True)
    sequence = fields.Integer(default=10)

    product_id = fields.Many2one(
        'product.product', string='Producto (Hilo)', required=True,
        domain=[('is_storable', '=', True)])
    lotes_cliente_ids = fields.Many2many(
        related='fabricacion_id.lotes_cliente_ids', string='Conos del Cliente')
    lot_id = fields.Many2one(
        'stock.lot', string='Cono / Lote', required=True,
        domain="[('id', 'in', lotes_cliente_ids), ('product_id', '=', product_id)]")

    cantidad = fields.Float(string='Cantidad (kg)', required=True)
    cantidad_disponible = fields.Float(
        string='Disponible (kg)', compute='_compute_cantidad_disponible')

    move_id = fields.Many2one('stock.move', string='Movimiento de Stock', readonly=True, copy=False)
    state = fields.Selection([
        ('draft', 'Borrador'),
        ('done', 'Procesada'),
    ], default='draft', required=True, copy=False)

    partner_id = fields.Many2one(related='fabricacion_id.partner_id', string='Cliente', store=False)

    @api.depends('product_id', 'lot_id', 'fabricacion_id.partner_id')
    def _compute_cantidad_disponible(self):
        Quant = self.env['stock.quant']
        for line in self:
            if not (line.product_id and line.lot_id and line.fabricacion_id.partner_id):
                line.cantidad_disponible = 0.0
                continue
            commercial_partner = line.fabricacion_id.partner_id.commercial_partner_id
            quants = Quant.search([
                ('product_id', '=', line.product_id.id),
                ('lot_id', '=', line.lot_id.id),
                '|', ('owner_id', '=', False), ('owner_id.commercial_partner_id', '=', commercial_partner.id),
            ])
            line.cantidad_disponible = sum(quants.mapped('quantity')) - sum(quants.mapped('reserved_quantity'))

    @api.constrains('cantidad', 'lot_id', 'product_id')
    def _check_cantidad_disponible(self):
        for line in self:
            if line.state != 'draft':
                continue
            if line.cantidad <= 0:
                raise ValidationError('La cantidad de hilo debe ser mayor a cero.')
            if line.cantidad > line.cantidad_disponible:
                Quant = self.env['stock.quant']
                quants = Quant.search([
                    ('product_id', '=', line.product_id.id),
                    ('lot_id', '=', line.lot_id.id),
                ])
                propietarios = ', '.join(quants.mapped('owner_id.display_name')) or '(sin quants para este producto/lote)'
                raise ValidationError(
                    'No hay suficiente hilo disponible para %s (cono %s). '
                    'Disponible: %.2f kg, solicitado: %.2f kg.\n'
                    'Cliente de la fabricación: %s. Propietario(s) encontrados en el stock de ese cono: %s.' % (
                        line.product_id.display_name, line.lot_id.name or '',
                        line.cantidad_disponible, line.cantidad,
                        line.fabricacion_id.partner_id.display_name, propietarios))
