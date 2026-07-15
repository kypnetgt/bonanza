from odoo import fields, models


class TextilMedida(models.Model):
    _name = 'textil.medida'
    _description = 'Medida / Loop de Hilo'
    _order = 'name'

    name = fields.Char(string='Medida (Loop)', required=True)
    code = fields.Char(string='Código')
    active = fields.Boolean(default=True)

    _sql_constraints = [
        ('name_uniq', 'unique(name)', 'Ya existe una medida con este nombre.'),
    ]
