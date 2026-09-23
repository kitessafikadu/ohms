from odoo import fields, models


class ResPartner(models.Model):
    _inherit = 'res.partner'

    hotel_id_type = fields.Selection(
        [('passport', 'Passport'),
         ('national_id', 'National ID'),
         ('driver_license', "Driver's License"),
         ('other', 'Other')],
        string='Hotel ID Type',
    )
    hotel_id_number = fields.Char(string='Hotel ID Number')
    hotel_id_expiry = fields.Date(string='Hotel ID Expiry')
    hotel_dob = fields.Date(string='Date of Birth')
    hotel_reservation_ids = fields.One2many(
        'hotel.reservation', 'guest_id',
        string='Hotel Reservations',
    )