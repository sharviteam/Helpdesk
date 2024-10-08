# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import api, fields, models


class AccountMove(models.Model):
    _inherit = 'account.move'

    invoice_ticket_id = fields.Many2one('axis.helpdesk.ticket')
    timesheet_id = fields.Many2one('account.analytic.line')
    account_move_ticket_ids = fields.Many2many('axis.helpdesk.ticket', compute='_compute_invoice_ticket_ids', string='Ticket associated to this sale')
    ticket_count = fields.Integer("Ticket Count",compute='_compute_invoice_ticket_ids', groups="website_axis_helpdesk_advance.group_invoice_helpdesk_ticket")
    inv_timesheet_ids = fields.Many2many('account.analytic.line', compute='_compute_timesheet_ids', store=1)
    inv_timesheet_id = fields.Many2one('account.analytic.line', string="Timsheet")
    inv_timesheet_count = fields.Integer("Timesheet Count", compute='_compute_timesheet_ids')

    @api.depends('inv_timesheet_id')
    def _compute_timesheet_ids(self):
        for timesheet in self:
            timesheet.inv_timesheet_ids = self.env['account.analytic.line'].search(
                [('invoice_timesheet_id', '=', timesheet.id)])
            timesheet.inv_timesheet_count = len(timesheet.inv_timesheet_ids)

    def action_view_invoice_timesheet(self):
        view_form_id = self.env.ref('hr_timesheet.hr_timesheet_line_form').id
        view_list_id = self.env.ref('hr_timesheet.hr_timesheet_line_tree').id
        action = {
            'type': 'ir.actions.act_window',
            'domain': [('id', 'in', self.inv_timesheet_ids.ids)],
            'view_mode': 'list,form',
            'name': ('Timsheet'),
            'res_model': 'account.analytic.line',
        }
        if len(self.inv_timesheet_ids) == 1:
            action.update({'views': [(view_form_id, 'form')], 'res_id': self.inv_timesheet_ids.id})
        else:
            action['views'] = [(view_list_id, 'list'), (view_form_id, 'form')]
        return action

    @api.depends('invoice_ticket_id')
    def _compute_invoice_ticket_ids(self):
        for acc_move in self:
            acc_move.ticket_count = 0
            acc_move.account_move_ticket_ids =False
            ticket_id = self.env['axis.helpdesk.ticket'].search(
                [('account_invoice_ids', '=', acc_move.id)])
            if ticket_id:
                for ticket in ticket_id:
                    acc_move.ticket_count = len(ticket)
                    acc_move.account_move_ticket_ids = ticket

    def action_view_invoice_ticket(self):
        view_form_id = self.env.ref('website_axis_helpdesk_advance.axis_helpdesk_ticket_form').id
        view_list_id = self.env.ref('website_axis_helpdesk_advance.axis_helpdesk_ticket_tree').id
        action = {
            'type': 'ir.actions.act_window',
            'domain': [('id', 'in', self.account_move_ticket_ids.ids)],
            'view_mode': 'list,form',
            'name': ('Helpdesk Ticket'),
            'res_model': 'axis.helpdesk.ticket',
        }
        if len(self.account_move_ticket_ids) == 1:
            action.update({'views': [(view_form_id, 'form')], 'res_id': self.account_move_ticket_ids.id})
        else:
            action['views'] = [(view_list_id, 'list'), (view_form_id, 'form')]
        return action



