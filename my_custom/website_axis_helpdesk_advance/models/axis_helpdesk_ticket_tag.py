# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import fields, models

class axisHelpdeskTicketTag(models.Model):
    _name = "axis.helpdesk.ticket.tag"
    _description = "Helpdesk Ticket Tag"

    name = fields.Char(string="Name")
    color = fields.Integer(string="Color Index")
    active = fields.Boolean(default=True)
    company_id = fields.Many2one("res.company",string="Company",default=lambda self: self.env.company)