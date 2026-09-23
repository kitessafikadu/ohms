from odoo import api, fields, models


class HotelHousekeepingTask(models.Model):
    _name = 'hotel.housekeeping.task'
    _description = 'Housekeeping Task'
    _inherit = ['mail.thread']
    _order = 'priority desc, scheduled_date asc'

    name = fields.Char(compute='_compute_name', store=True)

    room_id = fields.Many2one(
        'hotel.room', required=True, ondelete='restrict',
    )
    room_number = fields.Char(
        related='room_id.room_number', store=True, readonly=True,
    )
    room_category_id = fields.Many2one(
        related='room_id.category_id', store=True, readonly=True,
    )
    reservation_id = fields.Many2one(
        'hotel.reservation', ondelete='set null',
    )

    task_type = fields.Selection(
        [('checkout_cleaning', 'Check-out Cleaning'),
         ('daily_cleaning', 'Daily Cleaning'),
         ('maintenance', 'Maintenance')],
        default='checkout_cleaning', required=True,
    )

    priority = fields.Selection(
        [('0', 'Normal'), ('1', 'High'), ('2', 'Urgent')],
        default='0',
        help='Urgent = a new guest is arriving in this room today.',
    )

    scheduled_date = fields.Datetime(
        default=fields.Datetime.now, required=True,
    )
    completed_date = fields.Datetime()

    assigned_to = fields.Many2one('res.users', string='Assigned To')
    state = fields.Selection(
        [('pending', 'Pending'),
         ('in_progress', 'In Progress'),
         ('done', 'Done')],
        default='pending', tracking=True,
    )

    notes = fields.Text()

    @api.depends('room_id', 'task_type')
    def _compute_name(self):
        for rec in self:
            label = dict(rec._fields['task_type'].selection).get(
                rec.task_type, 'Task')
            rec.name = f"{rec.room_id.room_number or ''} — {label}"

    def action_start(self):
        for rec in self:
            rec.state = 'in_progress'
            rec.room_id.housekeeping_state = 'cleaning'
            if not rec.assigned_to:
                rec.assigned_to = self.env.user

    def action_done(self):
        for rec in self:
            rec.state = 'done'
            rec.completed_date = fields.Datetime.now()
            # Only mark clean if no other open tasks exist for the same room
            other = self.search([
                ('id', '!=', rec.id),
                ('room_id', '=', rec.room_id.id),
                ('state', '!=', 'done'),
            ], limit=1)
            if not other:
                rec.room_id.housekeeping_state = 'clean'