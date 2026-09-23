from odoo import api, fields, models


class HotelHousekeepingTask(models.Model):
    _name = 'hotel.housekeeping.task'
    _description = 'Housekeeping Task'
    _inherit = ['mail.thread']
    _order = 'scheduled_date desc'

    name = fields.Char(compute='_compute_name', store=True)
    room_id = fields.Many2one('hotel.room', required=True)
    reservation_id = fields.Many2one('hotel.reservation', ondelete='set null')
    task_type = fields.Selection(
        [('checkout_cleaning', 'Check-out Cleaning'),
         ('daily_cleaning', 'Daily Cleaning'),
         ('maintenance', 'Maintenance')],
        default='checkout_cleaning', required=True,
    )
    scheduled_date = fields.Datetime(default=fields.Datetime.now)
    completed_date = fields.Datetime()
    assigned_to = fields.Many2one('res.users')
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
            rec.name = f"{rec.room_id.name or ''} — {dict(rec._fields['task_type'].selection).get(rec.task_type, '')}"

    def action_start(self):
        self.write({'state': 'in_progress'})

    def action_done(self):
        for rec in self:
            rec.state = 'done'
            rec.completed_date = fields.Datetime.now()
            # Free the room again
            rec.room_id.housekeeping_state = 'clean'