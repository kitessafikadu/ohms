from odoo import api, fields, models
from odoo.exceptions import ValidationError


class HotelRoomService(models.Model):
    _name = 'hotel.room.service'
    _description = 'Food & Beverage Catalogue / Package'
    _order = 'service_type, sequence, name'

    name = fields.Char(required=True, translate=True)
    code = fields.Char(required=True)
    sequence = fields.Integer(default=10)

    service_type = fields.Selection(
        [('food_beverage', 'Food & Beverage'),
         ('package', 'Package')],
        required=True, default='food_beverage',
    )

    unit_price = fields.Monetary(currency_field='currency_id')
    currency_id = fields.Many2one(
        'res.currency',
        default=lambda self: self.env.company.currency_id,
    )
    description = fields.Text(translate=True)
    active = fields.Boolean(default=True)

    image_1920 = fields.Image()
    image_128 = fields.Image(related='image_1920', max_width=128,
                             max_height=128, store=True)

    package_line_ids = fields.One2many(
        'hotel.room.service.package.line', 'package_id',
        string='Package Contents',
    )

    _sql_constraints = [
        ('code_unique', 'UNIQUE(code)', 'Service code must be unique.'),
        ('price_positive', 'CHECK(unit_price >= 0)',
         'Price must be zero or positive.'),
    ]

    @api.constrains('service_type', 'package_line_ids')
    def _check_package_has_content(self):
        for rec in self:
            if rec.service_type == 'package' and not rec.package_line_ids:
                raise ValidationError(
                    f'Package "{rec.name}" must contain at least one item.'
                )


class HotelRoomServicePackageLine(models.Model):
    _name = 'hotel.room.service.package.line'
    _description = 'Package Content Line'

    package_id = fields.Many2one(
        'hotel.room.service', required=True, ondelete='cascade',
        domain="[('service_type', '=', 'package')]",
    )
    service_id = fields.Many2one(
        'hotel.room.service', required=True,
        domain="[('service_type', '=', 'food_beverage'), ('active', '=', True)]",
        string='Item',
    )
    quantity = fields.Float(default=1.0, required=True)

    _sql_constraints = [
        ('qty_positive', 'CHECK(quantity > 0)',
         'Quantity must be greater than zero.'),
    ]