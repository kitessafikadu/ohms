from odoo import fields, models


class AccountMove(models.Model):
    _inherit = 'account.move'

    hotel_reservation_id = fields.Many2one(
        'hotel.reservation',
        string='Hotel Reservation',
        ondelete='set null',
        index=True,
        copy=False,
    )
    corporate_account_id = fields.Many2one(
        'hotel.corporate.account',
        string='Corporate Account',
        ondelete='set null',
        index=True,
        copy=False,
    )