from datetime import date

from odoo import api, fields, models


class HotelReservationGuest(models.Model):
    _name = 'hotel.reservation.guest'
    _description = 'Companion on a Reservation'
    _rec_name = 'name'

    reservation_id = fields.Many2one(
        'hotel.reservation', required=True, ondelete='cascade',
    )
    name = fields.Char(string='Full Name (as on ID)', required=True)
    relationship = fields.Char(help='e.g. Spouse, Child, Colleague')

    id_type = fields.Selection(
        [('passport', 'Passport'),
         ('national_id', 'National ID'),
         ('driver_license', "Driver's License"),
         ('none', 'None')],
        default='national_id', required=True,
    )
    id_number = fields.Char()
    id_expiry = fields.Date()

    dob = fields.Date(string='Date of Birth')
    age = fields.Integer(compute='_compute_age', store=True)
    is_adult = fields.Boolean(compute='_compute_age', store=True)

    @api.depends('dob')
    def _compute_age(self):
        today = date.today()
        for rec in self:
            if rec.dob:
                age = today.year - rec.dob.year - (
                    (today.month, today.day) < (rec.dob.month, rec.dob.day)
                )
                rec.age = age
                rec.is_adult = age >= 18
            else:
                rec.age = 0
                rec.is_adult = True