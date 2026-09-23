# Hotel Management

Hotel Management is an Odoo 18 application for hotel reservations, room
operations, housekeeping, food and beverage services, and guest self-service.

## Features

- Room categories with capacities, rates, amenities, images, and bed configurations.
- Room inventory with housekeeping state, maintenance holds, current availability, and next-arrival tracking.
- Reservation workflow from draft request through confirmation, check-in, check-out, and cancellation.
- Guest identity details, age checks, ID scan uploads, contact details, emergency contacts, and special requests.
- Public booking form with category-based room selection and server-side validation.
- Portal reservation list and detail pages for authenticated guests.
- Food and beverage catalogue, packages, package entitlements, and room-service orders.
- Housekeeping tasks and room status management.
- Reservation feedback and portal ordering for checked-in guests.
- Role-based access for managers, front desk staff, housekeepers, waitstaff, and hotel customers.

## Requirements

- Odoo 18.0
- Python dependencies required by the parent Odoo installation
- Odoo modules: `base`, `mail`, `website`, and `portal`

## Installation

1. Copy or symlink this directory into an Odoo addons path.
2. Restart the Odoo server.
3. Update the Apps list, or run:

   ```bash
   ./odoo-bin -c /path/to/odoo.conf -d database_name -u hotel_management
   ```

4. Install **Hotel Management** if it is not already installed.
5. Assign the appropriate Hotel Management security group to each user.

For development, upgrade the module without starting the server:

```bash
testvenv/bin/python ./odoo-bin -c ./odoo.conf \
	-u hotel_management -d hotel_ms_db --stop-after-init
```

## User Roles

| Role | Main responsibilities |
| --- | --- |
| Manager | Full hotel-management access, configuration, cancellations, and administration |
| Front Desk | Reservations, rooms, confirmation, check-in, and check-out |
| Housekeeper | Housekeeping tasks and room cleanliness/status updates |
| Waitstaff | Food and beverage service orders |
| Hotel Customer | Portal access to their own reservations and guest booking features |

The customer group implies the standard Odoo portal group. Guests see only
reservations belonging to their own partner.

## Configuration

After installation, a manager should configure:

1. **Room Categories**: capacity, bed configuration, default rate, audience, and features.
2. **Rooms**: room number, category, rate, view, accessibility, and maintenance status.
3. **F&B & Packages**: food and beverage items, prices, and package contents.
4. **Users and groups**: assign the appropriate security group to each staff member.

## Reservation Workflow

1. A guest submits a booking request or front desk creates a draft.
2. Front desk reviews the guest, room, dates, and identity information.
3. The reservation is confirmed after availability and capacity checks.
4. The guest is checked in, enabling room-service ordering through the portal.
5. Room-service orders are prepared and delivered. Chargeable items are added to the reservation when delivered.
6. The guest is checked out and the reservation can no longer accept new room-service orders.

## Web Routes

### Public booking

- `GET /hotel/book` - Display the public booking form.
- `GET /hotel/rooms/<category_id>` - Return available rooms for a category as JSON.
- `POST /hotel/book/submit` - Validate and create a draft reservation.

### Guest portal

- `GET /my/reservations` - List the current user's reservations.
- `GET /my/reservations/<reservation_id>` - Show reservation details.
- `POST /my/reservations/<reservation_id>/order` - Order food or beverages while checked in.
- `POST /my/reservations/<reservation_id>/feedback` - Submit reservation feedback.

## Validation Rules

- Check-in cannot be earlier than today.
- Check-out must be after check-in and cannot be in the past.
- Backend date pickers disable dates before the valid minimum date; checkout starts on the day after check-in.
- The primary guest must be at least 18 years old.
- Full names require at least a first and last name.
- ID numbers must contain 4 to 32 letters, digits, hyphens, or spaces.
- Public ID scans accept JPG, JPEG, PNG, and PDF files up to 5 MB.
- At least one adult is required, and room capacity is enforced.
- Confirmed and checked-in reservations cannot overlap for the same room.
- Rooms on maintenance hold are excluded from public room selection.

Validation is performed in the browser where appropriate and enforced again by
the controller and Odoo model constraints.

## Initial Data

The module includes sample Standard, Deluxe, Family Suite, and Presidential
Suite room categories. It also installs reservation and room-service sequences
plus scheduled data defined by the module.

## Technical Notes

- Module name: `hotel_management`
- Version: `18.0.1.0.10`
- License: LGPL-3
- Backend date-picker behavior is implemented in `static/src/js/hotel_date_widgets.js`.
- Public pages use Odoo Website templates and CSRF-protected POST forms.
- Reservation and service models inherit Odoo chatter/activity support where operational history is needed.

## License

LGPL-3.
# Hotel Management

Hotel Management is an Odoo 18 application for hotel reservations, room
operations, housekeeping, food and beverage services, and guest self-service.

## Features

- Room categories with capacities, rates, amenities, images, and bed
	configurations.
- Room inventory with housekeeping state, maintenance holds, current
	availability, and next-arrival tracking.
- Reservation workflow from draft request through confirmation, check-in,
	check-out, and cancellation.
- Guest identity details, date of birth and age checks, ID scan uploads, guest
	contact details, emergency contacts, and special requests.
- Public booking form with category-based room selection and server-side
	validation.
- Portal reservation list and detail pages for authenticated guests.
- Food and beverage catalogue, packages, package entitlements, and room-service
	orders.
- Housekeeping tasks and room status management.
- Reservation feedback and portal ordering of additional services for checked-in
	guests.
- Role-based access for managers, front desk staff, housekeepers, waitstaff,
	and hotel customers.

## Requirements

- Odoo 18.0
- Python dependencies required by the parent Odoo installation
- Odoo modules: `base`, `mail`, `website`, and `portal`

## Installation

1. Copy or symlink this directory into an Odoo addons path.
2. Restart the Odoo server.
3. Update the Apps list from the Apps menu, or run:

	 ```bash
	 ./odoo-bin -c /path/to/odoo.conf -d database_name -u hotel_management
	 ```

4. Install **Hotel Management** from the Apps menu if it is not already
	 installed.
5. Assign the appropriate Hotel Management security group to each user.

For a development database, the module can be upgraded without starting the
server:

```bash
testvenv/bin/python ./odoo-bin -c ./odoo.conf \
		-u hotel_management -d hotel_ms_db --stop-after-init
```

## User Roles

| Role | Main responsibilities |
| --- | --- |
| Manager | Full hotel-management access, configuration, cancellations, and administration |
| Front Desk | Reservations, rooms, confirmation, check-in, and check-out |
| Housekeeper | Housekeeping tasks and room cleanliness/status updates |
| Waitstaff | Food and beverage service orders |
| Hotel Customer | Portal access to their own reservations and guest booking features |

The customer group implies the standard Odoo portal group. Reservation portal
records are filtered by the logged-in user's partner, so guests see only their
own reservations.

## Web Routes

### Public booking

- `GET /hotel/book` - Display the public booking form.
- `GET /hotel/rooms/<category_id>` - Return available rooms for a category as
	JSON.
- `POST /hotel/book/submit` - Validate and create a draft reservation.

### Guest portal

- `GET /my/reservations` - List the current user's reservations.
- `GET /my/reservations/<reservation_id>` - Show reservation details.
- `POST /my/reservations/<reservation_id>/order` - Order food or beverages
	while checked in.
- `POST /my/reservations/<reservation_id>/feedback` - Submit reservation
	feedback.

## Validation Rules

- Check-in cannot be earlier than today.
- Check-out must be after check-in and cannot be in the past.
- The backend date picker disables dates before the valid minimum date; checkout
	starts on the day after check-in.
- The primary guest must be at least 18 years old.
- Full names require at least a first and last name.
- ID numbers must contain 4 to 32 letters, digits, hyphens, or spaces.
- Public ID scans accept JPG, JPEG, PNG, and PDF files up to 5 MB.
- At least one adult is required, and room capacity is enforced.
- Confirmed and checked-in reservations cannot overlap for the same room.

Validation is performed in the browser where appropriate and enforced again by
the controller and Odoo model constraints.

## Initial Data

The module includes sample room categories for Standard, Deluxe, Family Suite,
and Presidential Suite rooms. It also installs reservation and room-service
sequences plus scheduled data defined by the module.

## Technical Notes

- Module name: `hotel_management`
- Version: `18.0.1.0.10`
- License: LGPL-3
- Backend date-picker behavior is implemented with
	`static/src/js/hotel_date_widgets.js`.
- Public pages use Odoo Website templates and CSRF-protected POST forms.
- Reservation and service models inherit Odoo chatter/activity support where
	operational history is needed.
 # Hotel Management

An Odoo 18 hotel operations module for reservations, rooms, housekeeping, food
and beverage service, public booking, and guest self-service.

## Features

- Manage room categories, rooms, rates, capacities, views, accessibility, and
	maintenance holds.
- Create and manage reservations through the front desk interface.
- Track reservation states: Draft, Confirmed, Checked-In, Checked-Out, and
	Cancelled.
- Validate guest identity information, date of birth, contact details, room
	capacity, stay dates, and overlapping confirmed reservations.
- Upload an optional government ID scan in JPG, JPEG, PNG, or PDF format up to
	5 MB.
- Track housekeeping tasks and room cleanliness states.
- Maintain food and beverage items and packages.
- Create room-service orders, deliver them, charge ad-hoc orders to the
	reservation, and consume package entitlements.
- Provide a public booking form at `/hotel/book`.
- Provide authenticated guests with a reservation portal, room-service
	ordering for checked-in stays, and feedback submission.

## Requirements

- Odoo 18.0
- Python dependencies required by the parent Odoo installation
- Odoo applications/modules: `base`, `mail`, `website`, and `portal`

The module is designed to run from a custom addons directory. It does not
include a separate database or external service.

## Installation

1. Copy or link `hotel_management` into a directory listed in Odoo's
	 `addons_path`.
2. Restart Odoo.
3. Update the Apps list from the Apps menu, or run:

	 ```bash
	 ./odoo-bin -c /path/to/odoo.conf -d <database> -u hotel_management \
			 --stop-after-init
	 ```

4. Open the Hotel application and configure room categories, rooms, and the
	 food-and-beverage catalogue.

For development environments using the repository virtual environment, run
the command with `testvenv/bin/python ./odoo-bin` instead of `./odoo-bin`.

## Configuration

After installation, a manager should configure:

1. **Room Categories**: capacity, bed configuration, default rate, audience,
	 and features.
2. **Rooms**: room number, category, rate, view, accessibility, and
	 maintenance status.
3. **F&B & Packages**: food and beverage items, prices, and package contents.
4. **Users and groups**: assign the appropriate Hotel Management security
	 group to each staff member.

## Security Groups

| Group | Responsibility |
| --- | --- |
| Hotel Customer | Portal access, public booking, and access to the customer's own reservations |
| Front Desk | Reservations, guests, check-in, and check-out |
| Housekeeper | Housekeeping tasks and room status |
| Waitstaff | Food and beverage orders for checked-in guests |
| Manager | Full hotel management access and configuration |

Portal users are restricted to reservations belonging to their own partner.
Public booking submissions are created as draft reservations for later front
desk confirmation.

## Reservation Workflow

1. A guest submits a booking request or a front-desk user creates a draft.
2. Front desk reviews the guest, room, dates, and identity information.
3. The reservation is confirmed after availability and capacity checks.
4. The guest is checked in, enabling room-service ordering through the portal.
5. Room-service orders are prepared and delivered. Chargeable items are added
	 to the reservation when delivered.
6. The guest is checked out and the reservation can no longer be used for new
	 room-service orders.

Check-in dates cannot be in the past. The backend date picker disables past
dates, and checkout must be at least one day after check-in. The public form
uses the browser date picker and applies the same server-side validation.

## Public and Portal URLs

| URL | Access | Purpose |
| --- | --- | --- |
| `/hotel/book` | Public | Booking form |
| `/hotel/rooms/<category_id>` | Public | JSON room list for a category |
| `/hotel/book/submit` | Public POST | Submit a booking request |
| `/my/reservations` | Authenticated user | List the current guest's reservations |
| `/my/reservations/<reservation_id>` | Authenticated user | View a reservation and available actions |
| `/my/reservations/<reservation_id>/order` | Authenticated user | Order food and beverages during a checked-in stay |
| `/my/reservations/<reservation_id>/feedback` | Authenticated user | Submit reservation feedback |

## Validation and Business Rules

- Guest names require first and last names using the supported Latin-letter
	format.
- Email addresses and phone numbers are validated before reservation creation.
- ID numbers must contain 4 to 32 letters, digits, hyphens, or spaces.
- The primary guest must be at least 18 years old.
- At least one adult is required; room category capacities are enforced.
- Check-out must be strictly after check-in.
- Confirmed and checked-in reservations cannot overlap for the same room.
- Rooms on maintenance hold are excluded from public room selection.
- ID uploads are limited to 5 MB and the supported file extensions.

## Main Models

- `hotel.reservation`
- `hotel.room`
- `hotel.room.category`
- `hotel.housekeeping.task`
- `hotel.room.service`
- `hotel.room.service.package.line`
- `hotel.room.service.order`
- `hotel.reservation.package`
- `hotel.reservation.package.entitlement`
- `hotel.reservation.guest`
- `hotel.reservation.feedback`

## Development

The addon contains backend assets for the checkout date picker in
`static/src/js/hotel_date_widgets.js`. After changing backend JavaScript,
restart Odoo and refresh assets in the browser. A module upgrade is usually
enough for Python, XML, and manifest changes.

Useful validation commands:

```bash
python3 -m py_compile custom_addons/hotel_management/**/*.py
python3 -c "import xml.etree.ElementTree as ET; ET.parse('custom_addons/hotel_management/views/website_templates.xml')"
testvenv/bin/python ./odoo-bin -c ./odoo.conf -u hotel_management \
		-d <database> --stop-after-init
```

## License

LGPL-3.
