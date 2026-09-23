from odoo import fields, models

class BookAuthor(models.Model):
  _name = "book.author"
  _description = "Book Author"
  
  name=fields.Char(required=True, index=True)