from odoo import fields, models

class AccountMove(models.Model):
    _inherit = 'account.move'

    hotel_reservation_id = fields.Many2one(
        'hotel.reservation',
        string='Hotel Reservation',
        ondelete='set null',
        index=True,
        copy=False,
        help='Reservation this invoice or credit note was generated for.',
    )