# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import api, fields, models
import datetime

class ProjectProject(models.Model):
    _inherit = "project.project"

    rate_per_hour = fields.Float("Rate Per Hour")

class TimesheetLine(models.Model):
    _inherit = "account.analytic.line"

    invoice_timesheet_ids = fields.Many2many('account.move', compute='_compute_move_timesheet_ids', store=1)
    invoice_timesheet_id = fields.Many2one('account.move')
    invoice_timesheet_count = fields.Integer("Account Move Count", compute='_compute_move_timesheet_ids')

    @api.depends('invoice_timesheet_id')
    def _compute_move_timesheet_ids(self):
        for timesheet in self:
            timesheet.invoice_timesheet_ids = self.env['account.move'].search(
                [('timesheet_id', '=', timesheet.id)])
            timesheet.invoice_timesheet_count = len(timesheet.invoice_timesheet_ids)

    def action_view_invoice_timesheet(self):
        view_form_id = self.env.ref('account.view_move_form').id
        view_list_id = self.env.ref('account.view_invoice_tree').id
        action = {
            'type': 'ir.actions.act_window',
            'domain': [('id', 'in', self.invoice_timesheet_ids.ids)],
            'view_mode': 'list,form',
            'name': ('Account Invoice'),
            'res_model': 'account.move',
        }
        if len(self.invoice_timesheet_ids) == 1:
            action.update({'views': [(view_form_id, 'form')], 'res_id': self.invoice_timesheet_ids.id})
        else:
            action['views'] = [(view_list_id, 'list'), (view_form_id, 'form')]
        return action