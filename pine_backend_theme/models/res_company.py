from odoo import models, fields


class ResCompany(models.Model):
    
    _inherit = 'res.company'
    
    #----------------------------------------------------------
    # Fields
    #----------------------------------------------------------

    hero_section_bg = fields.Binary(
        string='Hero Section Background Image',
        attachment=True
    )

    login_page_logo = fields.Binary(
        string='Login Page Logo',
        attachment=True
    )

    login_left_panel_bg_image = fields.Binary(
        string='Login Left Side Panel Background Image',
        attachment=True
    )

    left_bg_image = fields.Binary(
        string='Brand Header Background Image',
        attachment=True
    )

    motto = fields.Char(
        string='Company Motto',
        default=''
    )
