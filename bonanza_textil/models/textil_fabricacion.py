from odoo import api, fields, models
from odoo.exceptions import UserError


class TextilFabricacion(models.Model):
    _name = 'textil.fabricacion'
    _description = 'Fabricación de Tela'
    _inherit = ['mail.thread', 'mail.activity.mixin']
    _order = 'fecha desc, id desc'

    name = fields.Char(string='Referencia', required=True, copy=False,
                        default=lambda self: 'Nuevo', readonly=True)
    partner_id = fields.Many2one(
        'res.partner', string='Cliente', required=True, tracking=True,
        domain=[('customer_rank', '>', 0)])
    tipo_tela_id = fields.Many2one('textil.tipo.tela', string='Tipo de Tela', required=True)
    ancho = fields.Float(string='Ancho')
    peso_objetivo = fields.Float(string='Peso Objetivo (kg)')
    fecha = fields.Date(string='Fecha', default=fields.Date.context_today, required=True)
    company_id = fields.Many2one('res.company', string='Compañía',
                                  default=lambda self: self.env.company, required=True)
    state = fields.Selection([
        ('draft', 'Borrador'),
        ('confirmed', 'En Proceso'),
        ('done', 'Terminado'),
        ('cancel', 'Cancelado'),
    ], default='draft', required=True, tracking=True, copy=False)

    line_ids = fields.One2many('textil.fabricacion.linea', 'fabricacion_id', string='Hilos / Conos')
    maquina_produccion_ids = fields.One2many(
        'textil.fabricacion.maquina.produccion', 'fabricacion_id', string='Producción por Máquina')
    rollo_ids = fields.One2many('textil.rollo', 'fabricacion_id', string='Rollos')
    detalle_cono_ids = fields.One2many(
        'textil.fabricacion.detalle.cono', 'fabricacion_id', string='Detalle de Conos (Ficha)')
    picking_ids = fields.One2many('stock.picking', 'fabricacion_id', string='Transferencias de Stock')
    picking_count = fields.Integer(compute='_compute_picking_count', string='N° Transferencias')

    total_hilo_consumido = fields.Float(
        string='Hilo Consumido (kg)', compute='_compute_totales', store=True)
    total_hilo_disponible = fields.Float(
        string='Hilo Disponible (kg)', compute='_compute_totales', store=True)
    total_kg_fabricado = fields.Float(
        string='Kg Fabricado', compute='_compute_totales', store=True)
    cantidad_pendiente = fields.Float(
        string='Cantidad Pendiente (kg)', compute='_compute_totales', store=True)
    total_rollos_kg = fields.Float(
        string='Kg en Rollos', compute='_compute_totales', store=True)

    @api.depends('line_ids.cantidad', 'line_ids.cantidad_disponible', 'line_ids.state',
                 'maquina_produccion_ids.kg_hechos', 'rollo_ids.peso_kg', 'peso_objetivo')
    def _compute_totales(self):
        for record in self:
            record.total_hilo_consumido = sum(record.line_ids.filtered(lambda l: l.state == 'done').mapped('cantidad'))
            record.total_hilo_disponible = sum(record.line_ids.mapped('cantidad_disponible'))
            record.total_kg_fabricado = sum(record.maquina_produccion_ids.mapped('kg_hechos'))
            record.total_rollos_kg = sum(record.rollo_ids.mapped('peso_kg'))
            record.cantidad_pendiente = record.peso_objetivo - record.total_kg_fabricado

    def _compute_picking_count(self):
        for record in self:
            record.picking_count = len(record.picking_ids)

    @api.model_create_multi
    def create(self, vals_list):
        for vals in vals_list:
            if vals.get('name', 'Nuevo') == 'Nuevo':
                vals['name'] = self.env['ir.sequence'].next_by_code('textil.fabricacion') or 'Nuevo'
        return super().create(vals_list)

    def action_confirm(self):
        self.ensure_one()
        if not self.line_ids.filtered(lambda l: l.state == 'draft'):
            raise UserError('No hay líneas de hilo pendientes de procesar.')

        picking_type = self.env['stock.picking.type'].search([
            ('code', '=', 'internal'),
            ('warehouse_id.company_id', '=', self.company_id.id),
        ], limit=1)
        if not picking_type:
            raise UserError('No se encontró un tipo de operación interna de inventario para la compañía actual.')

        dest_location = picking_type.default_location_dest_id or self.env.ref('stock.stock_location_stock')

        picking = self.env['stock.picking'].create({
            'picking_type_id': picking_type.id,
            'partner_id': self.partner_id.id,
            'origin': self.name,
            'fabricacion_id': self.id,
            'location_id': picking_type.default_location_src_id.id,
            'location_dest_id': dest_location.id,
        })

        lines_to_process = self.line_ids.filtered(lambda l: l.state == 'draft')
        for line in lines_to_process:
            move = self.env['stock.move'].create({
                'name': line.product_id.display_name,
                'product_id': line.product_id.id,
                'product_uom_qty': line.cantidad,
                'product_uom': line.product_id.uom_id.id,
                'picking_id': picking.id,
                'location_id': line.location_id.id,
                'location_dest_id': dest_location.id,
                'restrict_lot_id': line.lot_id.id,
                'restrict_partner_id': self.partner_id.id,
            })
            line.move_id = move.id

        picking.action_confirm()
        picking.action_assign()
        for move in picking.move_ids:
            for move_line in move.move_line_ids:
                move_line.quantity = move.product_uom_qty
                if move.restrict_lot_id:
                    move_line.lot_id = move.restrict_lot_id.id
        picking.button_validate()

        lines_to_process.write({'state': 'done'})
        self.state = 'confirmed'

    def action_done(self):
        self.write({'state': 'done'})

    def action_cancel(self):
        self.write({'state': 'cancel'})

    def action_set_draft(self):
        self.write({'state': 'draft'})

    def action_view_pickings(self):
        self.ensure_one()
        return {
            'name': 'Transferencias de Stock',
            'type': 'ir.actions.act_window',
            'res_model': 'stock.picking',
            'view_mode': 'list,form',
            'domain': [('id', 'in', self.picking_ids.ids)],
        }

    def action_create_sale_order(self):
        self.ensure_one()
        rollos_pendientes = self.rollo_ids.filtered(lambda r: r.state == 'pending')
        if not rollos_pendientes:
            raise UserError('No hay rollos pendientes de facturar.')

        product = self.env.ref('bonanza_textil.product_servicio_maquila', raise_if_not_found=False)
        if not product:
            raise UserError('No se encontró el producto de servicio de maquila configurado.')

        order = self.env['sale.order'].create({
            'partner_id': self.partner_id.id,
            'origin': self.name,
        })
        for rollo in rollos_pendientes:
            line = self.env['sale.order.line'].create({
                'order_id': order.id,
                'product_id': product.id,
                'name': '%s - %s' % (self.name, rollo.name),
                'product_uom_qty': rollo.peso_kg,
            })
            rollo.write({'sale_order_line_id': line.id, 'state': 'invoiced'})

        return {
            'name': 'Orden de Venta',
            'type': 'ir.actions.act_window',
            'res_model': 'sale.order',
            'view_mode': 'form',
            'res_id': order.id,
        }
