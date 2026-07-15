from odoo import fields, models


class TextilMaquina(models.Model):
    _name = 'textil.maquina'
    _description = 'Máquina de Tejido'
    _order = 'name'

    name = fields.Char(string='Máquina', required=True)
    code = fields.Char(string='Código')
    capacidad_kg_dia = fields.Float(string='Capacidad (kg/día)')
    note = fields.Text(string='Notas')
    active = fields.Boolean(default=True)

    _sql_constraints = [
        ('name_uniq', 'unique(name)', 'Ya existe una máquina con este nombre.'),
    ]
