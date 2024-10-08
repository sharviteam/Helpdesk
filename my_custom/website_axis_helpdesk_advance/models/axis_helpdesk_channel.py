# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import fields, models

class HelpdeskTicketChannel(models.Model):
    _name = "axis.helpdesk.channel"
    _description = "Helpdesk Channel"

    name = fields.Char(required=True)
    active = fields.Boolean(default=True)
    company_id = fields.Many2one("res.company",string="Company",default=lambda self: self.env.company)
