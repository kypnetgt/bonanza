from odoo import fields, models


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
    state = fields.Selection([
        ('pending', 'Pendiente'),
        ('invoiced', 'Facturado'),
    ], default='pending', required=True, copy=False)

    sale_order_line_id = fields.Many2one('sale.order.line', string='Línea de Venta', readonly=True, copy=False)
    partner_id = fields.Many2one(related='fabricacion_id.partner_id', string='Cliente', store=True)
