import base64
import json
import re
import urllib.parse
from datetime import date, timedelta

from odoo import http
from odoo.http import request


NAME_RE = re.compile(r"^[A-Za-z][A-Za-z'\-]*(?:\s+[A-Za-z][A-Za-z'\-]*)+$")
EMAIL_RE = re.compile(r"^[^@\s]+@[^@\s]+\.[A-Za-z]{2,}$")
ID_RE = re.compile(r"^[A-Za-z0-9\- ]{4,32}$")
PHONE_RE = re.compile(r"^(?:\+?\d{1,4}[\s\-]?)?\d{6,12}$")

MAX_ID_SCAN_BYTES = 5 * 1024 * 1024
MAX_ID_SCAN_LABEL = '5 MB'

ALLOWED_MAGIC_BYTES = (
    (b'\x89PNG\r\n\x1a\n', 'image/png', 'PNG'),
    (b'\xff\xd8\xff', 'image/jpeg', 'JPG'),
)


def _clean(value):
    return (value or "").strip()


def _normalize_phone(phone):
    return re.sub(r"[\s\-()]+", "", phone or "")


def _sniff_file_type(data):
    for magic, mime, label in ALLOWED_MAGIC_BYTES:
        if data.startswith(magic):
            return mime, label
    return None, None


def _read_id_file(uploaded_file):
    if not uploaded_file or not uploaded_file.filename:
        return False, False, None

    filename = uploaded_file.filename
    data = uploaded_file.read()

    if not data:
        return False, False, 'The uploaded file is empty.'

    size = len(data)
    if size > MAX_ID_SCAN_BYTES:
        size_mb = round(size / (1024 * 1024), 2)
        return False, False, (
            f'File is {size_mb} MB — the maximum allowed is '
            f'{MAX_ID_SCAN_LABEL}. Please resize or compress the image.'
        )

    if not filename.lower().endswith(('.jpg', '.jpeg', '.png')):
        return False, False, (
            'Only JPG and PNG files are accepted. '
            'Convert your file and try again.'
        )

    detected_mime, detected_label = _sniff_file_type(data)
    if not detected_mime:
        return False, False, (
            'The file does not appear to be a valid JPG or PNG image. '
            'Please re-save it as JPG or PNG and try again.'
        )

    return base64.b64encode(data), filename, None


def _validate_booking(post):
    errors = []

    name = _clean(post.get("guest_name"))
    if not name:
        errors.append("Full name is required.")
    elif not NAME_RE.match(name):
        errors.append(
            "Please enter your full name as on your ID "
            "(first name and last name, letters only)."
        )

    email = _clean(post.get("email") or post.get("guest_email"))
    if not email:
        errors.append("Email is required.")
    elif not EMAIL_RE.match(email):
        errors.append("Please enter a valid email address.")

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

    id_number = _clean(post.get("guest_id_number"))
    if not id_number:
        errors.append("ID number is required.")
    elif not ID_RE.match(id_number):
        errors.append(
            "ID number must be 4 to 32 characters "
            "(letters, digits, hyphens or spaces)."
        )

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

    if not post.get("room_id"):
        errors.append("Please select a room.")

    return errors


class HotelPublicBooking(http.Controller):

    @http.route('/hotel/book', type='http', auth='public', website=True)
    def booking_form(self, **kw):
        today = date.today()
        categories = request.env['hotel.room.category'].sudo().search(
            [('active', '=', True)])

        field_errors = {}
        raw = kw.get('field_errors')
        if raw:
            try:
                field_errors = json.loads(urllib.parse.unquote(raw))
            except (ValueError, TypeError):
                field_errors = {}

        return request.render('hotel_management.public_booking_form', {
            'categories': categories,
            'min_check_in': (today + timedelta(days=1)).isoformat(),
            'min_check_out': (today + timedelta(days=2)).isoformat(),
            'field_errors': field_errors,
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
        front_file = request.httprequest.files.get('guest_id_scan_front')
        back_file = request.httprequest.files.get('guest_id_scan_back')

        front_b64, front_name, front_err = _read_id_file(front_file)
        back_b64, back_name, back_err = _read_id_file(back_file)

        field_errors = {}
        if front_err:
            field_errors['guest_id_scan_front'] = front_err
        if back_err:
            field_errors['guest_id_scan_back'] = back_err

        text_errors = _validate_booking(post)
        if text_errors:
            field_errors['__general__'] = ' | '.join(text_errors)

        if field_errors:
            encoded = urllib.parse.quote(json.dumps(field_errors))
            return request.redirect(f'/hotel/book?field_errors={encoded}')

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
                'guest_id_scan_front': front_b64,
                'guest_id_scan_front_filename': front_name,
                'guest_id_scan_back': back_b64,
                'guest_id_scan_back_filename': back_name,
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
            encoded = urllib.parse.quote(json.dumps({'__general__': str(e)}))
            return request.redirect(f'/hotel/book?field_errors={encoded}')

        return request.render('hotel_management.public_booking_thanks', {
            'reservation': reservation,
            'partner': partner,
        })