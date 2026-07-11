from datetime import timedelta

from odoo import _, api, fields, models
from odoo.exceptions import ValidationError


class StockBulkRepackLine(models.Model):
    _name = 'stock.bulk.repack.line'
    _description = 'Línea de Conversión y Empaque'

    repack_id = fields.Many2one(
        'stock.bulk.repack', string='Conversión y Empaque', required=True, ondelete='cascade',
    )
    state = fields.Selection(related='repack_id.state', string='Estado')
    company_currency_id = fields.Many2one(related='repack_id.company_currency_id', string='Moneda')
    bulk_product_id = fields.Many2one(
        'product.product', related='repack_id.bulk_product_id', string='Producto a Granel', store=True,
    )
    bulk_product_tmpl_id = fields.Many2one(
        'product.template', related='bulk_product_id.product_tmpl_id',
        string='Plantilla Producto a Granel', store=True,
    )
    presentation_product_id = fields.Many2one(
        'product.product', string='Producto Presentación', required=True,
        domain="[('product_tmpl_id.bulk_product_id', '=', bulk_product_tmpl_id)]",
    )
    qty_packages = fields.Integer(string='Cantidad de Paquetes', default=0)
    package_weight = fields.Float(
        string='Peso por Paquete',
        related='presentation_product_id.product_tmpl_id.package_weight',
        readonly=True, store=True,
    )
    pounds_consumed = fields.Float(
        string='Libras Consumidas', compute='_compute_pounds_consumed', store=True,
        digits='Product Unit of Measure',
    )
    lot_id = fields.Many2one(
        'stock.lot', string='Lote', domain="[('product_id', '=', presentation_product_id)]",
    )
    expiration_date = fields.Date(string='Fecha de Vencimiento')
    unit_cost = fields.Monetary(
        string='Costo Unitario', compute='_compute_costs', store=True, readonly=True,
        currency_field='company_currency_id',
    )
    total_cost = fields.Monetary(
        string='Costo Total', compute='_compute_costs', store=True, readonly=True,
        currency_field='company_currency_id',
    )
    move_id = fields.Many2one('stock.move', string='Movimiento Generado', readonly=True, copy=False)

    @api.constrains('qty_packages')
    def _check_qty_packages(self):
        for line in self:
            if line.qty_packages < 0:
                raise ValidationError(_('La cantidad de paquetes no puede ser negativa.'))

    @api.model
    def _get_default_expiration_date(self, product):
        """Replica el cálculo nativo de product_expiry: hoy + días de vencimiento del producto."""
        template = product.product_tmpl_id
        if template.use_expiration_date and template.expiration_time:
            return fields.Date.context_today(self) + timedelta(days=template.expiration_time)
        return False

    @api.onchange('presentation_product_id')
    def _onchange_presentation_product_id(self):
        if self.presentation_product_id and not self.expiration_date:
            self.expiration_date = self._get_default_expiration_date(self.presentation_product_id)

    @api.depends('qty_packages', 'package_weight')
    def _compute_pounds_consumed(self):
        for line in self:
            line.pounds_consumed = line.qty_packages * line.package_weight

    @api.depends('pounds_consumed', 'qty_packages', 'repack_id.bulk_unit_cost')
    def _compute_costs(self):
        for line in self:
            line.total_cost = line.pounds_consumed * line.repack_id.bulk_unit_cost
            line.unit_cost = line.total_cost / line.qty_packages if line.qty_packages else 0.0
