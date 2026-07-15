from odoo import fields, models


class StockPicking(models.Model):
    _inherit = 'stock.picking'

    fabricacion_id = fields.Many2one(
        'textil.fabricacion', string='Fabricación', index=True, copy=False)

    def _compute_state(self):
        super()._compute_state()
        for picking in self.sudo().filtered(lambda p: p.fabricacion_id and p.state == 'done'):
            picking.fabricacion_id.line_ids.filtered(
                lambda l: l.move_id.picking_id == picking
            ).write({'state': 'done'})
