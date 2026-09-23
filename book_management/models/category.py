from odoo import fields, models

class Category(models.Model):
  _name = "book.category"
  _description = "Book Category"
  
  name = fields.Char(required=True, index=True)