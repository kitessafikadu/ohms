{
    "name": "Book Management",
    "version": "18.0.1.0.0",
    "category": "Library",
    "summary": "Manage books, authors, and categories",
    "license": "LGPL-3",
    "depends": ["base", "mail"],
    "data": [
        "security/security_groups.xml",
        "security/ir.model.access.csv",
        "views/book_views.xml",
        "views/author_views.xml",
        "views/category_views.xml",
        "views/menu_views.xml",
    ],
    "application": True,
    "installable": True,
}