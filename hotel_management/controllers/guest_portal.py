from odoo import http
from odoo.http import request


class HotelGuestPortal(http.Controller):

    def _my_reservations(self):
        """Reservations for the currently logged-in user's partner.

        Runs with sudo because a plain portal user doesn't have
        explicit ACL on hotel.reservation. The partner filter below
        enforces the security boundary at the query level, so the
        user only sees their own bookings.
        """
        partner = request.env.user.partner_id
        if not partner:
            return request.env['hotel.reservation'].browse()
        return request.env['hotel.reservation'].sudo().search([
            ('guest_id', '=', partner.id),
        ])

    def _my_reservation(self, reservation_id):
        """The reservation with the given id, if it belongs to the user."""
        return self._my_reservations().filtered(
            lambda r: r.id == reservation_id)

    @http.route('/my/reservations', type='http', auth='user', website=True)
    def my_reservations(self, **kw):
        return request.render(
            'hotel_management.portal_my_reservations', {
                'reservations': self._my_reservations(),
            })

    @http.route('/my/reservations/<int:reservation_id>',
                type='http', auth='user', website=True)
    def reservation_detail(self, reservation_id, **kw):
        rec = self._my_reservation(reservation_id)
        if not rec:
            return request.not_found()
        catalogue = request.env['hotel.room.service'].sudo().search([
            ('service_type', '=', 'food_beverage'),
            ('active', '=', True),
        ])
        return request.render(
            'hotel_management.portal_reservation_detail', {
                'reservation': rec,
                'catalogue': catalogue,
                'error': kw.get('error'),
            })

    @http.route('/my/reservations/<int:reservation_id>/order',
                type='http', auth='user', website=True,
                methods=['POST'], csrf=True)
    def place_order(self, reservation_id, **post):
        rec = self._my_reservation(reservation_id)
        if not rec or rec.state != 'checked_in':
            return request.redirect('/my/reservations')
        try:
            request.env['hotel.room.service.order'].sudo().create({
                'reservation_id': rec.id,
                'source': 'ad_hoc',
                'service_id': int(post.get('service_id')),
                'quantity': float(post.get('quantity') or 1),
                'description': post.get('description') or '',
                'state': 'draft',
            })
        except Exception as e:
            request.env.cr.rollback()
            return request.redirect(
                f'/my/reservations/{reservation_id}?error={e}')
        return request.redirect(f'/my/reservations/{reservation_id}')

    @http.route('/my/reservations/<int:reservation_id>/feedback',
                type='http', auth='user', website=True,
                methods=['POST'], csrf=True)
    def submit_feedback(self, reservation_id, **post):
        rec = self._my_reservation(reservation_id)
        if not rec:
            return request.not_found()
        request.env['hotel.reservation.feedback'].sudo().create({
            'reservation_id': rec.id,
            'rating': int(post.get('rating') or 5),
            'comments': post.get('comments'),
        })
        return request.redirect(f'/my/reservations/{reservation_id}')