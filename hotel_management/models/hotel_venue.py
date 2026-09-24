from odoo import api, fields, models
from odoo.exceptions import ValidationError

class HotelVenue(models.Model):
    _name = 'hotel.venue'
    _description = 'Hotel Venue'
    _order = 'sequence, name'

    name = fields.Char(required=True)
    code = fields.Char(required=True)
    sequence = fields.Integer(default=10)
    active = fields.Boolean(default=True)

    capacity_seated = fields.Integer(string='Seated Capacity')
    capacity_standing = fields.Integer(string='Standing Capacity')

    rate_hourly = fields.Monetary(currency_field='currency_id')
    rate_half_day = fields.Monetary(currency_field='currency_id')
    rate_full_day = fields.Monetary(currency_field='currency_id')
    currency_id = fields.Many2one(
        'res.currency',
        default=lambda self: self.env.company.currency_id,
    )

    setup_minutes = fields.Integer(
        default=60, help='Minutes needed to set up before an event.')
    teardown_minutes = fields.Integer(
        default=30, help='Minutes needed to tear down after an event.')

    has_av = fields.Boolean(string='Audio/Visual')
    has_stage = fields.Boolean()
    has_dance_floor = fields.Boolean()
    has_outdoor_space = fields.Boolean()
    has_kitchen = fields.Boolean(string='Adjacent Kitchen')

    image_1920 = fields.Image()
    image_128 = fields.Image(
        related='image_1920', max_width=128, max_height=128, store=True,
    )

    notes = fields.Text()

    event_ids = fields.One2many('hotel.event', 'venue_id')
    event_count = fields.Integer(compute='_compute_event_count')

    _sql_constraints = [
        ('code_unique', 'UNIQUE(code)', 'Venue code must be unique.'),
    ]

    @api.depends('event_ids')
    def _compute_event_count(self):
        for rec in self:
            rec.event_count = len(rec.event_ids)