from datetime import date

from odoo import api, fields, models
from odoo.exceptions import UserError, ValidationError


SERVICE_TYPE_SELECTION = [
    ('room', 'Accommodation'),
    ('meal', 'Meal'),
    ('tea', 'Tea / Coffee'),
    ('boardroom', 'Boardroom / Meeting Room'),
    ('conference', 'Conference / Training'),
    ('other', 'Other'),
]


class HotelCorporateAccount(models.Model):
    _name = 'hotel.corporate.account'
    _description = 'Corporate Account'
    _inherit = ['mail.thread', 'mail.activity.mixin']
    _order = 'start_date desc, id desc'

    name = fields.Char(
        default=lambda self: self.env['ir.sequence'].next_by_code(
            'hotel.corporate.account') or 'New',
        readonly=True, copy=False,
    )
    company_id = fields.Many2one(
        'res.company', 'Hotel Branch',
        default=lambda self: self.env.company,
        index=True,
    )
    partner_id = fields.Many2one(
        'res.partner', string='Company', required=True, tracking=True,
    )
    contact_person = fields.Char()
    contact_email = fields.Char()
    contact_phone = fields.Char()
    start_date = fields.Date(required=True, default=fields.Date.today)
    end_date = fields.Date()
    billing_cycle = fields.Selection(
        [('monthly', 'Monthly'),
         ('quarterly', 'Quarterly'),
         ('program', 'End of Program')],
        default='monthly', required=True,
    )
    currency_id = fields.Many2one(
        'res.currency',
        default=lambda self: self.env.company.currency_id,
    )
    state = fields.Selection(
        [('draft', 'Draft'),
         ('active', 'Active'),
         ('ended', 'Ended'),
         ('cancelled', 'Cancelled')],
        default='draft', tracking=True,
    )
    subscription_ids = fields.One2many(
        'hotel.corporate.subscription', 'account_id',
        string='Subscriptions',
    )
    subscription_count = fields.Integer(
        compute='_compute_subscription_count')
    employee_ids = fields.One2many(
        'hotel.corporate.employee', 'account_id',
        string='Employees',
    )
    employee_count = fields.Integer(compute='_compute_employee_count')
    fulfillment_ids = fields.One2many(
        'hotel.corporate.fulfillment', 'account_id',
        string='Fulfillments',
    )
    fulfillment_count = fields.Integer(
        compute='_compute_fulfillment_count')
    invoice_ids = fields.One2many(
        'account.move', 'corporate_account_id',
        string='Invoices',
    )
    invoice_count = fields.Integer(compute='_compute_invoice_count')
    notes = fields.Text()

    _sql_constraints = [
        ('name_company_unique',
         'UNIQUE(name, company_id)',
         'Account number must be unique per branch.'),
    ]

    @api.depends('subscription_ids')
    def _compute_subscription_count(self):
        for rec in self:
            rec.subscription_count = len(rec.subscription_ids)

    @api.depends('employee_ids')
    def _compute_employee_count(self):
        for rec in self:
            rec.employee_count = len(rec.employee_ids)

    @api.depends('fulfillment_ids')
    def _compute_fulfillment_count(self):
        for rec in self:
            rec.fulfillment_count = len(rec.fulfillment_ids)

    @api.depends('invoice_ids')
    def _compute_invoice_count(self):
        for rec in self:
            rec.invoice_count = len(rec.invoice_ids)

    def _is_manager(self):
        return self.env.user.has_group(
            'hotel_management.group_hotel_manager')

    def _check_manager_field(self, label):
        if not self._is_manager():
            raise UserError(f'Only managers can {label}.')

    def action_activate(self):
        self._check_manager_field('activate an account')
        for rec in self:
            if rec.state != 'draft':
                raise UserError('Only draft accounts can be activated.')
            rec.state = 'active'

    def action_end(self):
        self._check_manager_field('end an account')
        for rec in self:
            rec.state = 'ended'

    def action_cancel(self):
        self._check_manager_field('cancel an account')
        for rec in self:
            rec.state = 'cancelled'

    def action_reset_draft(self):
        self._check_manager_field('reset an account')
        for rec in self:
            rec.state = 'draft'

    def action_view_fulfillments(self):
        self.ensure_one()
        return {
            'type': 'ir.actions.act_window',
            'name': 'Fulfillments',
            'res_model': 'hotel.corporate.fulfillment',
            'view_mode': 'list,form',
            'domain': [('account_id', '=', self.id)],
            'context': {'default_account_id': self.id},
        }

    def action_view_invoices(self):
        self.ensure_one()
        action = self.env['ir.actions.act_window']._for_xml_id(
            'account.action_move_out_invoice_type')
        action['domain'] = [('corporate_account_id', '=', self.id)]
        action['context'] = {'default_corporate_account_id': self.id}
        if len(self.invoice_ids) == 1:
            action['views'] = [(False, 'form')]
            action['res_id'] = self.invoice_ids.id
        return action

    def action_generate_invoice(self):
        self.ensure_one()
        if self.state != 'active':
            raise UserError('Only active accounts can be invoiced.')

        Fulfillment = self.env['hotel.corporate.fulfillment']
        unbilled = Fulfillment.search([
            ('account_id', '=', self.id),
            ('state', '=', 'delivered'),
            ('billed', '=', False),
        ])
        if not unbilled:
            raise UserError('No unbilled fulfillments to invoice.')

        grouped = {}
        for f in unbilled:
            key = (f.service_type, f.unit_price)
            entry = grouped.setdefault(key, {'qty': 0.0, 'total': 0.0})
            entry['qty'] += f.attended_qty
            entry['total'] += f.line_total

        lines = []
        for (service_type, unit_price), data in grouped.items():
            label = dict(SERVICE_TYPE_SELECTION).get(
                service_type, service_type)
            matching = unbilled.filtered(
                lambda f, st=service_type, up=unit_price:
                    f.service_type == st and f.unit_price == up)
            dates = matching.mapped('scheduled_date')
            period = f"{min(dates)} → {max(dates)}" if dates else ''
            lines.append((0, 0, {
                'name': f"{label} ({period})",
                'quantity': data['qty'],
                'price_unit': unit_price,
            }))

        if not lines:
            raise UserError('Nothing to invoice.')

        invoice = self.env['account.move'].create({
            'move_type': 'out_invoice',
            'partner_id': self.partner_id.id,
            'invoice_date': fields.Date.context_today(self),
            'invoice_origin': self.name,
            'corporate_account_id': self.id,
            'invoice_line_ids': lines,
        })

        unbilled.write({'billed': True, 'invoice_id': invoice.id})

        return {
            'type': 'ir.actions.act_window',
            'name': 'Invoice',
            'res_model': 'account.move',
            'res_id': invoice.id,
            'view_mode': 'form',
            'target': 'current',
        }

    @api.model
    def _cron_generate_daily_fulfillments(self):
        today = fields.Date.context_today(self)
        weekday = str(today.weekday())

        Subscription = self.env['hotel.corporate.subscription']
        Fulfillment = self.env['hotel.corporate.fulfillment']

        subs = Subscription.search([
            ('state', '=', 'active'),
            ('start_date', '<=', today),
            '|',
            ('end_date', '=', False),
            ('end_date', '>=', today),
        ])

        for sub in subs:
            day_list = (sub.day_of_week_list or '').split(',')
            if weekday not in day_list:
                continue
            exists = Fulfillment.search_count([
                ('subscription_id', '=', sub.id),
                ('scheduled_date', '=', today),
            ])
            if exists:
                continue
            Fulfillment.create({
                'subscription_id': sub.id,
                'account_id': sub.account_id.id,
                'scheduled_date': today,
                'scheduled_time': sub.start_time,
                'expected_qty': sub.expected_qty,
                'unit_price': sub.unit_price,
                'service_type': sub.service_type,
                'state': 'pending',
            })


class HotelCorporateSubscription(models.Model):
    _name = 'hotel.corporate.subscription'
    _description = 'Corporate Subscription Line'
    _order = 'account_id, start_time, id'

    name = fields.Char(required=True)
    account_id = fields.Many2one(
        'hotel.corporate.account', required=True, ondelete='cascade',
    )
    company_id = fields.Many2one(
        related='account_id.company_id',
        store=True, index=True,
    )
    service_type = fields.Selection(
        SERVICE_TYPE_SELECTION, required=True, default='meal',
    )
    description = fields.Text()

    day_of_week_list = fields.Char(
        compute='_compute_day_list', store=True,
    )
    day_mon = fields.Boolean('Monday', default=True)
    day_tue = fields.Boolean('Tuesday', default=True)
    day_wed = fields.Boolean('Wednesday', default=True)
    day_thu = fields.Boolean('Thursday', default=True)
    day_fri = fields.Boolean('Friday', default=True)
    day_sat = fields.Boolean('Saturday', default=False)
    day_sun = fields.Boolean('Sunday', default=False)

    start_time = fields.Float(required=True, default=12.0)
    end_time = fields.Float(required=True, default=14.0)
    start_date = fields.Date(required=True, default=fields.Date.today)
    end_date = fields.Date()

    expected_qty = fields.Integer(default=1, required=True)
    unit_price = fields.Monetary(currency_field='currency_id')
    currency_id = fields.Many2one(
        'res.currency', related='account_id.currency_id', store=True,
    )
    state = fields.Selection(
        [('active', 'Active'),
         ('paused', 'Paused'),
         ('ended', 'Ended')],
        default='active', required=True,
    )
    fulfillment_ids = fields.One2many(
        'hotel.corporate.fulfillment', 'subscription_id',
    )
    fulfillment_count = fields.Integer(
        compute='_compute_fulfillment_count')

    @api.depends('day_mon', 'day_tue', 'day_wed', 'day_thu',
                 'day_fri', 'day_sat', 'day_sun')
    def _compute_day_list(self):
        for rec in self:
            days = []
            if rec.day_mon:
                days.append('0')
            if rec.day_tue:
                days.append('1')
            if rec.day_wed:
                days.append('2')
            if rec.day_thu:
                days.append('3')
            if rec.day_fri:
                days.append('4')
            if rec.day_sat:
                days.append('5')
            if rec.day_sun:
                days.append('6')
            rec.day_of_week_list = ','.join(days)

    @api.depends('fulfillment_ids')
    def _compute_fulfillment_count(self):
        for rec in self:
            rec.fulfillment_count = len(rec.fulfillment_ids)

    @api.constrains('start_time', 'end_time')
    def _check_times(self):
        for rec in self:
            if rec.start_time >= rec.end_time:
                raise ValidationError(
                    'End time must be after start time.')
            if rec.start_time < 0 or rec.end_time > 24:
                raise ValidationError(
                    'Times must be between 00:00 and 24:00.')

    @api.constrains('start_date', 'end_date')
    def _check_dates(self):
        for rec in self:
            if rec.start_date and rec.end_date \
                    and rec.end_date < rec.start_date:
                raise ValidationError(
                    'End date must be after start date.')


class HotelCorporateFulfillment(models.Model):
    _name = 'hotel.corporate.fulfillment'
    _description = 'Corporate Service Fulfillment'
    _inherit = ['mail.thread']
    _order = 'scheduled_date desc, scheduled_time desc, id desc'

    name = fields.Char(compute='_compute_name', store=True)
    subscription_id = fields.Many2one(
        'hotel.corporate.subscription', required=True, ondelete='cascade',
    )
    account_id = fields.Many2one(
        'hotel.corporate.account', required=True, ondelete='cascade',
        related='subscription_id.account_id', store=True, readonly=False,
    )
    company_id = fields.Many2one(
        related='account_id.company_id',
        store=True, index=True,
    )
    service_type = fields.Selection(
        SERVICE_TYPE_SELECTION, required=True)
    scheduled_date = fields.Date(required=True, index=True)
    scheduled_time = fields.Float()
    expected_qty = fields.Integer()
    attended_qty = fields.Integer(default=0)
    unit_price = fields.Monetary(currency_field='currency_id')
    line_total = fields.Monetary(
        compute='_compute_line_total', store=True,
        currency_field='currency_id',
    )
    currency_id = fields.Many2one(
        'res.currency', related='account_id.currency_id', store=True,
    )
    served_by = fields.Many2one(
        'res.users', default=lambda self: self.env.user,
    )
    served_on = fields.Datetime()
    notes = fields.Text()
    state = fields.Selection(
        [('pending', 'Pending'),
         ('delivered', 'Delivered'),
         ('cancelled', 'Cancelled')],
        default='pending', tracking=True,
    )
    billed = fields.Boolean(default=False, readonly=True, copy=False)
    invoice_id = fields.Many2one(
        'account.move', readonly=True, copy=False,
    )

    @api.depends('subscription_id', 'scheduled_date')
    def _compute_name(self):
        for rec in self:
            sub_name = rec.subscription_id.name or ''
            d = rec.scheduled_date
            rec.name = f"{sub_name} - {d}" if d else sub_name

    @api.depends('attended_qty', 'unit_price')
    def _compute_line_total(self):
        for rec in self:
            rec.line_total = (rec.attended_qty or 0) * (rec.unit_price or 0)

    def action_deliver(self):
        for rec in self:
            if rec.state != 'pending':
                raise UserError(
                    'Only pending fulfillments can be delivered.')
            if rec.attended_qty <= 0:
                raise UserError({
                    'attended_qty':
                        'Enter how many people were served before '
                        'marking as delivered.'
                })
            rec.state = 'delivered'
            rec.served_on = fields.Datetime.now()
            if not rec.served_by:
                rec.served_by = self.env.user

    def action_cancel(self):
        for rec in self:
            rec.state = 'cancelled'

    def action_reset_draft(self):
        for rec in self:
            if rec.billed:
                raise UserError(
                    'Cannot reset a fulfillment that has been billed.')
            rec.state = 'pending'


class HotelCorporateEmployee(models.Model):
    _name = 'hotel.corporate.employee'
    _description = 'Employee on a Corporate Account'
    _order = 'name'

    name = fields.Char(required=True)
    account_id = fields.Many2one(
        'hotel.corporate.account', required=True, ondelete='cascade',
    )
    company_id = fields.Many2one(
        related='account_id.company_id',
        store=True, index=True,
    )
    partner_id = fields.Many2one('res.partner')
    employee_number = fields.Char()
    department = fields.Char()
    email = fields.Char()
    phone = fields.Char()
    id_number = fields.Char()
    dietary_notes = fields.Text()
    active = fields.Boolean(default=True)

    _sql_constraints = [
        ('unique_number_per_account',
         'UNIQUE(account_id, employee_number)',
         'Employee number must be unique per account.'),
    ]