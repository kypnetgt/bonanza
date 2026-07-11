from odoo import Command, _, api, fields, models
from odoo.exceptions import UserError
from odoo.tools import float_compare


class StockBulkRepack(models.Model):
    _name = 'stock.bulk.repack'
    _description = 'Conversión y Empaque'
    _inherit = ['mail.thread', 'mail.activity.mixin']
    _order = 'date desc, id desc'

    def _default_warehouse_id(self):
        return self.env['stock.warehouse'].search([('company_id', '=', self.env.company.id)], limit=1)

    name = fields.Char(
        string='Número', required=True, copy=False, readonly=True, default=lambda self: _('New'),
    )
    date = fields.Datetime(string='Fecha', required=True, default=fields.Datetime.now, tracking=True)
    bulk_product_id = fields.Many2one(
        'product.product', string='Producto a Granel', required=True,
        domain="[('is_bulk_product', '=', True)]",
        readonly="state != 'draft'", tracking=True,
    )
    source_lot_id = fields.Many2one(
        'stock.lot', string='Lote Origen', required=True,
        domain="[('product_id', '=', bulk_product_id)]",
        readonly="state != 'draft'", tracking=True,
    )
    warehouse_id = fields.Many2one(
        'stock.warehouse', string='Almacén', required=True,
        default=_default_warehouse_id, readonly="state != 'draft'",
    )
    source_location_id = fields.Many2one(
        'stock.location', string='Ubicación Origen', required=True,
        domain="[('usage', '=', 'internal')]", readonly="state != 'draft'",
    )
    destination_location_id = fields.Many2one(
        'stock.location', string='Ubicación Destino', required=True,
        domain="[('usage', '=', 'internal')]", readonly="state != 'draft'",
    )
    production_location_id = fields.Many2one(
        'stock.location', string='Ubicación de Producción (Virtual)',
        compute='_compute_production_location_id', store=True, readonly=True,
    )
    user_id = fields.Many2one(
        'res.users', string='Responsable', required=True, default=lambda self: self.env.user,
        readonly="state != 'draft'", tracking=True,
    )
    company_id = fields.Many2one(
        'res.company', string='Compañía', required=True, default=lambda self: self.env.company,
    )
    company_currency_id = fields.Many2one(
        'res.currency', related='company_id.currency_id', string='Moneda',
    )
    state = fields.Selection(
        [
            ('draft', 'Borrador'),
            ('confirmed', 'Confirmado'),
            ('done', 'Realizado'),
            ('cancelled', 'Cancelado'),
        ],
        string='Estado', default='draft', copy=False, tracking=True,
    )
    line_ids = fields.One2many('stock.bulk.repack.line', 'repack_id', string='Líneas')
    move_ids = fields.One2many('stock.move', 'bulk_repack_id', string='Movimientos de Inventario')

    bulk_unit_cost = fields.Float(
        string='Costo Promedio (por lb)', compute='_compute_bulk_unit_cost',
        digits='Product Price',
    )
    pounds_available = fields.Float(
        string='Libras Disponibles', compute='_compute_pounds_available',
        digits='Product Unit of Measure',
    )
    pounds_consumed = fields.Float(
        string='Libras Consumidas', compute='_compute_pounds_consumed', store=True,
        digits='Product Unit of Measure',
    )
    pounds_remaining = fields.Float(
        string='Libras Restantes', compute='_compute_pounds_remaining',
        digits='Product Unit of Measure',
    )
    total_packages = fields.Integer(string='Total de Paquetes', compute='_compute_total_packages')
    total_cost_transferred = fields.Monetary(
        string='Costo Trasladado', compute='_compute_total_cost_transferred',
        currency_field='company_currency_id',
    )

    move_count = fields.Integer(string='# Movimientos', compute='_compute_move_count')
    product_count = fields.Integer(string='# Productos', compute='_compute_product_count')
    valuation_move_count = fields.Integer(string='# Capas de Valoración', compute='_compute_valuation_move_count')

    @api.depends('bulk_product_id', 'company_id')
    def _compute_production_location_id(self):
        for repack in self:
            location = False
            if repack.bulk_product_id:
                location = repack.bulk_product_id.product_tmpl_id.with_company(
                    repack.company_id).property_stock_production
            repack.production_location_id = location

    @api.depends('bulk_product_id', 'company_id')
    def _compute_bulk_unit_cost(self):
        for repack in self:
            repack.bulk_unit_cost = (
                repack.bulk_product_id.with_company(repack.company_id).standard_price
                if repack.bulk_product_id else 0.0
            )

    @api.depends('bulk_product_id', 'source_location_id', 'source_lot_id')
    def _compute_pounds_available(self):
        for repack in self:
            if not repack.bulk_product_id or not repack.source_location_id:
                repack.pounds_available = 0.0
                continue
            repack.pounds_available = self.env['stock.quant']._get_available_quantity(
                repack.bulk_product_id,
                repack.source_location_id,
                lot_id=repack.source_lot_id or None,
                strict=False,
            )

    @api.depends('line_ids.pounds_consumed')
    def _compute_pounds_consumed(self):
        for repack in self:
            repack.pounds_consumed = sum(repack.line_ids.mapped('pounds_consumed'))

    @api.depends('pounds_available', 'pounds_consumed')
    def _compute_pounds_remaining(self):
        for repack in self:
            repack.pounds_remaining = repack.pounds_available - repack.pounds_consumed

    @api.depends('line_ids.qty_packages')
    def _compute_total_packages(self):
        for repack in self:
            repack.total_packages = sum(repack.line_ids.mapped('qty_packages'))

    @api.depends('line_ids.total_cost')
    def _compute_total_cost_transferred(self):
        for repack in self:
            repack.total_cost_transferred = sum(repack.line_ids.mapped('total_cost'))

    @api.depends('move_ids')
    def _compute_move_count(self):
        for repack in self:
            repack.move_count = len(repack.move_ids)

    @api.depends('line_ids.presentation_product_id')
    def _compute_product_count(self):
        for repack in self:
            repack.product_count = len(repack.line_ids.presentation_product_id)

    @api.depends('move_ids.is_in', 'move_ids.is_out')
    def _compute_valuation_move_count(self):
        for repack in self:
            repack.valuation_move_count = len(
                repack.move_ids.filtered(lambda m: m.is_in or m.is_out))

    @api.onchange('warehouse_id')
    def _onchange_warehouse_id(self):
        if self.warehouse_id:
            self.source_location_id = self.warehouse_id.lot_stock_id
            self.destination_location_id = self.warehouse_id.lot_stock_id

    @api.onchange('bulk_product_id', 'source_lot_id')
    def _onchange_bulk_product_source_lot(self):
        self.line_ids = [Command.clear()]
        if not self.bulk_product_id:
            return
        presentations = self.env['product.product'].search([
            ('product_tmpl_id.bulk_product_id', '=', self.bulk_product_id.product_tmpl_id.id),
        ])
        self.line_ids = [
            Command.create({'presentation_product_id': product.id, 'qty_packages': 0})
            for product in presentations
        ]

    @api.model_create_multi
    def create(self, vals_list):
        for vals in vals_list:
            if vals.get('name', _('New')) == _('New'):
                vals['name'] = self.env['ir.sequence'].next_by_code('stock.bulk.repack') or _('New')
        return super().create(vals_list)

    def _get_active_lines(self):
        self.ensure_one()
        return self.line_ids.filtered(lambda line: line.qty_packages > 0)

    def _validate_before_confirm(self):
        self.ensure_one()
        errors = []
        if not self.source_lot_id:
            errors.append(_('Debe indicar el lote origen.'))
        if not self.production_location_id:
            errors.append(_(
                'El producto a granel "%s" no tiene configurada una Ubicación de Producción. '
                'Revise Ajustes > Inventario > Ubicaciones.',
                self.bulk_product_id.display_name,
            ))
        active_lines = self._get_active_lines()
        if not active_lines:
            errors.append(_('Debe ingresar al menos una línea con cantidad de paquetes mayor a cero.'))
        for line in active_lines:
            if not line.lot_id:
                errors.append(_(
                    'La línea de "%s" requiere un lote.', line.presentation_product_id.display_name))
            if not line.expiration_date:
                errors.append(_(
                    'La línea de "%s" requiere una fecha de vencimiento.',
                    line.presentation_product_id.display_name,
                ))
        if active_lines:
            total_pounds = sum(active_lines.mapped('pounds_consumed'))
            rounding = self.bulk_product_id.uom_id.rounding if self.bulk_product_id else 0.01
            if float_compare(total_pounds, self.pounds_available, precision_rounding=rounding) > 0:
                errors.append(_(
                    'Inventario insuficiente: disponible %(available).2f, requerido %(required).2f.',
                    available=self.pounds_available, required=total_pounds,
                ))
        if errors:
            raise UserError('\n'.join(errors))

    def _create_moves(self, active_lines):
        self.ensure_one()
        total_pounds = sum(active_lines.mapped('pounds_consumed'))
        bulk_move = self.env['stock.move'].create({
            'name': self.name,
            'origin': self.name,
            'product_id': self.bulk_product_id.id,
            'product_uom_qty': total_pounds,
            'product_uom': self.bulk_product_id.uom_id.id,
            'location_id': self.source_location_id.id,
            'location_dest_id': self.production_location_id.id,
            'company_id': self.company_id.id,
            'bulk_repack_id': self.id,
        })
        presentation_moves = self.env['stock.move']
        for line in active_lines:
            move = self.env['stock.move'].create({
                'name': self.name,
                'origin': self.name,
                'product_id': line.presentation_product_id.id,
                'product_uom_qty': line.qty_packages,
                'product_uom': line.presentation_product_id.uom_id.id,
                'location_id': self.production_location_id.id,
                'location_dest_id': self.destination_location_id.id,
                'company_id': self.company_id.id,
                'bulk_repack_id': self.id,
                'bulk_repack_line_id': line.id,
            })
            line.move_id = move
            presentation_moves |= move
        return bulk_move | presentation_moves

    def _create_move_lines(self, moves):
        self.ensure_one()
        bulk_move = moves.filtered(lambda m: not m.bulk_repack_line_id)
        bulk_move.ensure_one()
        self.env['stock.move.line'].create({
            'move_id': bulk_move.id,
            'product_id': bulk_move.product_id.id,
            'product_uom_id': bulk_move.product_uom.id,
            'quantity': bulk_move.product_uom_qty,
            'lot_id': self.source_lot_id.id,
            'location_id': bulk_move.location_id.id,
            'location_dest_id': bulk_move.location_dest_id.id,
            'picked': True,
            'company_id': self.company_id.id,
        })
        for move in moves - bulk_move:
            line = move.bulk_repack_line_id
            self.env['stock.move.line'].create({
                'move_id': move.id,
                'product_id': move.product_id.id,
                'product_uom_id': move.product_uom.id,
                'quantity': move.product_uom_qty,
                'lot_id': line.lot_id.id,
                'location_id': move.location_id.id,
                'location_dest_id': move.location_dest_id.id,
                'picked': True,
                'company_id': self.company_id.id,
            })

    def action_confirm(self):
        self.ensure_one()
        if self.state != 'draft':
            raise UserError(_('Solo se puede confirmar una Conversión y Empaque en estado Borrador.'))
        self._validate_before_confirm()
        active_lines = self._get_active_lines()
        moves = self._create_moves(active_lines)
        moves._action_confirm()
        self._create_move_lines(moves)
        for line in active_lines:
            line.move_id.value_manual = line.total_cost
        moves._action_done()
        if any(move.state != 'done' for move in moves):
            raise UserError(_(
                'Uno o más movimientos no pudieron completarse. Revise las líneas e intente nuevamente.'))
        self.write({'state': 'done'})

    def action_cancel(self):
        for repack in self:
            if repack.state == 'done':
                raise UserError(_('No se puede cancelar una Conversión y Empaque ya realizada.'))
            repack.state = 'cancelled'

    def action_draft(self):
        for repack in self:
            if repack.state != 'cancelled':
                raise UserError(_(
                    'Solo se puede restablecer a borrador una Conversión y Empaque cancelada.'))
            repack.state = 'draft'

    def action_view_moves(self):
        self.ensure_one()
        return {
            'name': _('Movimientos de Inventario'),
            'type': 'ir.actions.act_window',
            'res_model': 'stock.move',
            'view_mode': 'list,form',
            'domain': [('bulk_repack_id', '=', self.id)],
            'context': {'create': False},
        }

    def action_view_products(self):
        self.ensure_one()
        products = self.line_ids.presentation_product_id
        return {
            'name': _('Productos Generados'),
            'type': 'ir.actions.act_window',
            'res_model': 'product.product',
            'view_mode': 'list,form',
            'domain': [('id', 'in', products.ids)],
            'context': {'create': False},
        }

    def action_view_valuation(self):
        self.ensure_one()
        action = self.env['ir.actions.act_window']._for_xml_id(
            'stock_account.stock_move_valuation_action')
        action['domain'] = [
            ('bulk_repack_id', '=', self.id),
            '|', ('is_in', '=', True), ('is_out', '=', True),
        ]
        action['context'] = {'create': False}
        return action

    def action_view_traceability(self):
        self.ensure_one()
        return {
            'name': _('Trazabilidad'),
            'type': 'ir.actions.act_window',
            'res_model': 'stock.move.line',
            'view_mode': 'list,form',
            'domain': [('move_id', 'in', self.move_ids.ids)],
            'context': {'create': False},
        }
