# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import api, fields, models, _
import datetime

class HelpdeskInvoice(models.TransientModel):
    _name = "helpdesk.invoice.confirm"

    name = fields.Char("Name", readonly=1, force_save=1)
    ticket_id = fields.Many2one('axis.helpdesk.ticket', readonly=1, force_save=1)

    def create_account_move_data(self):
        self.ticket_id.create_acount_move()

        message_id = self.env['message.wizard'].create({'name': 'Are you sure you want to update record !'})
        return {
            'name': 'Confirmation',
            'type': 'ir.actions.act_window',
            'view_mode': 'form',
            'res_model': 'message.wizard',
            'res_id': message_id.id,
            'target': 'new'
        }
