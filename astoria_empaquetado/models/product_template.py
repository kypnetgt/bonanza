from odoo import _, api, fields, models
from odoo.exceptions import ValidationError


class ProductTemplate(models.Model):
    _inherit = 'product.template'

    is_bulk_product = fields.Boolean(
        string='Es Producto a Granel',
        help='Marca este producto como un producto a granel que puede convertirse en presentaciones comerciales.',
    )
    bulk_product_id = fields.Many2one(
        'product.template',
        string='Producto a Granel de Origen',
        domain="[('is_bulk_product', '=', True)]",
        help='Producto a granel del cual se obtiene esta presentación comercial.',
    )
    package_weight = fields.Float(
        string='Peso por Paquete',
        digits='Product Unit of Measure',
        help='Peso de un paquete de esta presentación, expresado en la unidad de medida del producto a granel.',
    )
    bulk_presentation_ids = fields.One2many(
        'product.template', 'bulk_product_id',
        string='Presentaciones',
    )

    @api.constrains('is_bulk_product', 'bulk_product_id', 'package_weight')
    def _check_bulk_config(self):
        for product in self:
            if product.is_bulk_product and product.bulk_product_id:
                raise ValidationError(_(
                    'Un producto a granel no puede ser a la vez una presentación de otro producto a granel: %s',
                    product.display_name,
                ))
            if product.bulk_product_id:
                if not product.bulk_product_id.is_bulk_product:
                    raise ValidationError(_(
                        '"%(bulk)s" no está marcado como producto a granel y no puede ser el origen de "%(presentation)s".',
                        bulk=product.bulk_product_id.display_name,
                        presentation=product.display_name,
                    ))
                if product.package_weight <= 0:
                    raise ValidationError(_(
                        'El peso por paquete de "%s" debe ser mayor a cero.',
                        product.display_name,
                    ))
