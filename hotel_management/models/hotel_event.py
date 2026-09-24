from datetime import datetime, timedelta

from odoo import api, fields, models
from odoo.exceptions import UserError, ValidationError

class HotelEvent(models.Model):
    _name = 'hotel.event'
    _description = 'Hotel Event Booking'
    _inherit = ['mail.thread', 'mail.activity.mixin']
    _order = 'event_date desc, start_time desc, id desc'

    name = fields.Char(
        default=lambda self: self.env['ir.sequence'].next_by_code(
            'hotel.event') or 'New',
        readonly=True, copy=False,
    )

    # =================================================================
    # Customer
    # =================================================================
    customer_id = fields.Many2one('res.partner', required=True, tracking=True)
    customer_name = fields.Char(required=True)
    customer_phone = fields.Char()
    customer_email = fields.Char()

    company_name = fields.Char(string='Company (for invoice)')
    tax_id = fields.Char(string='Tax ID / VAT')

    # =================================================================
    # Event details
    # =================================================================
    event_type = fields.Selection([
        ('wedding', 'Wedding'),
        ('conference', 'Conference'),
        ('meeting', 'Meeting'),
        ('birthday', 'Birthday'),
        ('corporate', 'Corporate Event'),
        ('other', 'Other'),
    ], required=True, default='meeting', tracking=True)

    venue_id = fields.Many2one(
        'hotel.venue', required=True, tracking=True,
    )
    event_date = fields.Date(required=True, tracking=True)
    start_time = fields.Float(
        required=True, help='Start time, e.g. 18.5 = 18:30.')
    end_time = fields.Float(
        required=True, help='End time, e.g. 23.0 = 23:00.')

    start_datetime = fields.Datetime(
        compute='_compute_datetimes', store=True, readonly=True)
    end_datetime = fields.Datetime(
        compute='_compute_datetimes', store=True, readonly=True)

    attendees = fields.Integer(default=0)
    description = fields.Text()
    special_requirements = fields.Text()

    responsible_id = fields.Many2one(
        'res.users', string='Event Coordinator',
        default=lambda self: self.env.user, tracking=True,
    )

    # =================================================================
    # Catering (via hotel.room.service catalogue)
    # =================================================================
    catering_line_ids = fields.One2many(
        'hotel.event.catering.line', 'event_id',
        string='Catering',
    )
    catering_total = fields.Monetary(
        compute='_compute_catering_total', store=True,
        currency_field='currency_id',
    )

    # =================================================================
    # Guest rooms linked to this event (optional)
    # =================================================================
    reservation_ids = fields.Many2many(
        'hotel.reservation',
        'hotel_event_reservation_rel',
        'event_id', 'reservation_id',
        string='Linked Reservations',
        help='Rooms booked for guests attending this event.',
    )

    # =================================================================
    # Pricing
    # =================================================================
    rate = fields.Monetary(
        currency_field='currency_id',
        help='Venue rental rate (whole event).',
    )
    extras_total = fields.Monetary(
        currency_field='currency_id',
        help='AV, decoration, staffing, other charges.',
    )
    total_amount = fields.Monetary(
        compute='_compute_total_amount', store=True,
        currency_field='currency_id',
    )
    currency_id = fields.Many2one(
        'res.currency',
        default=lambda self: self.env.company.currency_id,
    )

    deposit_amount = fields.Monetary(currency_field='currency_id')
    deposit_invoice_id = fields.Many2one(
        'account.move', string='Deposit Invoice', readonly=True, copy=False,
    )
    final_invoice_id = fields.Many2one(
        'account.move', string='Final Invoice', readonly=True, copy=False,
    )
    invoice_count = fields.Integer(compute='_compute_invoice_count')

    # =================================================================
    # Calendar integration
    # =================================================================
    calendar_event_id = fields.Many2one(
        'calendar.event', string='Calendar Entry',
        readonly=True, copy=False, ondelete='set null',
    )

    # =================================================================
    # State
    # =================================================================
    state = fields.Selection([
        ('enquiry', 'Enquiry'),
        ('quoted', 'Quoted'),
        ('confirmed', 'Confirmed'),
        ('in_progress', 'In Progress'),
        ('done', 'Completed'),
        ('cancelled', 'Cancelled'),
    ], default='enquiry', tracking=True, group_expand='_expand_states')

    notes = fields.Text()

    # =================================================================
    # Computes
    # =================================================================
    @api.depends('event_date', 'start_time', 'end_time')
    def _compute_datetimes(self):
        for rec in self:
            rec.start_datetime = rec._combine(rec.event_date, rec.start_time)
            rec.end_datetime = rec._combine(rec.event_date, rec.end_time)

    @staticmethod
    def _combine(date_val, float_val):
        if not date_val or not float_val:
            return False
        h = int(float_val)
        m = int(round((float_val - h) * 60))
        return datetime.combine(
            date_val, datetime.min.time().replace(hour=h, minute=m))

    @api.depends('catering_line_ids.subtotal')
    def _compute_catering_total(self):
        for rec in self:
            rec.catering_total = sum(
                rec.catering_line_ids.mapped('subtotal'))

    @api.depends('rate', 'catering_total', 'extras_total')
    def _compute_total_amount(self):
        for rec in self:
            rec.total_amount = (
                rec.rate + rec.catering_total + rec.extras_total)

    @api.depends('deposit_invoice_id', 'final_invoice_id')
    def _compute_invoice_count(self):
        for rec in self:
            rec.invoice_count = (
                (1 if rec.deposit_invoice_id else 0) +
                (1 if rec.final_invoice_id else 0))

    # =================================================================
    # Constraints
    # =================================================================
    @api.constrains('start_time', 'end_time')
    def _check_times(self):
        for rec in self:
            if rec.start_time and rec.end_time:
                if rec.start_time >= rec.end_time:
                    raise ValidationError(
                        'End time must be after start time.')
                if rec.start_time < 0 or rec.end_time > 24:
                    raise ValidationError(
                        'Times must be between 00:00 and 24:00.')

    @api.constrains('event_date', 'venue_id', 'start_time', 'end_time',
                    'state')
    def _check_venue_availability(self):
        for rec in self:
            if rec.state in ('cancelled', 'done'):
                continue
            if not (rec.event_date and rec.venue_id
                    and rec.start_time and rec.end_time):
                continue

            # Check for overlapping events on the same venue
            overlapping = self.search([
                ('id', '!=', rec.id),
                ('venue_id', '=', rec.venue_id.id),
                ('event_date', '=', rec.event_date),
                ('state', 'not in', ('cancelled', 'done')),
                ('start_time', '<', rec.end_time),
                ('end_time', '>', rec.start_time),
            ], limit=1)
            if overlapping:
                raise ValidationError(
                    f"{rec.venue_id.name} is already booked for that time "
                    f"({overlapping.name}, "
                    f"{overlapping._format_time_range()})."
                )

            # Setup / teardown buffer
            setup_h = (rec.venue_id.setup_minutes or 0) / 60.0
            teardown_h = (rec.venue_id.teardown_minutes or 0) / 60.0

            prev = self.search([
                ('id', '!=', rec.id),
                ('venue_id', '=', rec.venue_id.id),
                ('event_date', '=', rec.event_date),
                ('state', 'not in', ('cancelled', 'done')),
                ('end_time', '<=', rec.start_time),
            ], order='end_time desc', limit=1)
            if prev and prev.end_time + teardown_h > rec.start_time:
                raise ValidationError(
                    f"Not enough teardown time before {rec.name}. "
                    f"Previous event ({prev.name}) ends at "
                    f"{prev._format_time(prev.end_time)} and the venue "
                    f"needs {rec.venue_id.teardown_minutes} minutes of "
                    f"teardown."
                )

            nxt = self.search([
                ('id', '!=', rec.id),
                ('venue_id', '=', rec.venue_id.id),
                ('event_date', '=', rec.event_date),
                ('state', 'not in', ('cancelled', 'done')),
                ('start_time', '>=', rec.end_time),
            ], order='start_time asc', limit=1)
            if nxt and rec.end_time + setup_h > nxt.start_time:
                raise ValidationError(
                    f"Not enough setup time before {nxt.name}. "
                    f"This event ends at {rec._format_time(rec.end_time)} "
                    f"and the next event needs "
                    f"{rec.venue_id.setup_minutes} minutes of setup."
                )

    def _format_time(self, float_val):
        h = int(float_val)
        m = int(round((float_val - h) * 60))
        return f"{h:02d}:{m:02d}"

    def _format_time_range(self):
        self.ensure_one()
        return f"{self._format_time(self.start_time)}–" \
               f"{self._format_time(self.end_time)}"

    # =================================================================
    # Group guards
    # =================================================================
    def _is_frontdesk(self):
        return self.env.user.has_group(
            'hotel_management.group_hotel_frontdesk')

    def _is_manager(self):
        return self.env.user.has_group(
            'hotel_management.group_hotel_manager')

    def _check_frontdesk(self, label):
        if not self._is_frontdesk():
            raise UserError(f'Only front-desk staff can {label}.')

    def _check_manager(self, label):
        if not self._is_manager():
            raise UserError(f'Only managers can {label}.')

    # =================================================================
    # Workflow
    # =================================================================
    def action_quote(self):
        self._check_frontdesk('send a quote')
        for rec in self:
            if rec.state != 'enquiry':
                raise UserError('Only enquiries can be quoted.')
            rec.state = 'quoted'

    def action_confirm(self):
        self._check_frontdesk('confirm an event')
        for rec in self:
            if rec.state not in ('enquiry', 'quoted'):
                raise UserError('Only enquiries or quotes can be confirmed.')
            rec._check_venue_availability()
            rec._create_calendar_event()
            rec.state = 'confirmed'

    def action_start(self):
        self._check_frontdesk('start an event')
        for rec in self:
            if rec.state != 'confirmed':
                raise UserError('Only confirmed events can be started.')
            rec.state = 'in_progress'

    def action_done(self):
        self._check_frontdesk('complete an event')
        for rec in self:
            if rec.state != 'in_progress':
                raise UserError('Only running events can be completed.')
            rec.state = 'done'

    def action_cancel(self):
        for rec in self:
            if rec.state == 'cancelled':
                continue
            if rec.state != 'enquiry':
                self._check_manager('cancel a confirmed event')
            rec._remove_calendar_event()
            rec.state = 'cancelled'

    def action_reset_enquiry(self):
        self._check_manager('reopen an event')
        for rec in self:
            rec._remove_calendar_event()
            rec.state = 'enquiry'

    # =================================================================
    # Calendar integration
    # =================================================================
    def _create_calendar_event(self):
        self.ensure_one()
        self._remove_calendar_event()

        if not (self.start_datetime and self.end_datetime):
            return

        partner_ids = [(4, self.customer_id.id)] if self.customer_id else []
        cal = self.env['calendar.event'].create({
            'name': f"{self.name} — {self.customer_name}",
            'start': self.start_datetime,
            'stop': self.end_datetime,
            'user_id': self.responsible_id.id or self.env.user.id,
            'partner_ids': partner_ids,
            'description': (
                f"{self.get_event_type_label()} at {self.venue_id.name}\n"
                f"{self.attendees} guests\n"
                f"{self.description or ''}"
            ),
            'show_as': 'busy',
        })
        self.calendar_event_id = cal.id

    def _remove_calendar_event(self):
        for rec in self:
            if rec.calendar_event_id:
                rec.calendar_event_id.sudo().unlink()
                rec.calendar_event_id = False

    def get_event_type_label(self):
        self.ensure_one()
        return dict(self._fields['event_type'].selection).get(
            self.event_type, '')

    def action_view_calendar_event(self):
        self.ensure_one()
        if not self.calendar_event_id:
            raise UserError('No calendar entry exists for this event.')
        return {
            'type': 'ir.actions.act_window',
            'name': 'Calendar Entry',
            'res_model': 'calendar.event',
            'res_id': self.calendar_event_id.id,
            'view_mode': 'form',
            'target': 'current',
        }

    # =================================================================
    # Invoicing
    # =================================================================
    def _prepare_deposit_lines(self):
        self.ensure_one()
        if self.deposit_amount <= 0:
            return []
        return [(0, 0, {
            'name': f"Event deposit — {self.name}",
            'quantity': 1,
            'price_unit': self.deposit_amount,
        })]

    def _prepare_final_lines(self):
        self.ensure_one()
        lines = []

        # Venue rental
        if self.rate:
            lines.append((0, 0, {
                'name': (
                    f"Venue rental — {self.venue_id.name}\n"
                    f"{self.event_date} {self._format_time_range()}"
                ),
                'quantity': 1,
                'price_unit': self.rate,
            }))

        # Catering
        for line in self.catering_line_ids:
            lines.append((0, 0, {
                'name': line.description or (
                    line.service_id.name if line.service_id else 'Catering'),
                'quantity': line.quantity,
                'price_unit': line.unit_price,
            }))

        # Extras
        if self.extras_total:
            lines.append((0, 0, {
                'name': 'Extras (AV, decoration, staffing)',
                'quantity': 1,
                'price_unit': self.extras_total,
            }))

        # Subtract deposit already collected
        if self.deposit_amount and self.deposit_invoice_id:
            lines.append((0, 0, {
                'name': f"Less: deposit already invoiced ({self.name})",
                'quantity': 1,
                'price_unit': -self.deposit_amount,
            }))

        return lines

    def action_create_deposit_invoice(self):
        self.ensure_one()
        if self.deposit_invoice_id:
            return self._open_invoice(self.deposit_invoice_id)
        if self.deposit_amount <= 0:
            raise UserError('Set a deposit amount first.')

        invoice = self.env['account.move'].create({
            'move_type': 'out_invoice',
            'partner_id': self.customer_id.id,
            'invoice_date': fields.Date.context_today(self),
            'invoice_origin': self.name,
            'invoice_line_ids': self._prepare_deposit_lines(),
        })
        self.deposit_invoice_id = invoice.id
        return self._open_invoice(invoice)

    def action_create_final_invoice(self):
        self.ensure_one()
        if self.final_invoice_id:
            return self._open_invoice(self.final_invoice_id)

        lines = self._prepare_final_lines()
        if not lines:
            raise UserError('Nothing to invoice — no charges on this event.')

        invoice = self.env['account.move'].create({
            'move_type': 'out_invoice',
            'partner_id': self.customer_id.id,
            'invoice_date': fields.Date.context_today(self),
            'invoice_origin': self.name,
            'invoice_line_ids': lines,
        })
        self.final_invoice_id = invoice.id
        return self._open_invoice(invoice)

    def _open_invoice(self, invoice):
        return {
            'type': 'ir.actions.act_window',
            'name': 'Invoice',
            'res_model': 'account.move',
            'res_id': invoice.id,
            'view_mode': 'form',
            'target': 'current',
        }

    def action_view_invoices(self):
        self.ensure_one()
        invoice_ids = []
        if self.deposit_invoice_id:
            invoice_ids.append(self.deposit_invoice_id.id)
        if self.final_invoice_id:
            invoice_ids.append(self.final_invoice_id.id)

        action = self.env['ir.actions.act_window']._for_xml_id(
            'account.action_move_out_invoice_type')
        action['domain'] = [('id', 'in', invoice_ids)]
        if len(invoice_ids) == 1:
            action['views'] = [(False, 'form')]
            action['res_id'] = invoice_ids[0]
        return action

    @api.model
    def _expand_states(self, states, domain, order):
        return [key for key, _ in self._fields['state'].selection]


class HotelEventCateringLine(models.Model):
    _name = 'hotel.event.catering.line'
    _description = 'Event Catering Line'

    event_id = fields.Many2one(
        'hotel.event', required=True, ondelete='cascade')
    service_id = fields.Many2one(
        'hotel.room.service',
        domain="[('active', '=', True)]",
        help='Pick from the F&B catalogue, or describe freely.',
    )
    description = fields.Char(required=True)
    quantity = fields.Float(default=1.0, required=True)
    unit_price = fields.Monetary(currency_field='currency_id')
    currency_id = fields.Many2one(
        'res.currency',
        default=lambda self: self.env.company.currency_id,
    )
    subtotal = fields.Monetary(
        compute='_compute_subtotal', store=True,
        currency_field='currency_id',
    )

    @api.depends('quantity', 'unit_price')
    def _compute_subtotal(self):
        for rec in self:
            rec.subtotal = (rec.quantity or 0) * (rec.unit_price or 0)

    @api.onchange('service_id')
    def _onchange_service_id(self):
        if self.service_id:
            self.description = self.service_id.name
            self.unit_price = self.service_id.unit_price