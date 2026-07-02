from odoo import fields, models


class TextilPorcentajeMezcla(models.Model):
    _name = 'textil.porcentaje.mezcla'
    _description = 'Porcentaje de Mezcla de Hilo'
    _order = 'name'

    name = fields.Char(string='Porcentaje de Mezcla', required=True,
                        help='Ej: 60/40 Algodón/Poliéster')
    code = fields.Char(string='Código')
    active = fields.Boolean(default=True)

    _sql_constraints = [
        ('name_uniq', 'unique(name)', 'Ya existe un porcentaje de mezcla con este nombre.'),
    ]
