from odoo import fields, models


class TextilFabricacionMaquinaProduccion(models.Model):
    _name = 'textil.fabricacion.maquina.produccion'
    _description = 'Producción Diaria por Máquina'
    _order = 'fecha desc, id desc'

    fabricacion_id = fields.Many2one(
        'textil.fabricacion', string='Fabricación',
        required=True, ondelete='cascade', index=True)
    maquina_id = fields.Many2one('textil.maquina', string='Máquina', required=True, index=True)
    fecha = fields.Date(string='Fecha', required=True, default=fields.Date.context_today)
    kg_hechos = fields.Float(string='Kilogramos Hechos', required=True)
    note = fields.Char(string='Nota')

    partner_id = fields.Many2one(related='fabricacion_id.partner_id', string='Cliente', store=True)
