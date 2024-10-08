# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import api, fields, models

class axisHelpdeskCategory(models.Model):
    _name = "axis.helpdesk.ticket.category"

    name = fields.Char(string="Name", required=1)
    active = fields.Boolean(string="Active", default=1 )
    company_id = fields.Many2one("res.company",string="Company",default=lambda self: self.env.company)

