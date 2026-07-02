from odoo import fields, models


class TextilAgujado(models.Model):
    _name = 'textil.agujado'
    _description = 'Agujado'
    _order = 'name'

    name = fields.Char(string='Agujado', required=True)
    code = fields.Char(string='Código')
    active = fields.Boolean(default=True)

    _sql_constraints = [
        ('name_uniq', 'unique(name)', 'Ya existe un agujado con este nombre.'),
    ]
