from odoo import api, fields, models
from odoo.exceptions import UserError


class HotelReservationPackage(models.Model):
    _name = 'hotel.reservation.package'
    _description = 'Package Booked on a Reservation'
    _rec_name = 'package_id'

    reservation_id = fields.Many2one(
        'hotel.reservation', required=True, ondelete='cascade',
    )
    package_id = fields.Many2one(
        'hotel.room.service', required=True,
        domain="[('service_type', '=', 'package'), ('active', '=', True)]",
    )
    price = fields.Monetary(
        currency_field='currency_id',
        help='Price snapshot at booking time. Added to the reservation total '
             'but NOT to extra_charges — it is part of the room deal.',
    )
    currency_id = fields.Many2one(
        'res.currency', related='reservation_id.currency_id', store=True,
    )

    entitlement_ids = fields.One2many(
        'hotel.reservation.package.entitlement', 'reservation_package_id',
        string='Included Items',
    )

    @api.model_create_multi
    def create(self, vals_list):
        packages = super().create(vals_list)
        for pkg in packages:
            pkg._build_entitlements()
        return packages

    def _build_entitlements(self):
        """Snapshot the package's contents into entitlements for this stay."""
        self.ensure_one()
        self.entitlement_ids.unlink()
        for line in self.package_id.package_line_ids:
            self.env['hotel.reservation.package.entitlement'].create({
                'reservation_package_id': self.id,
                'service_id': line.service_id.id,
                'qty_included': line.quantity,
            })


class HotelReservationPackageEntitlement(models.Model):
    _name = 'hotel.reservation.package.entitlement'
    _description = 'F&B Item Included in a Package'
    _rec_name = 'service_id'

    reservation_package_id = fields.Many2one(
        'hotel.reservation.package', required=True, ondelete='cascade',
    )
    reservation_id = fields.Many2one(
        related='reservation_package_id.reservation_id',
        store=True, readonly=True,
    )
    service_id = fields.Many2one(
        'hotel.room.service', required=True,
        domain="[('service_type', '=', 'food_beverage')]",
    )

    qty_included = fields.Float(required=True)
    qty_used = fields.Float(default=0.0, readonly=True)
    qty_remaining = fields.Float(
        compute='_compute_qty_remaining', store=True,
    )

    @api.depends('qty_included', 'qty_used')
    def _compute_qty_remaining(self):
        for rec in self:
            rec.qty_remaining = max(0.0, rec.qty_included - rec.qty_used)

    def consume(self, quantity):
        """Called by an order when delivered. Raises if oversubscribed."""
        self.ensure_one()
        if quantity > self.qty_remaining:
            raise UserError(
                f"Only {self.qty_remaining} x {self.service_id.name} "
                f"remaining on this package."
            )
        self.qty_used += quantity