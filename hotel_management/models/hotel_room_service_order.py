from odoo import api, fields, models
from odoo.exceptions import UserError


class HotelRoomServiceOrder(models.Model):
    _name = 'hotel.room.service.order'
    _description = 'Room Service Order'
    _inherit = ['mail.thread', 'mail.activity.mixin']
    _order = 'order_date desc, id desc'

    name = fields.Char(
        default=lambda self: self.env['ir.sequence'].next_by_code(
            'hotel.room.service.order') or 'New',
        readonly=True, copy=False,
    )

    reservation_id = fields.Many2one(
        'hotel.reservation', required=True, ondelete='cascade',
        domain="[('state', '=', 'checked_in')]",
    )
    room_id = fields.Many2one(
        related='reservation_id.room_id', store=True, readonly=True,
    )
    guest_name = fields.Char(
        related='reservation_id.guest_name', readonly=True,
    )

    source = fields.Selection(
        [('ad_hoc', 'Additional (Chargeable)'),
         ('package', 'From Package')],
        default='ad_hoc', required=True, tracking=True,
    )

    service_id = fields.Many2one(
        'hotel.room.service', string='Item',
        domain="[('active', '=', True), ('service_type', '=', 'food_beverage')]",
    )
    entitlement_id = fields.Many2one(
        'hotel.reservation.package.entitlement', string='Package Item',
    )
    quantity = fields.Float(default=1.0, required=True)
    unit_price = fields.Monetary(currency_field='currency_id')
    amount = fields.Monetary(
        compute='_compute_amount', store=True, readonly=False,
        currency_field='currency_id',
    )
    currency_id = fields.Many2one(
        'res.currency',
        default=lambda self: self.env.company.currency_id,
    )

    description = fields.Text()
    order_date = fields.Datetime(default=fields.Datetime.now, required=True)
    delivered_date = fields.Datetime()
    server_id = fields.Many2one(
        'res.users', string='Served By',
        default=lambda self: self.env.user, required=True,
    )
    state = fields.Selection(
        [('draft', 'Draft'), ('preparing', 'Preparing'),
         ('delivered', 'Delivered'), ('cancelled', 'Cancelled')],
        default='draft', tracking=True,
    )
    posted_to_reservation = fields.Boolean(
        'Charged to Reservation', default=False, readonly=True, copy=False,
    )

    @api.depends('source', 'quantity', 'unit_price')
    def _compute_amount(self):
        for rec in self:
            if rec.source == 'package':
                rec.amount = 0.0
            else:
                rec.amount = (rec.quantity or 0.0) * (rec.unit_price or 0.0)

    @api.onchange('service_id')
    def _onchange_service_id(self):
        if self.service_id:
            self.unit_price = self.service_id.unit_price
            if not self.description:
                self.description = self.service_id.description or self.service_id.name

    def action_preparing(self):
        for rec in self:
            if rec.state != 'draft':
                raise UserError('Only draft orders can move to Preparing.')
            rec.state = 'preparing'

    def action_deliver(self):
        for rec in self:
            if rec.state not in ('draft', 'preparing'):
                raise UserError('Only draft or preparing orders can be delivered.')
            if rec.reservation_id.state != 'checked_in':
                raise UserError('Guest must be checked in.')
            if rec.source == 'ad_hoc':
                if rec.amount > 0 and not rec.posted_to_reservation:
                    rec.reservation_id.sudo().write({
                        'extra_charges':
                            rec.reservation_id.extra_charges + rec.amount,
                    })
                    rec.posted_to_reservation = True
            else:
                if rec.entitlement_id:
                    rec.entitlement_id.consume(rec.quantity)
            rec.state = 'delivered'
            rec.delivered_date = fields.Datetime.now()

    def action_cancel(self):
        for rec in self:
            if rec.state == 'delivered':
                if not self.env.user.has_group(
                        'hotel_management.group_hotel_manager'):
                    raise UserError('Only managers can cancel delivered orders.')
            rec.state = 'cancelled'