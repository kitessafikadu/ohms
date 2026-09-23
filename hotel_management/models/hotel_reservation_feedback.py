from odoo import fields, models


class HotelReservationFeedback(models.Model):
    _name = 'hotel.reservation.feedback'
    _description = 'Guest Feedback'
    _order = 'create_date desc'

    reservation_id = fields.Many2one(
        'hotel.reservation', required=True, ondelete='cascade',
    )
    guest_id = fields.Many2one(
        related='reservation_id.guest_id', store=True,
    )
    room_id = fields.Many2one(
        related='reservation_id.room_id', store=True,
    )
    rating = fields.Integer(required=True)
    comments = fields.Text()
    response = fields.Text(
        string='Hotel Response',
        help='Front-desk or manager reply.',
    )
    responded_by = fields.Many2one('res.users')
    responded_on = fields.Datetime()