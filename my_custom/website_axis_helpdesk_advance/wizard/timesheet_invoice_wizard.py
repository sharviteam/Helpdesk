# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import api, fields, models, _
import datetime

class TimesheetInvoice(models.TransientModel):
    _name = "timesheet.invoice.confirm"

    def confirm_create_invoice(self):
        message_id = self.env['timesheet.invoice.confirm'].create(
            {'name': 'Are you sure you want to create invoice record !'})
        return {
            'name': 'Confirmation',
            'type': 'ir.actions.act_window',
            'view_mode': 'form',
            'res_model': 'timesheet.invoice.confirm',
            'res_id': message_id.id,
            'target': 'new'
        }
    name = fields.Char("Name", readonly=1, force_save=1,deafult=confirm_create_invoice)

    def Create(self):
        selected_ids = self.env.context.get('active_ids', [])
        selected_records = self.env['account.analytic.line'].sudo().browse(selected_ids)
        account = self.env['account.account'].search([('company_id', '=', self.env.company.id)], limit=1)
        for timesheet_data in selected_ids:
            timesheet_id = self.env['account.analytic.line'].sudo().search([('id','=',timesheet_data)])
            move = self.env['account.move'].create({
                'type': 'out_invoice',
                'partner_id': timesheet_id.project_id.partner_id.id,
                'invoice_date': datetime.datetime.now(),
                'timesheet_id':timesheet_data,
            })
            msg = "Date:"+str(timesheet_id.date) + " Time Spent(Hours): "+ str(timesheet_id.project_id.rate_per_hour)+" Timesheet Info :"+ timesheet_id.name
            move.write({
                'invoice_line_ids': [
                    (0, 0, {
                        'name': msg,
                        'quantity': timesheet_id.unit_amount,
                        'price_unit': timesheet_id.project_id.rate_per_hour or 0.0,
                        'move_id': move.id,
                        'account_id': account.id,
                        'price_subtotal': float(timesheet_id.unit_amount * timesheet_id.project_id.rate_per_hour),
                    }),
                ]
            })
            timesheet_id.write({'invoice_timesheet_id':move.id})
