# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import api, fields, models, _
from odoo.exceptions import UserError


class ResConfigSettings(models.TransientModel):

    _inherit = 'res.config.settings'

    is_attachment = fields.Boolean('Allow Attachment', default=False, config_parameter='axis_helpdesk_advance.is_attachment')
    manage_product = fields.Boolean('Manage Products', default=True)
    manage_product_selection = fields.Selection([('all', 'All'), ('manual_select_product', 'Manual Select Product')], string="Status",default="all")
    product_ids = fields.Many2many('product.product', 'config_product_product', 'config_id', 'product_id', string="Products")
    manual_boolean = fields.Boolean("Manual Boolean")
    helpdesk_stage_ids = fields.Many2many('axis.helpdesk.stage', 'config_helpdesk_stage', 'config_stage_id',
                                          'conf_stage_id',string="Stages",)
    company_id = fields.Many2one('res.company', string='Company',
                                 default=lambda self: self.env.user.company_id, readonly=True)
    manage_whatsapp_features = fields.Boolean('Helpdesk Whatsapp features ', default=False,implied_group='website_axis_helpdesk_advance.group_whatsapp')



    @api.onchange('manage_product_selection')
    def _onchnage_manage_product_selection(self):
        if self.manage_product_selection == "manual_select_product":
            self.manual_boolean = True
        else:
            self.manual_boolean = False

    @api.onchange('company_id')
    def onchange_company_id(self):
        self.manage_product = self.company_id.manage_product
        self.manage_product_selection = self.company_id.manage_product_selection
        self.manual_boolean = self.company_id.manual_boolean
        self.product_ids = self.company_id.product_ids
        self.helpdesk_stage_ids = self.company_id.helpdesk_stage_ids
        self.manage_whatsapp_features = self.company_id.manage_whatsapp_features

    def set_values(self):
        self.ensure_one()
        super(ResConfigSettings, self).set_values()
        self.company_id.manage_product = self.manage_product
        self.company_id.manage_product_selection = self.manage_product_selection
        self.company_id.product_ids = self.product_ids
        self.company_id.helpdesk_stage_ids = self.helpdesk_stage_ids
        self.company_id.manage_whatsapp_features = self.manage_whatsapp_features
