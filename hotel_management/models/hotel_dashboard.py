from datetime import date, timedelta

from odoo import api, models


class HotelDashboard(models.TransientModel):
    _name = 'hotel.dashboard'
    _description = 'Hotel Dashboard Data Provider'

    @api.model
    def get_dashboard_data(self):
        today = date.today()
        week_end = today + timedelta(days=7)

        Reservation = self.env['hotel.reservation']
        Room = self.env['hotel.room']
        Task = self.env['hotel.housekeeping.task']
        Order = self.env['hotel.room.service.order']
        Event = self.env['hotel.event']

        # ============================================================
        # KPIs — arrivals / departures / in-house
        # ============================================================
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

        # ============================================================
        # Room status
        # ============================================================
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
            'maintenance': Room.search_count([
                ('maintenance_hold', '=', True),
            ]),
        }

        # ============================================================
        # Housekeeping
        # ============================================================
        open_tasks = Task.search([
            ('state', 'in', ('pending', 'in_progress')),
        ])
        urgent_tasks = open_tasks.filtered(
            lambda t: t.priority in ('1', '2'))

        # ============================================================
        # Invoicing queue
        # ============================================================
        to_invoice = Reservation.search([
            ('invoice_status', '=', 'to_invoice'),
            ('state', '=', 'checked_out'),
        ])
        to_invoice_total = float(
            sum(to_invoice.mapped('total_amount')) or 0.0)

        # ============================================================
        # F&B orders in progress
        # ============================================================
        orders_in_progress = Order.search_count([
            ('state', 'in', ('draft', 'preparing')),
        ])

        # ============================================================
        # Events — today and this week
        # ============================================================
        events_today = Event.search([
            ('event_date', '=', today),
            ('state', 'not in', ('cancelled',)),
        ])
        events_this_week = Event.search([
            ('event_date', '>', today),
            ('event_date', '<=', week_end),
            ('state', 'not in', ('cancelled',)),
        ])

        # ============================================================
        # Package
        # ============================================================
        return {
            'today': str(today),

            # ---- KPI cards ----
            'occupancy': occupancy,
            'total_rooms': total_rooms,
            'occupied_rooms': occupied_rooms,
            'arrivals_count': len(arrivals),
            'departures_count': len(departures),
            'in_house_count': len(in_house),

            # ---- Arrivals list ----
            'arrivals': [{
                'id': r.id,
                'name': r.name,
                'guest_name': r.guest_name or '',
                'room_name': r.room_id.name or '',
                'nights': r.total_nights,
            } for r in arrivals[:10]],

            # ---- Departures list ----
            'departures': [{
                'id': r.id,
                'name': r.name,
                'guest_name': r.guest_name or '',
                'room_name': r.room_id.name or '',
            } for r in departures[:10]],

            # ---- Rooms ----
            'rooms': rooms,

            # ---- Housekeeping ----
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

            # ---- Invoicing ----
            'to_invoice_count': len(to_invoice),
            'to_invoice_total': to_invoice_total,
            'to_invoice': [{
                'id': r.id,
                'name': r.name,
                'guest_name': r.guest_name or '',
                'total_amount': float(r.total_amount or 0.0),
            } for r in to_invoice[:10]],

            # ---- F&B ----
            'orders_in_progress': orders_in_progress,

            # ---- Events (new) ----
            'events_today_count': len(events_today),
            'events_week_count': len(events_this_week),
            'events_today': [{
                'id': e.id,
                'name': e.name,
                'customer_name': e.customer_name or '',
                'venue': e.venue_id.name or '',
                'event_type': dict(
                    e._fields['event_type'].selection).get(
                        e.event_type, ''),
                'time_range': e._format_time_range(),
                'attendees': e.attendees,
                'state': e.state,
                'responsible': e.responsible_id.name or '',
            } for e in events_today[:10]],
            'events_week': [{
                'id': e.id,
                'name': e.name,
                'customer_name': e.customer_name or '',
                'venue': e.venue_id.name or '',
                'date': str(e.event_date) if e.event_date else '',
                'time_range': e._format_time_range(),
                'attendees': e.attendees,
                'state': e.state,
            } for e in events_this_week[:10]],
        }