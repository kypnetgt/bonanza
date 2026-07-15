from odoo import fields, models


class TextilTipoHilo(models.Model):
    _name = 'textil.tipo.hilo'
    _description = 'Tipo de Hilo'
    _order = 'name'

    name = fields.Char(string='Tipo de Hilo', required=True)
    code = fields.Char(string='Código')
    active = fields.Boolean(default=True)

    _sql_constraints = [
        ('name_uniq', 'unique(name)', 'Ya existe un tipo de hilo con este nombre.'),
    ]
