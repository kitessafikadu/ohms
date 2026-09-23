from datetime import date, timedelta

from odoo import api, fields, models
from odoo.exceptions import UserError, ValidationError

MIN_AGE = 18


class HotelReservation(models.Model):
    _name = 'hotel.reservation'
    _description = 'Hotel Reservation'
    _inherit = ['mail.thread', 'mail.activity.mixin']
    _order = 'check_in_date desc, id desc'

    name = fields.Char(
        default=lambda self: self.env['ir.sequence'].next_by_code(
            'hotel.reservation'),
        readonly=True, copy=False,
    )

    # =================================================================
    # Guest identity
    # =================================================================
    guest_id = fields.Many2one('res.partner', required=True, tracking=True)
    guest_name = fields.Char(
        string='Full Name (as on ID)', required=True, tracking=True,
    )
    guest_id_type = fields.Selection(
        [('passport', 'Passport'),
         ('national_id', 'National ID'),
         ('driver_license', "Driver's License")],
        required=True, default='national_id', tracking=True,
    )
    guest_id_number = fields.Char(required=True, tracking=True)
    guest_id_expiry = fields.Date()
    guest_id_scan = fields.Binary(string='Scanned ID')
    guest_id_scan_filename = fields.Char(string='ID Scan Filename')

    guest_dob = fields.Date(string='Date of Birth')
    guest_age = fields.Integer(compute='_compute_guest_age', store=True)
    is_adult = fields.Boolean(compute='_compute_guest_age', store=True)

    # =================================================================
    # Contact
    # =================================================================
    guest_email = fields.Char(string='Email')
    guest_phone = fields.Char(string='Phone')
    email = fields.Char(related='guest_email', store=True, readonly=False)
    phone = fields.Char(related='guest_phone', store=True, readonly=False)

    emergency_contact_name = fields.Char()
    emergency_contact_phone = fields.Char()
    emergency_contact_relation = fields.Char()

    vehicle_plate = fields.Char(string='Vehicle Plate')

    # =================================================================
    # Stay
    # =================================================================
    room_id = fields.Many2one('hotel.room', required=True, tracking=True)
    category_id = fields.Many2one(
        related='room_id.category_id', store=True, readonly=True,
    )
    check_in_date = fields.Date(required=True, tracking=True)
    check_out_date = fields.Date(required=True, tracking=True)
    total_nights = fields.Integer(compute='_compute_total_nights', store=True)

    adults = fields.Integer(default=1, required=True)
    children = fields.Integer(default=0, required=True)

    # =================================================================
    # Preferences
    # =================================================================
    bed_preference = fields.Selection(
        [('single', 'Single'), ('twin', 'Twin'),
         ('queen', 'Queen'), ('king', 'King')],
    )
    accessibility_needs = fields.Text()
    special_requests = fields.Text()

    # =================================================================
    # Companions
    # =================================================================
    companion_ids = fields.One2many(
        'hotel.reservation.guest', 'reservation_id',
        string='Additional Guests',
    )
    companion_count = fields.Integer(compute='_compute_companion_count')

    # =================================================================
    # Packages — charged separately
    # =================================================================
    package_ids = fields.One2many(
        'hotel.reservation.package', 'reservation_id',
        string='Packages',
    )
    packages_total = fields.Monetary(
        compute='_compute_packages_total', store=True,
        currency_field='currency_id',
        help='Total value of packages booked on this reservation.',
    )

    # =================================================================
    # Billing
    # =================================================================
    rate = fields.Monetary(currency_field='currency_id', tracking=True)
    extra_charges = fields.Monetary(currency_field='currency_id')
    payment_status = fields.Selection(
        [('pending', 'Pending'),
         ('partial', 'Partially Paid'),
         ('paid', 'Paid'),
         ('corporate', 'Corporate Account'),
         ('refunded', 'Refunded')],
        default='pending', tracking=True,
    )
    total_amount = fields.Monetary(
        compute='_compute_total_amount', store=True,
        currency_field='currency_id',
    )
    currency_id = fields.Many2one(
        'res.currency',
        default=lambda self: self.env.company.currency_id,
    )
    company_name = fields.Char(string='Company (for invoice)')
    tax_id = fields.Char(string='Tax ID / VAT')

    # =================================================================
    # Invoicing
    # =================================================================
    invoice_ids = fields.One2many(
        'account.move', 'hotel_reservation_id',
        string='Invoices',
        domain=[('move_type', '=', 'out_invoice')],
    )
    credit_note_ids = fields.One2many(
        'account.move', 'hotel_reservation_id',
        string='Credit Notes',
        domain=[('move_type', '=', 'out_refund')],
    )
    invoice_count = fields.Integer(compute='_compute_invoice_count')
    invoiced_amount = fields.Monetary(
        compute='_compute_invoiced_amount', store=True,
        currency_field='currency_id',
    )
    invoice_status = fields.Selection(
        [('nothing_to_invoice', 'Nothing to Invoice'),
         ('to_invoice', 'To Invoice'),
         ('invoiced', 'Fully Invoiced')],
        compute='_compute_invoice_status', store=True,
    )

    # =================================================================
    # State
    # =================================================================
    state = fields.Selection(
        [('draft', 'Draft'),
         ('confirmed', 'Confirmed'),
         ('checked_in', 'Checked-In'),
         ('checked_out', 'Checked-Out'),
         ('cancelled', 'Cancelled')],
        default='draft', tracking=True, group_expand='_expand_states',
    )

    notes = fields.Text()

    # =================================================================
    # Computes — charges
    # =================================================================
    @api.depends('check_in_date', 'check_out_date')
    def _compute_total_nights(self):
        for rec in self:
            if (rec.check_in_date and rec.check_out_date
                    and rec.check_out_date > rec.check_in_date):
                rec.total_nights = (rec.check_out_date - rec.check_in_date).days
            else:
                rec.total_nights = 0

    @api.depends('guest_dob')
    def _compute_guest_age(self):
        today = date.today()
        for rec in self:
            if rec.guest_dob:
                age = today.year - rec.guest_dob.year - (
                    (today.month, today.day) <
                    (rec.guest_dob.month, rec.guest_dob.day)
                )
                rec.guest_age = age
                rec.is_adult = age >= MIN_AGE
            else:
                rec.guest_age = 0
                rec.is_adult = False

    @api.depends('companion_ids')
    def _compute_companion_count(self):
        for rec in self:
            rec.companion_count = len(rec.companion_ids)

    @api.depends('package_ids.price')
    def _compute_packages_total(self):
        for rec in self:
            rec.packages_total = sum(rec.package_ids.mapped('price'))

    @api.depends('total_nights', 'rate', 'extra_charges', 'packages_total')
    def _compute_total_amount(self):
        for rec in self:
            rec.total_amount = (
                rec.total_nights * rec.rate
                + rec.packages_total
                + rec.extra_charges
            )

    # =================================================================
    # Computes — invoicing
    # =================================================================
    @api.depends('invoice_ids')
    def _compute_invoice_count(self):
        for rec in self:
            rec.invoice_count = len(rec.invoice_ids)

    @api.depends('invoice_ids', 'invoice_ids.state',
                 'invoice_ids.amount_total')
    def _compute_invoiced_amount(self):
        for rec in self:
            posted = rec.invoice_ids.filtered(lambda m: m.state == 'posted')
            rec.invoiced_amount = sum(posted.mapped('amount_total'))

    @api.depends('total_amount', 'invoiced_amount', 'state')
    def _compute_invoice_status(self):
        for rec in self:
            if rec.state == 'cancelled':
                rec.invoice_status = 'nothing_to_invoice'
            elif rec.total_amount <= 0:
                rec.invoice_status = 'nothing_to_invoice'
            elif rec.invoiced_amount >= rec.total_amount:
                rec.invoice_status = 'invoiced'
            elif rec.state in ('checked_in', 'checked_out'):
                rec.invoice_status = 'to_invoice'
            else:
                rec.invoice_status = 'nothing_to_invoice'

    # =================================================================
    # Onchange
    # =================================================================
    @api.onchange('check_in_date')
    def _onchange_check_in_date(self):
        if not self.check_in_date:
            return
        today = fields.Date.context_today(self)
        if self.check_in_date < today:
            self.check_in_date = today
            return {
                'warning': {
                    'title': 'Invalid check-in date',
                    'message': 'Check-in date cannot be in the past. '
                               'It has been set to today.',
                }
            }
        if (self.check_out_date
                and self.check_out_date <= self.check_in_date):
            self.check_out_date = self.check_in_date + timedelta(days=1)

    @api.onchange('check_out_date')
    def _onchange_check_out_date(self):
        if not self.check_out_date:
            return
        today = fields.Date.context_today(self)
        if self.check_out_date < today:
            self.check_out_date = today + timedelta(days=1)
            return {
                'warning': {
                    'title': 'Invalid check-out date',
                    'message': 'Check-out date cannot be in the past. '
                               'It has been set to tomorrow.',
                }
            }
        if (self.check_in_date
                and self.check_out_date <= self.check_in_date):
            self.check_out_date = self.check_in_date + timedelta(days=1)
            return {
                'warning': {
                    'title': 'Invalid check-out date',
                    'message': 'Check-out must be at least one day after '
                               'check-in. It has been adjusted.',
                }
            }

    @api.onchange('room_id')
    def _onchange_room_id(self):
        for rec in self:
            if rec.room_id and not rec.rate:
                rec.rate = (rec.room_id.rate
                            or rec.room_id.category_id.default_rate)

    @api.onchange('guest_id')
    def _onchange_guest_id(self):
        if self.guest_id:
            if not self.guest_name:
                self.guest_name = self.guest_id.name
            if not self.guest_email:
                self.guest_email = self.guest_id.email
            if not self.guest_phone:
                self.guest_phone = self.guest_id.phone

    # =================================================================
    # Constraints
    # =================================================================
    @api.constrains('check_in_date', 'check_out_date')
    def _check_dates(self):
        today = fields.Date.context_today(self)
        for rec in self:
            if rec.check_in_date and rec.check_in_date < today:
                raise ValidationError('Check-in date cannot be in the past.')
            if rec.check_out_date and rec.check_out_date < today:
                raise ValidationError('Check-out date cannot be in the past.')
            if (rec.check_in_date and rec.check_out_date
                    and rec.check_out_date <= rec.check_in_date):
                raise ValidationError(
                    'Check-out date must be strictly after check-in date.'
                )

    @api.constrains('guest_dob')
    def _check_adult(self):
        for rec in self:
            if rec.guest_dob:
                age = fields.Date.today().year - rec.guest_dob.year
                if age < MIN_AGE:
                    raise ValidationError(
                        f'Primary guest must be at least {MIN_AGE} years old.'
                    )

    @api.constrains('adults', 'children', 'room_id')
    def _check_capacity(self):
        for rec in self:
            cat = rec.room_id.category_id
            if rec.adults > cat.capacity_adults:
                raise ValidationError(
                    f'{rec.room_id.name} allows at most '
                    f'{cat.capacity_adults} adults.'
                )
            if rec.children > cat.capacity_children:
                raise ValidationError(
                    f'{rec.room_id.name} allows at most '
                    f'{cat.capacity_children} children.'
                )

    @api.constrains('room_id', 'check_in_date', 'check_out_date', 'state')
    def _check_no_double_booking(self):
        for rec in self:
            if rec.state in ('cancelled', 'checked_out', 'draft'):
                continue
            if rec._find_overlapping_reservations():
                raise ValidationError(
                    f'{rec.room_id.name} is already reserved for that period.'
                )

    def _find_overlapping_reservations(self):
        self.ensure_one()
        if not (self.room_id and self.check_in_date and self.check_out_date):
            return self.browse()
        return self.search([
            ('id', '!=', self.id),
            ('room_id', '=', self.room_id.id),
            ('state', 'in', ('confirmed', 'checked_in')),
            ('check_in_date', '<', self.check_out_date),
            ('check_out_date', '>', self.check_in_date),
        ], limit=1)

    # =================================================================
    # Group guards
    # =================================================================
    def _is_frontdesk(self):
        return self.env.user.has_group('hotel_management.group_hotel_frontdesk')

    def _is_manager(self):
        return self.env.user.has_group('hotel_management.group_hotel_manager')

    def _check_frontdesk(self, label):
        if not self._is_frontdesk():
            raise UserError(f'Only front-desk staff can {label}.')

    def _check_manager(self, label):
        if not self._is_manager():
            raise UserError(f'Only managers can {label}.')

    # =================================================================
    # Create / write
    # =================================================================
    @api.model_create_multi
    def create(self, vals_list):
        if self.env.user.has_group('base.group_portal'):
            for vals in vals_list:
                vals['guest_id'] = self.env.user.partner_id.id
                vals['state'] = 'draft'
                for forbidden in ('rate', 'extra_charges', 'total_amount',
                                  'package_ids', 'payment_status'):
                    vals.pop(forbidden, None)
        return super().create(vals_list)

    EDITABLE_AFTER_DRAFT = {
        'state', 'extra_charges', 'payment_status', 'notes',
        'accessibility_needs', 'special_requests', 'vehicle_plate',
        'companion_ids', 'guest_email', 'guest_phone',
        'emergency_contact_name', 'emergency_contact_phone',
        'message_ids', 'message_follower_ids', 'activity_ids',
    }

    def write(self, vals):
        if not self._is_manager() and set(vals) - self.EDITABLE_AFTER_DRAFT:
            locked = self.filtered(lambda r: r.state != 'draft')
            if locked:
                raise UserError(
                    f"Reservation(s) {', '.join(locked.mapped('name'))} "
                    f"are confirmed and cannot be edited. Ask a manager to "
                    f"reopen them first."
                )
        old_states = {rec.id: rec.state for rec in self}
        result = super().write(vals)
        if 'state' in vals:
            for rec in self:
                if (old_states.get(rec.id) != 'checked_out'
                        and rec.state == 'checked_out'):
                    rec._on_checkout_side_effects()
        return result

    # =================================================================
    # Workflow
    # =================================================================
    def action_confirm(self):
        self._check_frontdesk('confirm a reservation')
        for rec in self:
            if rec.state != 'draft':
                raise UserError('Only draft reservations can be confirmed.')
            if rec.room_id.maintenance_hold:
                raise UserError(f'{rec.room_id.name} is on maintenance hold.')
            if rec._find_overlapping_reservations():
                raise UserError(f'{rec.room_id.name} is already booked.')
            rec.state = 'confirmed'

    def action_check_in(self):
        self._check_frontdesk('check a guest in')
        for rec in self:
            if rec.state != 'confirmed':
                raise UserError('Only confirmed reservations can be checked in.')
            rec.state = 'checked_in'
            rec.room_id.housekeeping_state = 'dirty'

    def action_check_out(self):
        self._check_frontdesk('check a guest out')
        for rec in self:
            if rec.state != 'checked_in':
                raise UserError('Only checked-in reservations can be checked out.')
            rec.write({'state': 'checked_out'})

    def action_cancel(self):
        for rec in self:
            if rec.state == 'cancelled':
                continue
            if rec.state != 'draft':
                self._check_manager('cancel a confirmed booking')
            else:
                self._check_frontdesk('cancel a draft reservation')
            rec.state = 'cancelled'

    def action_set_draft(self):
        self._check_manager('reopen a booking')
        for rec in self:
            rec.state = 'draft'

    def _on_checkout_side_effects(self):
        self.ensure_one()
        room = self.room_id
        if not room:
            return
        room.housekeeping_state = 'dirty'

        today = fields.Date.context_today(self)
        next_arrival = self.env['hotel.reservation'].search([
            ('id', '!=', self.id),
            ('room_id', '=', room.id),
            ('state', '=', 'confirmed'),
            ('check_in_date', '=', today),
        ], limit=1)

        Task = self.env['hotel.housekeeping.task'].sudo()
        existing = Task.search([
            ('reservation_id', '=', self.id),
            ('task_type', '=', 'checkout_cleaning'),
            ('state', '!=', 'done'),
        ], limit=1)

        if not existing:
            Task.create({
                'room_id': room.id,
                'reservation_id': self.id,
                'task_type': 'checkout_cleaning',
                'scheduled_date': fields.Datetime.now(),
                'priority': '2' if next_arrival else '0',
            })

        self.message_post(body=(
            f'Guest checked out. Room <b>{room.name}</b> flagged Dirty.'
        ))

    # =================================================================
    # Invoicing
    # =================================================================
    def _prepare_invoice_lines(self):
        """Build the invoice line commands for the current charges."""
        self.ensure_one()
        lines = []

        # Room nights
        if self.total_nights and self.rate:
            room_product = self.env.ref(
                'hotel_management.product_hotel_room', raise_if_not_found=False)
            lines.append((0, 0, {
                'product_id': room_product.id if room_product else False,
                'name': (
                    f"Room {self.room_id.name}"
                    f"{' — ' + self.category_id.name if self.category_id else ''}\n"
                    f"{self.check_in_date} → {self.check_out_date}\n"
                    f"{self.total_nights} night(s)"
                ),
                'quantity': self.total_nights,
                'price_unit': self.rate,
            }))

        # Packages (charged separately)
        package_product = self.env.ref(
            'hotel_management.product_hotel_package', raise_if_not_found=False)
        for pkg in self.package_ids.filtered(lambda p: p.price):
            lines.append((0, 0, {
                'product_id': package_product.id if package_product else False,
                'name': f"Package: {pkg.package_id.name}",
                'quantity': 1,
                'price_unit': pkg.price,
            }))

        # Extra charges (F&B orders, damages, minibar, etc.)
        if self.extra_charges:
            extra_product = self.env.ref(
                'hotel_management.product_hotel_extra', raise_if_not_found=False)
            lines.append((0, 0, {
                'product_id': extra_product.id if extra_product else False,
                'name': 'Extra charges (F&B, services)',
                'quantity': 1,
                'price_unit': self.extra_charges,
            }))

        return lines

    def action_create_invoice(self):
        """Create a draft customer invoice for this reservation."""
        self.ensure_one()

        if self.state in ('draft', 'cancelled'):
            raise UserError(
                'You can only invoice confirmed, checked-in, or '
                'checked-out reservations.'
            )

        lines = self._prepare_invoice_lines()
        if not lines:
            raise UserError(
                'Nothing to invoice — the reservation has no charges.'
            )

        invoice = self.env['account.move'].create({
            'move_type': 'out_invoice',
            'partner_id': self.guest_id.id,
            'invoice_date': fields.Date.context_today(self),
            'invoice_origin': self.name,
            'hotel_reservation_id': self.id,
            'invoice_line_ids': lines,
        })

        return {
            'type': 'ir.actions.act_window',
            'name': 'Invoice',
            'res_model': 'account.move',
            'res_id': invoice.id,
            'view_mode': 'form',
            'target': 'current',
        }

    def action_view_invoices(self):
        """Smart button: open the list of invoices for this reservation."""
        self.ensure_one()
        action = self.env['ir.actions.act_window']._for_xml_id(
            'account.action_move_out_invoice_type')
        action['domain'] = [('hotel_reservation_id', '=', self.id)]
        action['context'] = {
            'default_hotel_reservation_id': self.id,
            'default_partner_id': self.guest_id.id,
        }
        if len(self.invoice_ids) == 1:
            action['views'] = [(False, 'form')]
            action['res_id'] = self.invoice_ids.id
        return action

    @api.model
    def _expand_states(self, states, domain, order):
        return [key for key, _ in self._fields['state'].selection]