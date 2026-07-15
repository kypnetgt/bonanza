from odoo import Command, api, fields, models
from odoo.exceptions import UserError


class TextilFabricacion(models.Model):
    _name = 'textil.fabricacion'
    _description = 'Fabricación de Tela'
    _inherit = ['mail.thread', 'mail.activity.mixin']
    _order = 'fecha desc, id desc'

    name = fields.Char(string='Referencia', required=True, copy=False,
                        default=lambda self: 'Nuevo', readonly=True)
    partner_id = fields.Many2one(
        'res.partner', string='Cliente', required=True, tracking=True)
    tipo_tela_id = fields.Many2one('textil.tipo.tela', string='Tipo de Tela', required=True)
    tipo_hilo_id = fields.Many2one('textil.tipo.hilo', string='Tipo de Hilo', required=True)
    calibre_id = fields.Many2one('textil.calibre', string='Calibre', required=True)
    porcentaje_mezcla_id = fields.Many2one('textil.porcentaje.mezcla', string='% Mezcla')
    agujado_id = fields.Many2one('textil.agujado', string='Agujado')
    medida_id = fields.Many2one('textil.medida', string='Loop / Medida')
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
    picking_ids = fields.One2many('stock.picking', 'fabricacion_id', string='Transferencias de Stock')
    picking_count = fields.Integer(compute='_compute_picking_count', string='N° Transferencias')

    hilo_lot_ids = fields.Many2many(
        'stock.lot', compute='_compute_hilo_lot_ids', string='Conos de Hilo Cargados')
    lotes_cliente_ids = fields.Many2many(
        'stock.lot', compute='_compute_lotes_cliente_ids', string='Conos Disponibles del Cliente')
    peso_rollo_kg = fields.Float(string='Peso por Rollo (kg)', default=20.0)

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

    @api.depends('line_ids.lot_id')
    def _compute_hilo_lot_ids(self):
        for record in self:
            record.hilo_lot_ids = record.line_ids.lot_id

    @api.depends('partner_id')
    def _compute_lotes_cliente_ids(self):
        Quant = self.env['stock.quant']
        for record in self:
            if not record.partner_id:
                record.lotes_cliente_ids = False
                continue
            commercial_partner = record.partner_id.commercial_partner_id
            quants = Quant.search([
                ('lot_id', '!=', False),
                ('quantity', '>', 0),
                '|', ('owner_id', '=', False), ('owner_id.commercial_partner_id', '=', commercial_partner.id),
            ])
            record.lotes_cliente_ids = quants.lot_id

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

        self_sudo = self.sudo()
        picking_type = self_sudo.env['stock.picking.type'].search([
            ('code', '=', 'internal'),
            ('warehouse_id.company_id', '=', self.company_id.id),
        ], limit=1)
        if not picking_type:
            raise UserError('No se encontró un tipo de operación interna de inventario para la compañía actual.')

        dest_location = picking_type.default_location_dest_id or self_sudo.env.ref('stock.stock_location_stock')

        picking = self_sudo.env['stock.picking'].create({
            'picking_type_id': picking_type.id,
            'partner_id': self.partner_id.id,
            'origin': self.name,
            'fabricacion_id': self.id,
            'location_id': picking_type.default_location_src_id.id,
            'location_dest_id': dest_location.id,
        })

        lines_to_process = self.line_ids.filtered(lambda l: l.state == 'draft')
        for line in lines_to_process:
            quant = self_sudo.env['stock.quant'].search([
                ('product_id', '=', line.product_id.id),
                ('lot_id', '=', line.lot_id.id),
                ('location_id', '=', line.location_id.id),
            ], limit=1, order='quantity desc')
            owner_id = quant.owner_id.id if quant else False
            move = self_sudo.env['stock.move'].create({
                'product_id': line.product_id.id,
                'product_uom_qty': line.cantidad,
                'product_uom': line.product_id.uom_id.id,
                'picking_id': picking.id,
                'location_id': line.location_id.id,
                'location_dest_id': dest_location.id,
                'lot_ids': [Command.set([line.lot_id.id])],
                'restrict_partner_id': owner_id,
            })
            line.move_id = move.id

        picking.action_confirm()
        picking.action_assign()

        self.state = 'confirmed'

    def action_done(self):
        for record in self:
            record._reconciliar_rollos()
            total_producido = sum(record.maquina_produccion_ids.mapped('kg_hechos'))
            kg_en_rollos = sum(record.rollo_ids.filtered(
                lambda r: r.origen in ('auto', 'cierre')).mapped('peso_kg'))
            remanente = total_producido - kg_en_rollos
            if remanente > 0.001:
                record._crear_rollo(remanente, origen='cierre')
        self.write({'state': 'done'})

    def _reconciliar_rollos(self):
        for record in self:
            if record.peso_rollo_kg <= 0:
                continue
            total_producido = sum(record.maquina_produccion_ids.mapped('kg_hechos'))
            kg_en_rollos = sum(record.rollo_ids.filtered(
                lambda r: r.origen in ('auto', 'cierre')).mapped('peso_kg'))
            kg_restante = total_producido - kg_en_rollos
            nuevos_completos = int(kg_restante // record.peso_rollo_kg)
            for _ in range(nuevos_completos):
                record._crear_rollo(record.peso_rollo_kg, origen='auto')

    def _get_tela_product(self):
        product = self.env.ref('bonanza_textil.product_tela_terminada', raise_if_not_found=False)
        if not product:
            raise UserError('No se encontró el producto de tela terminada configurado.')
        return product

    def _get_ubicacion_tela_terminada(self):
        self.ensure_one()
        Location = self.env['stock.location']
        warehouse = self.env['stock.warehouse'].search(
            [('company_id', '=', self.company_id.id)], limit=1)
        location = Location.search([
            ('name', '=', 'Tela Terminada'),
            ('location_id', '=', warehouse.view_location_id.id),
        ], limit=1)
        if not location:
            location = Location.create({
                'name': 'Tela Terminada',
                'location_id': warehouse.view_location_id.id,
                'usage': 'internal',
            })
        return location

    def _crear_rollo(self, peso, origen='auto'):
        self.ensure_one()
        self_sudo = self.sudo()
        product = self_sudo._get_tela_product()
        seq = len(self_sudo.rollo_ids) + 1
        lot = self_sudo.env['stock.lot'].create({
            'name': '%s-R%03d' % (self.name, seq),
            'product_id': product.id,
            'company_id': self.company_id.id,
        })
        rollo = self_sudo.env['textil.rollo'].create({
            'fabricacion_id': self.id,
            'peso_kg': peso,
            'lot_id': lot.id,
            'origen': origen,
        })
        rollo._generar_entrada_stock()
        return rollo

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
