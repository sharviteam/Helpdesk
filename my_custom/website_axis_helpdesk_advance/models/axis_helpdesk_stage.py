# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import api, fields, models

class axisHelpdeskStage(models.Model):
    _name = "axis.helpdesk.stage"

    def _default_team_ids(self):
        team_id = self.env.context.get('default_team_id')
        if team_id:
            return [(4, team_id, 0)]

    name = fields.Char(string="Name",required=1)
    is_close = fields.Boolean('Closing Stage')
    mail_template_id = fields.Many2one("mail.template",string="Email Template",domain="[('model', '=', 'axis.helpdesk.ticket')]",)
    folded_kanban = fields.Boolean(string="Folded in Kanban")
    description = fields.Html(string="Description", translate=True, sanitize_style=True)
    sequence = fields.Integer(default=True)
    active = fields.Boolean(default=True)
    not_start = fields.Boolean(string="Not Started")
    closed = fields.Boolean(string="Closed")
    company_id = fields.Many2one("res.company",string="Company", default=lambda self: self.env.company)
    team_ids = fields.Many2many('axis.helpdesk.ticket.team', relation='team_stage_rel', string='Team',default=_default_team_ids)
