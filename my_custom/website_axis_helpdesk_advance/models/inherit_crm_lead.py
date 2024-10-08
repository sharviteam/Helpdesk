# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import api, fields, models


class CrmLead(models.Model):
    _inherit = 'crm.lead'

    crm_ticket_id = fields.Many2one('axis.helpdesk.ticket')
    crm_ticket_ids = fields.Many2many('axis.helpdesk.ticket', compute='_compute_axis_ticket_ids', string='Ticket associated to this CRM Lead')
    ticket_count = fields.Integer("Ticket Count",compute='_compute_axis_ticket_ids', groups="website_axis_helpdesk_advance.group_crm_helpdesk_ticket")

    @api.depends('crm_ticket_id')
    def _compute_axis_ticket_ids(self):
        for order in self:
            order.ticket_count = 0
            order.crm_ticket_ids = False
            ticket_id = self.env['axis.helpdesk.ticket'].search(
                [('crm_lead_ids', '=', order.id)])
            for ticket in ticket_id:
                order.ticket_count = len(ticket)
                order.crm_ticket_ids = ticket

    def action_view_ticket(self):
        view_form_id = self.env.ref('website_axis_helpdesk_advance.axis_helpdesk_ticket_form').id
        view_list_id = self.env.ref('website_axis_helpdesk_advance.axis_helpdesk_ticket_tree').id
        action = {
            'type': 'ir.actions.act_window',
            'domain': [('id', 'in', self.crm_ticket_ids.ids)],
            'view_mode': 'list,form',
            'name': ('Helpdesk Ticket'),
            'res_model': 'axis.helpdesk.ticket',
        }
        if len(self.crm_ticket_ids) == 1:
            action.update({'views': [(view_form_id, 'form')], 'res_id': self.crm_ticket_ids.id})
        else:
            action['views'] = [(view_list_id, 'list'), (view_form_id, 'form')]
        return action