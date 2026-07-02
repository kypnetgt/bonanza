from odoo import fields, models


class TextilFabricacionDetalleCono(models.Model):
    _name = 'textil.fabricacion.detalle.cono'
    _description = 'Detalle Manual de Conos (Ficha)'
    _order = 'fabricacion_id, sequence, id'

    fabricacion_id = fields.Many2one(
        'textil.fabricacion', string='Fabricación',
        required=True, ondelete='cascade', index=True)
    sequence = fields.Integer(default=10)
    numero_cono = fields.Char(string='Número de Cono', required=True)
    kg_lote = fields.Float(string='KG Lote', required=True)
