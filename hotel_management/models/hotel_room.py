from odoo import api, fields, models


class HotelRoom(models.Model):
    _name = 'hotel.room'
    _description = 'Hotel Room'
    _inherit = ['mail.thread']

    name = fields.Char(compute='_compute_name', store=True)
    room_number = fields.Char(required=True)
    floor = fields.Integer()
    category_id = fields.Many2one(
        'hotel.room.category', required=True, ondelete='restrict',
    )
    bed_configuration = fields.Selection(
        related='category_id.bed_configuration', store=True, readonly=True,
    )
    view_type = fields.Selection(
        [('none', 'No View'),
         ('garden', 'Garden'),
         ('city', 'City'),
         ('ocean', 'Ocean'),
         ('pool', 'Pool')],
        default='none',
    )
    is_accessible = fields.Boolean(related='category_id.is_accessible',
                                   store=True, readonly=True)

    rate = fields.Monetary(currency_field='currency_id')
    currency_id = fields.Many2one(
        'res.currency',
        default=lambda self: self.env.company.currency_id,
    )

    housekeeping_state = fields.Selection(
        [('clean', 'Clean'),
         ('dirty', 'Dirty'),
         ('cleaning', 'Cleaning')],
        default='clean',
        tracking=True,
    )
    maintenance_hold = fields.Boolean(
        help='When set, the room cannot be reserved.',
    )
    maintenance_note = fields.Char()

    reservation_ids = fields.One2many('hotel.reservation', 'room_id')

    is_available_now = fields.Boolean(
        compute='_compute_is_available_now',
        search='_search_is_available_now',
    )
    next_arrival_date = fields.Date(
        compute='_compute_next_arrival_date',
        help='Date of the next confirmed check-in. Used at peak times.',
    )

    _sql_constraints = [
        ('room_number_unique', 'UNIQUE(room_number)',
         'Room number must be unique.'),
    ]

    @api.depends('room_number', 'category_id')
    def _compute_name(self):
        for rec in self:
            rec.name = f"{rec.room_number} - {rec.category_id.name or ''}".strip(' -')

    @api.depends('reservation_ids.state', 'reservation_ids.check_in_date',
                 'reservation_ids.check_out_date', 'maintenance_hold')
    def _compute_is_available_now(self):
        today = fields.Date.context_today(self)
        for rec in self:
            if rec.maintenance_hold:
                rec.is_available_now = False
                continue
            busy = rec.reservation_ids.filtered(
                lambda r: r.state in ('confirmed', 'checked_in')
                and r.check_in_date <= today < r.check_out_date
            )
            rec.is_available_now = not busy

    def _search_is_available_now(self, operator, value):
        """Search method for the non-stored is_available_now field.

        Translates a filter on the compute field into a real SQL-searchable
        domain based on maintenance_hold and overlapping reservations.
        """
        today = fields.Date.context_today(self)

        # Rooms that have an active reservation covering today
        busy_room_ids = self.env['hotel.reservation'].search([
            ('state', 'in', ('confirmed', 'checked_in')),
            ('check_in_date', '<=', today),
            ('check_out_date', '>', today),
        ]).mapped('room_id').ids

        # True = available → not on hold AND not busy
        if (operator == '=' and value) or (operator == '!=' and not value):
            return [
                ('maintenance_hold', '=', False),
                ('id', 'not in', busy_room_ids),
            ]

        # False = unavailable → on hold OR busy
        return [
            '|',
            ('maintenance_hold', '=', True),
            ('id', 'in', busy_room_ids),
        ]

    @api.depends('reservation_ids.state', 'reservation_ids.check_in_date')
    def _compute_next_arrival_date(self):
        today = fields.Date.context_today(self)
        for rec in self:
            future = rec.reservation_ids.filtered(
                lambda r: r.state == 'confirmed' and r.check_in_date >= today
            ).sorted('check_in_date')
            rec.next_arrival_date = future[:1].check_in_date or False