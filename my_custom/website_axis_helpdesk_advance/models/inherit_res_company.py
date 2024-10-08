# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import api, fields, models, _
from odoo.exceptions import UserError


class ResCompany(models.Model):

    _inherit = 'res.company'

    manage_product = fields.Boolean('Manage Products', default=True)
    manage_product_selection = fields.Selection([('all', 'All'), ('manual_select_product', 'Manual Select Product')], string="Status",default="all")
    product_ids = fields.Many2many('product.product', 'company_product_product', 'company_id', 'product_id', string="Products")
    manual_boolean = fields.Boolean("Manual Boolean")
    helpdesk_stage_ids = fields.Many2many('axis.helpdesk.stage', 'company_helpdesk_stage', 'company_stage_id', 'com_stage_id',
                                 string="Stages")
    manage_whatsapp_features = fields.Boolean('Helpdesk Whatsapp features ', default=False,implied_group='website_axis_helpdesk_advance.group_whatsapp')
