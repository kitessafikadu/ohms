{
    'name': 'Hotel Management',
    'version': '18.0.1.2.1',
    'category': 'Services',
    'summary': 'Reservations, rooms, housekeeping, F&B, guest portal',
    'depends': ['base', 'mail', 'website', 'portal'],
    'data': [
        'security/hotel_security.xml',
        'security/ir.model.access.csv',
        'security/hotel_record_rules.xml',
        'data/ir_sequence_data.xml',
        'data/ir_cron_data.xml',
        'data/hotel_room_categories.xml',
        'views/hotel_room_views.xml',
        'views/hotel_reservation_views.xml',
        'views/hotel_housekeeping_views.xml',
        'views/hotel_room_service_views.xml',
        'views/hotel_menus.xml',
        'views/website_templates.xml',
    ],
    'assets': {
        'web.assets_backend': [
            'hotel_management/static/src/js/hotel_date_widgets.js',
        ],
    },
    'application': True,
    'installable': True,
    'license': 'LGPL-3',
}