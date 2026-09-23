from odoo import api, fields, models
from odoo.exceptions import ValidationError

class Book(models.Model):
  _name = "book.book"
  _description = "Book"
  _inherit  = ["mail.thread", "mail.activity.mixin"]
  
  name = fields.Char(required=True, index=True)
  author_id = fields.Many2one(
    "book.author",
    required=True,
    ondelete="restrict",
  )
  isbn=fields.Char(required=True, copy=False,)
  category_id = fields.Many2one(
    "book.category",
    required=True,
    help="Select the category this bokk belongs to.",
  )
  price = fields.Float(digits="Product Price")
  publication_date = fields.Date(
    default=fields.Date.today,
  )
  
  state=fields.Selection(
    [
      ("draft", "Draft"),
      ("available", "Available"),
      ("unavailable", "Unavailable"),
    ],
    default="draft",
    tracking=True,
  )
  
  description=fields.Html(translate=True,)
  
  _sql_constraints = [
    (
      "isbn_unique",
      "UNIQUE(isbn)",
      "The ISBN must be unique.",
    )
  ]
  
  @api.constrains("price")
  def _check_price(self):
    for record in self:
      if record.price < 0:
        raise ValidationError("The book price cannot be negative.")


