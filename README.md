# Custom Odoo Addons

Custom Odoo 18 modules developed for extending and customizing the Odoo ERP system.

## Modules

* **Book Management**: Manage books, authors, categories, and related information.
* **Hotel Management**: Hotel and hospitality management functionality.
* **MuK Web Customizations**: UI, theme, sidebar, chatter, dialog, and color customizations.

## Requirements

* Odoo 18.0
* Python 3.12+
* PostgreSQL

## Installation

Clone the repository into your Odoo custom addons directory:

```bash
git clone https://github.com/kitessafikadu/ohms.git
```

Add the addons directory to `addons_path` in `odoo.conf`:

```ini
addons_path = /path/to/odoo/addons,/path/to/custom_addons
```

Restart Odoo, activate Developer Mode, update the Apps list, and install the required modules.

## Development

```bash
cd custom_addons
git checkout main
```

Each module is maintained as an independent Odoo addon.

## License

LGPL-3.0
