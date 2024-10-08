# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import api, fields, models

class axisTicketType(models.Model):
    _name = "axis.helpdesk.ticket.type"
    _description = "Helpdesk Ticket Type"

    def _default_domain_member_ids(self):
        return [('groups_id', 'in', self.env.ref('website_axis_helpdesk_advance.group_helpdesk_ticket_users').id)]

    name = fields.Char(string="Name", required=True)
    type_based_on = fields.Selection([
        ('helpdesk_team', 'Helpdesk Team'), 
        ('users', 'Users')
    ], string="Type Based On", default="helpdesk_team")
    team_ids = fields.Many2many("axis.helpdesk.ticket.team", string="Helpdesk Teams")
    user_ids = fields.Many2many('res.users', string="Users", domain=lambda self: self._default_domain_member_ids())
    email_domain = fields.Char(string='Email Domain')
    email_ids = fields.Many2many('res.partner', string="Specific Emails")
    
    @api.model
    def fields_view_get(self, view_id=None, view_type='form', toolbar=False, submenu=False):
        res = super(axisTicketType, self).fields_view_get(view_id=view_id, view_type=view_type, toolbar=toolbar, submenu=submenu)
        user_email = self.env.user.email
        if user_email:
            domain = user_email.split('@')[-1]
            allowed_ticket_types = self.search([
                '|', 
                ('email_domain', '=', domain), 
                ('email_ids', 'in', self.env.user.partner_id.id)
            ])
            res['arch'] = res['arch'].decode('utf-8')
            res['arch'] = res['arch'].replace('<tree>', '<tree domain="[\'|\', (\'id\', \'in\', %s)]">' % allowed_ticket_types.ids)
        return res

