# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import models, api, fields, _

class WhatsappSendMessage(models.TransientModel):

    _name = 'whatsapp.message.wizard'
    _description = "Whatsapp Wizard"

    user_id = fields.Many2one('res.partner', string="Recipient",readonly=1,force_save=1)
    mobile = fields.Char(readonly=1, force_save=1,required=1)
    message = fields.Text(string="message", required=True)
    helpdesk_id = fields.Many2one('axis.helpdesk.ticket',readonly=1,force_save=1)

    def send_message(self):
        selected_ids = self.env.context.get('active_ids', [])
        selected_records = self.env['axis.helpdesk.ticket'].browse(selected_ids)
        if self.message and selected_records.partner_id.mobile:
            message_string = ''
            message = self.message.split(' ')
            for msg in message:
                message_string = message_string + msg + '%20'
            message_string = message_string[:(len(message_string) - 3)]
            return {
                'type': 'ir.actions.act_url',
                'url': "https://web.whatsapp.com/send?phone="+selected_records.partner_id.mobile+"&text=" + message_string,
                'target': 'new',
                'res_id': self.id,
            }