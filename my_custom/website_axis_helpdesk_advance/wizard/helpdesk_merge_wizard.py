# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import api, fields, models, _
from odoo.exceptions import UserError, ValidationError

class MergeHelpdeskTicket(models.TransientModel):
    _name ="wizard.helpdesk.ticket.merge"

    user_id = fields.Many2one(
        'res.users', string='Assigned to', compute='_compute_user_and_stage_ids', store=True,
        readonly=False, tracking=True,
        domain=lambda self: [('groups_id', 'in', self.env.ref('website_axis_helpdesk_advance.group_helpdesk_ticket_users').id)])
    customer_id = fields.Many2one('res.partner',string="Customer")
    partner_email = fields.Char(string='Customer Email', compute='_compute_partner_info', store=True, readonly=False)
    name = fields.Char()
    ticket_type_id = fields.Many2one('axis.helpdesk.ticket.type', string="Ticket Type")
    tag_ids = fields.Many2many('axis.helpdesk.ticket.tag', string='Tags')
    team_id = fields.Many2one('axis.helpdesk.ticket.team', string='Helpdesk Team', index=True)
    create_new_bool = fields.Boolean(string='Create New Ticket ?')
    sure_bool = fields.Boolean(string='Are you Sure ?')
    description = fields.Text()
    stage_id = fields.Many2one(
        'axis.helpdesk.stage', string='Stage', compute='_compute_user_and_stage_ids', store=True,
        readonly=False, ondelete='restrict', tracking=True, group_expand='_read_group_stage_ids',
        copy=False, index=True, domain="[('team_ids', '=', team_id)]")

    @api.depends('customer_id')
    def _compute_partner_info(self):
        helpdesk_id = self.env['axis.helpdesk.ticket'].search([])
        for ticket in helpdesk_id:
            if ticket.partner_id:
                ticket.partner_email = self.customer_id.email

    @api.depends('team_id')
    def _compute_user_and_stage_ids(self):
        for ticket in self.filtered(lambda ticket: ticket.team_id):
            if not ticket.user_id:
                self.user_id = ticket.team_id._determine_user_to_assign()[ticket.team_id.id]
            if not ticket.stage_id or ticket.stage_id not in ticket.team_id.stage_ids:
                self.stage_id = ticket.team_id._ticket_stage_define()[ticket.team_id.id]

    @api.model
    def _read_group_stage_ids(self, stages, domain, order):
        search_ticket_id = [('id', 'in', stages.ids)]
        if self.env.context.get('default_team_id'):
            search_ticket_id = ['|', ('team_ids', 'in', self.env.context['default_team_id'])] + search_ticket_id

        return stages.search(search_ticket_id, order=order)


    def merge_ticket(self):
        selected_ids = self.env.context.get('active_ids', [])
        selected_records = self.env['axis.helpdesk.ticket'].browse(selected_ids)
        stage_id = self.env['axis.helpdesk.stage'].search([('name', '=', 'Cancelled')], limit=1)
        lst_ticket = []
        for ticket in selected_records:
            if ticket.helpdesk_stage_id.name == "Cancelled":
                raise UserError(
                    _("Selected Ticket Is Already in Cancelled State Please Select Ticket Not In Cancelled State"))
            if ticket.is_merge:
                raise UserError(_("Selected Ticket Is Already Merge"))
            ticket.update({'helpdesk_stage_id': stage_id.id})
            lst_ticket.append(ticket.id)
        if not self.sure_bool:
            raise UserError(_("Are you Sure You Want To Create Merge Ticket?"))
        if self.sure_bool:
            helpdesk_ticket = self.env['axis.helpdesk.ticket'].create({
                'name':self.name,
                'description':self.description,
                'partner_id':self.customer_id.id,
                'partner_email':self.partner_email,
                'res_user_id':self.user_id.id,
                'helpdesk_ticket_type_id':self.ticket_type_id.id,
                'helpdesk_team_id':self.team_id.id,
                'description':self.description,
                'ticket_ids': [(6, 0, lst_ticket)],
                'is_merge':True
            })
            for tickets in selected_records:
                merge_ticket = self.env['helpdesk.ticket.merge'].create(
                    {'name': tickets.name, 'ticket_id': tickets.id,'ticket_merge_id':helpdesk_ticket.id})
                merge_ticket.update({'ticket_ids':[(6,0,lst_ticket)]})
