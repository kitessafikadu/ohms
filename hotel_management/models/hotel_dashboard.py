from datetime import date, timedelta
from odoo import api, models

class HotelDashboard(models.TransientModel):
    _name = 'hotel.dashboard'
    _description = 'Hotel Dashboard Data Provider'

    @api.model
    def get_dashboard_data(self):
        today = date.today()
        Reservation = self.env['hotel.reservation']
        Room = self.env['hotel.room']
        Task = self.env['hotel.housekeeping.task']
        Order = self.env['hotel.room.service.order']

        # -------- KPIs --------
        arrivals = Reservation.search([
            ('check_in_date', '=', today),
            ('state', '=', 'confirmed'),
        ])
        departures = Reservation.search([
            ('check_out_date', '=', today),
            ('state', '=', 'checked_in'),
        ])
        in_house = Reservation.search([('state', '=', 'checked_in')])

        total_rooms = Room.search_count([('maintenance_hold', '=', False)])
        occupied_rooms = len(in_house.mapped('room_id'))
        occupancy = round(
            (occupied_rooms / total_rooms * 100) if total_rooms else 0.0, 1)

        # -------- Room status --------
        rooms = {
            'clean': Room.search_count([
                ('housekeeping_state', '=', 'clean'),
                ('maintenance_hold', '=', False),
            ]),
            'dirty': Room.search_count([
                ('housekeeping_state', '=', 'dirty'),
                ('maintenance_hold', '=', False),
            ]),
            'cleaning': Room.search_count([
                ('housekeeping_state', '=', 'cleaning'),
            ]),
            'maintenance': Room.search_count([('maintenance_hold', '=', True)]),
        }

        # -------- Housekeeping --------
        open_tasks = Task.search([
            ('state', 'in', ('pending', 'in_progress')),
        ])
        urgent_tasks = open_tasks.filtered(lambda t: t.priority in ('1', '2'))

        # -------- Invoicing queue --------
        to_invoice = Reservation.search([
            ('invoice_status', '=', 'to_invoice'),
            ('state', '=', 'checked_out'),
        ])
        to_invoice_total = float(
            sum(to_invoice.mapped('total_amount')) or 0.0)

        # -------- F&B --------
        orders_in_progress = Order.search_count([
            ('state', 'in', ('draft', 'preparing')),
        ])

        return {
            'today': str(today),
            'occupancy': occupancy,
            'total_rooms': total_rooms,
            'occupied_rooms': occupied_rooms,
            'arrivals_count': len(arrivals),
            'departures_count': len(departures),
            'in_house_count': len(in_house),
            'arrivals': [{
                'id': r.id,
                'name': r.name,
                'guest_name': r.guest_name or '',
                'room_name': r.room_id.name or '',
                'nights': r.total_nights,
            } for r in arrivals[:10]],
            'departures': [{
                'id': r.id,
                'name': r.name,
                'guest_name': r.guest_name or '',
                'room_name': r.room_id.name or '',
            } for r in departures[:10]],
            'rooms': rooms,
            'open_tasks_count': len(open_tasks),
            'urgent_tasks_count': len(urgent_tasks),
            'urgent_tasks': [{
                'id': t.id,
                'name': t.name or '',
                'room': t.room_id.name or '',
                'task_type': dict(
                    t._fields['task_type'].selection).get(t.task_type, ''),
                'priority': t.priority or '0',
                'assigned_to': t.assigned_to.name if t.assigned_to else '',
            } for t in urgent_tasks[:10]],
            'to_invoice_count': len(to_invoice),
            'to_invoice_total': to_invoice_total,
            'to_invoice': [{
                'id': r.id,
                'name': r.name,
                'guest_name': r.guest_name or '',
                'total_amount': float(r.total_amount or 0.0),
            } for r in to_invoice[:10]],
            'orders_in_progress': orders_in_progress,
        }