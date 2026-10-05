from odoo import fields, models


class ResCompany(models.Model):
    _inherit = 'res.company'

    is_hotel_branch = fields.Boolean(
        string='Hotel Branch',
        default=True,
        help='Mark this company as a hotel branch for filtering.',
    )
    branch_code = fields.Char(
        string='Branch Code',
        help='Short code for this branch, e.g. ADD, HWS.',
    )
    hotel_star_rating = fields.Selection(
        [('1', '1 Star'), ('2', '2 Star'), ('3', '3 Star'),
         ('4', '4 Star'), ('5', '5 Star')],
        string='Star Rating',
    )
    hotel_license_number = fields.Char(string='Hotel License Number')
    hotel_manager_id = fields.Many2one(
        'res.users', string='Branch Manager',
    )