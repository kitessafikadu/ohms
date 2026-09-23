from odoo import api, fields, models
from odoo.exceptions import ValidationError


class HotelRoomCategory(models.Model):
    _name = 'hotel.room.category'
    _description = 'Hotel Room Category (Room Type)'
    _order = 'sequence, name'

    name = fields.Char(required=True, translate=True)
    code = fields.Char(required=True)
    sequence = fields.Integer(default=10)
    active = fields.Boolean(default=True)

    capacity_adults = fields.Integer(default=2, required=True)
    capacity_children = fields.Integer(default=0)
    bed_configuration = fields.Selection(
        [('single', 'Single'),
         ('twin', 'Twin'),
         ('queen', 'Queen'),
         ('king', 'King'),
         ('sofa_bed', 'Sofa Bed'),
         ('multi', 'Multi-bed')],
        default='queen',
        required=True,
    )

    target_audience = fields.Char(
        help='Who is this room designed for? e.g. "Business travelers, couples".',
    )
    core_features = fields.Html(
        help='Rich text description of what is included in this room type.',
    )
    is_accessible = fields.Boolean(
        'Wheelchair Accessible',
        help='Room can be assigned to guests with mobility needs.',
    )

    default_rate = fields.Monetary(currency_field='currency_id')
    currency_id = fields.Many2one(
        'res.currency',
        default=lambda self: self.env.company.currency_id,
    )

    room_ids = fields.One2many('hotel.room', 'category_id')
    room_count = fields.Integer(compute='_compute_room_count')
    package_ids = fields.Many2many(
        'hotel.room.service',
        'hotel_category_package_rel', 'category_id', 'service_id',
        domain="[('service_type', '=', 'package')]",
        string='Available Packages',
    )

    image_1920 = fields.Image()
    image_128 = fields.Image(related='image_1920', max_width=128,
                             max_height=128, store=True)

    _sql_constraints = [
        ('code_unique', 'UNIQUE(code)', 'Category code must be unique.'),
        ('capacity_positive',
         'CHECK(capacity_adults >= 1 AND capacity_children >= 0)',
         'Adult capacity must be at least 1 and child capacity 0 or more.'),
    ]

    @api.depends('room_ids')
    def _compute_room_count(self):
        for rec in self:
            rec.room_count = len(rec.room_ids)