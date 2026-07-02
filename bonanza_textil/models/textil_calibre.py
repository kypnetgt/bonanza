from odoo import fields, models


class TextilCalibre(models.Model):
    _name = 'textil.calibre'
    _description = 'Calibre / Grosor de Hilo'
    _order = 'name'

    name = fields.Char(string='Calibre', required=True)
    code = fields.Char(string='Código')
    active = fields.Boolean(default=True)

    _sql_constraints = [
        ('name_uniq', 'unique(name)', 'Ya existe un calibre con este nombre.'),
    ]
