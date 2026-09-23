import base64
import re
from datetime import date

from odoo import http
from odoo.http import request


# ------------------------------------------------------------------
# Validation helpers
# ------------------------------------------------------------------
NAME_RE = re.compile(r"^[A-Za-z][A-Za-z'\-]*(?:\s+[A-Za-z][A-Za-z'\-]*)+$")
EMAIL_RE = re.compile(r"^[^@\s]+@[^@\s]+\.[A-Za-z]{2,}$")
ID_RE = re.compile(r"^[A-Za-z0-9\- ]{4,32}$")
PHONE_RE = re.compile(r"^(?:\+?\d{1,4}[\s\-]?)?\d{6,12}$")

MAX_ID_SCAN_SIZE = 5 * 1024 * 1024        # 5 MB
ALLOWED_ID_SCAN_EXT = ('.jpg', '.jpeg', '.png', '.pdf')


def _clean(value):
    return (value or "").strip()


def _normalize_phone(phone):
    return re.sub(r"[\s\-()]+", "", phone or "")


def _validate_booking(post, has_id_scan=False):
    """Return a list of error strings. Empty list = valid."""
    errors = []

    # Full name
    name = _clean(post.get("guest_name"))
    if not name:
        errors.append("Full name is required.")
    elif not NAME_RE.match(name):
        errors.append(
            "Please enter your full name as on your ID "
            "(first name and last name, letters only)."
        )

    # Email
    email = _clean(post.get("email") or post.get("guest_email"))
    if not email:
        errors.append("Email is required.")
    elif not EMAIL_RE.match(email):
        errors.append("Please enter a valid email address.")

    # Phone
    phone = _normalize_phone(post.get("phone") or post.get("guest_phone"))
    if not phone:
        errors.append("Phone number is required.")
    else:
        digits = re.sub(r"[^\d]", "", phone)
        if phone.startswith("+"):
            if not (9 <= len(digits) <= 15):
                errors.append(
                    "Phone with country code must have 9 to 15 digits "
                    "(e.g. +251912345678)."
                )
        else:
            if len(digits) not in (10, 13):
                errors.append(
                    "Phone must be 10 digits (e.g. 0912345678) "
                    "or 13 digits with country code (e.g. 251912345678)."
                )

    # ID number
    id_number = _clean(post.get("guest_id_number"))
    if not id_number:
        errors.append("ID number is required.")
    elif not ID_RE.match(id_number):
        errors.append(
            "ID number must be 4 to 32 characters "
            "(letters, digits, hyphens or spaces)."
        )

    # DOB + age
    dob_str = _clean(post.get("guest_dob"))
    if not dob_str:
        errors.append("Date of birth is required.")
    else:
        try:
            dob = date.fromisoformat(dob_str)
            today = date.today()
            age = today.year - dob.year - (
                (today.month, today.day) < (dob.month, dob.day)
            )
            if age < 18:
                errors.append("Primary guest must be at least 18 years old.")
            if dob > today:
                errors.append("Date of birth cannot be in the future.")
        except ValueError:
            errors.append("Invalid date of birth format.")

    # Check-in / check-out
    check_in = _clean(post.get("check_in_date"))
    check_out = _clean(post.get("check_out_date"))

    try:
        ci = date.fromisoformat(check_in) if check_in else None
        co = date.fromisoformat(check_out) if check_out else None
    except ValueError:
        errors.append("Invalid check-in or check-out date format.")
        ci = co = None

    if not check_in:
        errors.append("Check-in date is required.")
    elif ci and ci < date.today():
        errors.append("Check-in date cannot be in the past.")

    if not check_out:
        errors.append("Check-out date is required.")
    elif co and ci and co <= ci:
        errors.append("Check-out must be after check-in.")

    # Adults / children
    try:
        adults = int(post.get("adults") or 0)
        children = int(post.get("children") or 0)
    except (TypeError, ValueError):
        errors.append("Adults and children must be numbers.")
        adults = children = 0

    if adults < 1:
        errors.append("At least one adult is required.")
    if children < 0:
        errors.append("Children count cannot be negative.")

    # Room
    if not post.get("room_id"):
        errors.append("Please select a room.")

    return errors


# ------------------------------------------------------------------
# Controller
# ------------------------------------------------------------------
class HotelPublicBooking(http.Controller):

    @http.route('/hotel/book', type='http', auth='public', website=True)
    def booking_form(self, **kw):
        today = date.today()
        categories = request.env['hotel.room.category'].sudo().search(
            [('active', '=', True)])
        return request.render('hotel_management.public_booking_form', {
            'categories': categories,
            'min_check_in': today.isoformat(),
            'min_check_out': today.isoformat(),
            'error': kw.get('error'),
        })

    @http.route('/hotel/rooms/<int:category_id>', type='http',
                auth='public', website=True)
    def rooms_by_category(self, category_id, **kw):
        Room = request.env['hotel.room'].sudo()
        rooms = Room.search([
            ('category_id', '=', category_id),
            ('maintenance_hold', '=', False),
        ])
        return request.make_json_response([
            {'id': r.id, 'name': r.name, 'rate': r.rate}
            for r in rooms
        ])

    @http.route('/hotel/book/submit', type='http', auth='public',
            website=True, methods=['POST'], csrf=True)
    def booking_submit(self, **post):
        # -------- Read the uploaded ID scan
        guest_id_scan_b64 = False
        guest_id_scan_filename = False

        uploaded_file = request.httprequest.files.get('guest_id_scan')
        if uploaded_file and uploaded_file.filename:
            filename = uploaded_file.filename
            file_data = uploaded_file.read()

            if len(file_data) > MAX_ID_SCAN_SIZE:
                return request.redirect(
                    '/hotel/book?error=' +
                    'ID scan must be smaller than 5 MB.')

            if not filename.lower().endswith(ALLOWED_ID_SCAN_EXT):
                return request.redirect(
                    '/hotel/book?error=' +
                    'ID scan must be a JPG, PNG, or PDF file.')

            guest_id_scan_b64 = base64.b64encode(file_data)
            guest_id_scan_filename = filename

        # -------- Text-field validation
        errors = _validate_booking(post)
        if errors:
            return request.redirect(
                '/hotel/book?error=' + ' | '.join(errors))

        # -------- Create reservation
        try:
            Partner = request.env['res.partner'].sudo()
            guest_email = _clean(post.get('email') or post.get('guest_email'))
            guest_phone = _clean(post.get('phone') or post.get('guest_phone'))

            partner = Partner.search([('email', '=', guest_email)], limit=1)
            if not partner:
                partner = Partner.create({
                    'name': _clean(post.get('guest_name')),
                    'email': guest_email,
                    'phone': guest_phone,
                })

            reservation = request.env['hotel.reservation'].sudo().create({
                'guest_id': partner.id,
                'guest_name': _clean(post.get('guest_name')),
                'guest_id_type': post.get('guest_id_type') or 'national_id',
                'guest_id_number': _clean(post.get('guest_id_number')),
                'guest_id_expiry': post.get('guest_id_expiry') or False,
                'guest_id_scan': guest_id_scan_b64,
                'guest_id_scan_filename': guest_id_scan_filename,
                'guest_dob': post.get('guest_dob') or False,
                'guest_email': guest_email,
                'guest_phone': guest_phone,
                'emergency_contact_name': post.get('emergency_contact_name'),
                'emergency_contact_phone': post.get('emergency_contact_phone'),
                'vehicle_plate': post.get('vehicle_plate'),
                'room_id': int(post.get('room_id')),
                'check_in_date': post.get('check_in_date'),
                'check_out_date': post.get('check_out_date'),
                'adults': int(post.get('adults') or 1),
                'children': int(post.get('children') or 0),
                'special_requests': post.get('special_requests'),
                'state': 'draft',
            })
        except Exception as e:
            request.env.cr.rollback()
            return request.redirect(f'/hotel/book?error={e}')

        return request.render('hotel_management.public_booking_thanks', {
            'reservation': reservation,
            'partner': partner,
        })