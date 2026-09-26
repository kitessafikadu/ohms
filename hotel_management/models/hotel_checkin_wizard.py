from odoo import api, fields, models
from odoo.exceptions import ValidationError


class HotelCheckinWizard(models.TransientModel):
    _name = 'hotel.checkin.wizard'
    _description = 'Guest Check-In Verification'

    reservation_id = fields.Many2one(
        'hotel.reservation', required=True, ondelete='cascade',
    )

    guest_name = fields.Char(
        related='reservation_id.guest_name', readonly=True)
    guest_id_type = fields.Selection(
        related='reservation_id.guest_id_type', readonly=True)
    guest_id_number = fields.Char(
        related='reservation_id.guest_id_number', readonly=True)
    guest_id_expiry = fields.Date(
        related='reservation_id.guest_id_expiry', readonly=True)
    guest_dob = fields.Date(
        related='reservation_id.guest_dob', readonly=True)
    guest_age = fields.Integer(
        related='reservation_id.guest_age', readonly=True)
    guest_id_scan_front = fields.Binary(
        related='reservation_id.guest_id_scan_front', readonly=True)
    guest_id_scan_back = fields.Binary(
        related='reservation_id.guest_id_scan_back', readonly=True)
    room_id = fields.Many2one(
        related='reservation_id.room_id', readonly=True)

    is_expired = fields.Boolean(compute='_compute_warnings')
    is_underage = fields.Boolean(compute='_compute_warnings')
    has_scan = fields.Boolean(compute='_compute_warnings')

    id_matches_guest = fields.Boolean(
        'ID photo matches the guest in person')
    id_not_expired = fields.Boolean(
        'ID document is not expired')
    age_verified = fields.Boolean(
        'Guest is confirmed to be of legal age (18+)')

    notes = fields.Text(
        'Notes',
        help='Any discrepancy noticed during verification.',
    )

    @api.depends('guest_id_expiry', 'guest_age',
                 'guest_id_scan_front', 'guest_id_scan_back')
    def _compute_warnings(self):
        today = fields.Date.context_today(self)
        for rec in self:
            rec.is_expired = bool(
                rec.guest_id_expiry and rec.guest_id_expiry < today)
            rec.is_underage = bool(
                rec.guest_age and rec.guest_age < 18)
            rec.has_scan = bool(
                rec.guest_id_scan_front or rec.guest_id_scan_back)

    def action_confirm_checkin(self):
        self.ensure_one()

        errors = {}
        if not self.id_matches_guest:
            errors['id_matches_guest'] = (
                'Please confirm the ID photo matches the guest.'
            )
        if not self.id_not_expired:
            errors['id_not_expired'] = (
                'Please confirm the ID is not expired.'
            )
        if not self.age_verified:
            errors['age_verified'] = (
                'Please confirm the guest is of legal age.'
            )

        if errors:
            raise ValidationError(errors)

        reservation = self.reservation_id
        reservation.write({
            'state': 'checked_in',
            'id_verified_by': self.env.user.id,
            'id_verified_on': fields.Datetime.now(),
            'id_verification_notes': self.notes,
        })
        reservation.room_id.housekeeping_state = 'dirty'

        return {'type': 'ir.actions.act_window_close'}