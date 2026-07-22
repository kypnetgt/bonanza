from odoo import api, fields, models


class TextilFabricacionMaquinaProduccion(models.Model):
    _name = 'textil.fabricacion.maquina.produccion'
    _description = 'Producción Diaria por Máquina'
    _order = 'fecha desc, id desc'

    fabricacion_id = fields.Many2one(
        'textil.fabricacion', string='Fabricación',
        required=True, ondelete='cascade', index=True)
    turno = fields.Selection([
        ('dia', 'Día'),
        ('noche', 'Noche'),
    ], string='Turno', required=True, default='dia')
    empleado_id = fields.Many2one('hr.employee', string='Empleado', required=True)
    maquina_id = fields.Many2one(
        related='fabricacion_id.maquina_id', string='Máquina', store=True)
    lot_id = fields.Many2one(
        'stock.lot', string='Cono / Lote', required=True,
        domain="[('id', 'in', fabricacion_lot_ids)]")
    fabricacion_lot_ids = fields.Many2many(
        related='fabricacion_id.hilo_lot_ids', string='Conos de la Fabricación')
    fecha = fields.Date(string='Fecha', required=True, default=fields.Date.context_today)
    kg_hechos = fields.Float(string='Kilogramos Hechos', required=True)
    note = fields.Char(string='Nota')

    partner_id = fields.Many2one(related='fabricacion_id.partner_id', string='Cliente', store=True)

    @api.model_create_multi
    def create(self, vals_list):
        records = super().create(vals_list)
        records.fabricacion_id.sudo()._reconciliar_rollos()
        return records

    def write(self, vals):
        result = super().write(vals)
        if 'kg_hechos' in vals or 'lot_id' in vals:
            self.fabricacion_id.sudo()._reconciliar_rollos()
        return result

    def unlink(self):
        fabricaciones = self.fabricacion_id
        result = super().unlink()
        fabricaciones.sudo()._reconciliar_rollos()
        return result
