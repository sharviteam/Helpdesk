# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import api, fields, models, _
from odoo.exceptions import UserError, ValidationError

class MassCloseHelpdeskTicket(models.TransientModel):
    _name ="wizard.helpdesk.ticket.mass.close"

    update_for = fields.Selection([('none','None'),('close_tickets','Close Tickets'),('update_team_user','Update Team And User')],default='close_tickets')
    stage_id = fields.Many2one('axis.helpdesk.stage', string='Stage', domain="[('is_close', '=', True)]")
    team_id = fields.Many2one('axis.helpdesk.ticket.team',string='Helpdesk Team')
    user_id = fields.Many2one(
        'res.users', string='Assigned to', compute='_compute_user_and_stage_ids', store=True,
        readonly=False, tracking=True,
        domain=lambda self: [('groups_id', 'in', self.env.ref('website_axis_helpdesk_advance.group_helpdesk_ticket_users').id)])

    @api.depends('team_id')
    def _compute_user_and_stage_ids(self):
        for ticket in self.filtered(lambda ticket: ticket.team_id):
            if not ticket.user_id:
                ticket.user_id = ticket.team_id.assign_user_to_team()[ticket.team_id.id]
            if not ticket.stage_id or ticket.stage_id not in ticket.team_id.stage_ids:
                ticket.stage_id = ticket.team_id._ticket_stage_define()[ticket.team_id.id]

    def update_ticket(self):
        selected_ids = self.env.context.get('active_ids', [])
        selected_records = self.env['axis.helpdesk.ticket'].browse(selected_ids)
        if self.update_for == "close_tickets":
            for ticket in selected_records:
                ticket.update({'stage_id': self.stage_id.id})
        elif self.update_for == "update_team_user":
            for ticket in selected_records:
                ticket.update({'helpdesk_team_id': self.team_id.id,
                               'res_user_id':self.user_id.id})

        message_id = self.env['message.wizard'].create({'name': 'Are you sure you want to update record !'})
        return {
            'name': 'Confirmation',
            'type': 'ir.actions.act_window',
            'view_mode': 'form',
            'res_model': 'message.wizard',
            'res_id': message_id.id,
            'target': 'new'
        }
