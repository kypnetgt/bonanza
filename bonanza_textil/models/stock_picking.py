from odoo import fields, models


class StockPicking(models.Model):
    _inherit = 'stock.picking'

    fabricacion_id = fields.Many2one(
        'textil.fabricacion', string='Fabricación', index=True, copy=False)

    def write(self, vals):
        result = super().write(vals)
        if vals.get('state') == 'done':
            for picking in self.sudo().filtered('fabricacion_id'):
                picking.fabricacion_id.line_ids.filtered(
                    lambda l: l.move_id.picking_id == picking
                ).write({'state': 'done'})
        return result
