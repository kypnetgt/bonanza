from odoo import fields, models


class StockPicking(models.Model):
    _inherit = 'stock.picking'

    fabricacion_id = fields.Many2one(
        'textil.fabricacion', string='Fabricación', index=True, copy=False)
