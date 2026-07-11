from odoo import fields, models


class StockMove(models.Model):
    _inherit = 'stock.move'

    bulk_repack_id = fields.Many2one(
        'stock.bulk.repack',
        string='Conversión y Empaque',
        copy=False,
        index=True,
    )
    bulk_repack_line_id = fields.Many2one(
        'stock.bulk.repack.line',
        string='Línea de Conversión y Empaque',
        copy=False,
        index=True,
    )
