from odoo import fields, models


class TextilTipoTela(models.Model):
    _name = 'textil.tipo.tela'
    _description = 'Tipo de Tela'
    _order = 'name'

    name = fields.Char(string='Tipo de Tela', required=True)
    code = fields.Char(string='Código')
    active = fields.Boolean(default=True)

    _sql_constraints = [
        ('name_uniq', 'unique(name)', 'Ya existe un tipo de tela con este nombre.'),
    ]
