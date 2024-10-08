# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import api, fields, models, _, tools
import calendar as cal
from datetime import timedelta
import datetime
import re
from datetime import date
from email.utils import formataddr

TICKET_PRIORITY = [
    ('0', 'All'),
    ('1', 'Low priority'),
    ('2', 'High priority'),
    ('3', 'Urgent'),
    ('4', 'High'),
]

class axisHelpdeskTicketInvoice(models.Model):
    _name = 'helpdesk.ticket.invoice'
    _description = "Helpdesk Ticket Invoice"

    product_id = fields.Many2one('product.product', 'Product',required=True)
    name = fields.Char(related='product_id.name',string='Lable',required=True)
    tax = fields.Char(string='Tax')
    quantity = fields.Float('Quantity')
    price_unit = fields.Float(compute='_compute_abcd',string='Price',store=True)
    ticket_id = fields.Many2one('axis.helpdesk.ticket', 'First')

    @api.depends('quantity')
    def _compute_abcd(self):
        for record in self:
            search = record.env['product.product'].sudo().search([('name','=',record.product_id.name)])
            for rec in search:
                record.price_unit = record.quantity * rec.list_price

    @api.onchange('product_id')
    def _onchange_tax(self):
        for record in self:
            search = record.env['product.product'].sudo().search([('name','=',record.product_id.name)])
            for rec in search:
                record.tax =search.taxes_id.name

class AccountAnalyticLine(models.Model):
    _inherit = 'account.analytic.line'

    ticket_id = fields.Many2one('axis.helpdesk.ticket', 'Ticket')

class axisHelpdeskTicket(models.Model):
    _name = "axis.helpdesk.ticket"


    _description = 'Helpdesk Ticket'
    _rec_name = "number"
    _order = 'priority desc, id desc'
    _primary_email = 'partner_email'
    _inherit = [
        'portal.mixin',
        'mail.thread.cc',
        'utm.mixin',
        'rating.mixin',
        'mail.activity.mixin',
        'mail.tracking.duration.mixin',
    ]
    _track_duration_field = 'stage_id'

    def _default_helpdesk_stage_id(self):
        return [(0, 0, {'name': 'New', 'sequence': 0,
                        'template_id': self.env.ref('website_axis_helpdesk_advance.axis_helpdesk_ticket_new_create',
                                                    raise_if_not_found=False) or None})]

    @api.model
    def group_helpdesk_stage_ids(self, stages, domain, order):
        helpdesk_stage_ids = self.env["axis.helpdesk.stage"].search([])
        return helpdesk_stage_ids

    def _manage_product_config(self):
        config_id = self.env['res.config.settings'].search([], limit=1, order='id desc')
        if config_id.manage_product:
            self.product_boolean = True

    @api.onchange('product_ids')
    def _product_select_helpdesk(self):
        res = {}
        config_id = self.env['res.config.settings'].search([], limit=1, order='id desc')
        if config_id.manage_product:
            self.product_boolean = True
            if config_id.manage_product_selection == "all":
                lst = []
                for product_ids_all in self.env['product.product'].search([]):
                    lst.append(product_ids_all.id)
                res['domain'] = {'product_ids': [('id', 'in', lst)]}
            elif config_id.manage_product_selection == "manual_select_product":
                lst_prod = []
                for product in config_id.product_ids:
                    product_id = self.env['product.product'].search([('id', '=', product.id)])
                    lst_prod.append(product_id.id)
                res['domain'] = {'product_ids': [('id', 'in', lst_prod)]}
            return res
        else:
            self.product_boolean = True

    name = fields.Char(string="Name",required=1)
    client_id = fields.Many2one("res.users", string="Contact")
    number = fields.Char(string="Ticket number", default="/", readonly=True)
    team_id = fields.Many2one("axis.helpdesk.ticket.team",string="Helpdesk Team")
    helpdesk_team_id = fields.Many2one("axis.helpdesk.ticket.team",string="Helpdesk Team")
    helpdesk_stage_id = fields.Many2one("axis.helpdesk.stage",string="Stage",group_expand="group_helpdesk_stage_ids",default=_default_helpdesk_stage_id,
        track_visibility="onchange",ondelete="restrict",index=True,copy=False,)
    helpdesk_ticket_type_id = fields.Many2one('axis.helpdesk.ticket.type', string="Ticket Type")
    res_user_id = fields.Many2one("res.users", string="Assigned user", tracking=True, index=True)
    not_start = fields.Boolean(related="helpdesk_stage_id.not_start", store=True)
    priority = fields.Selection([("0", ("Low")),("1", ("Medium")),("2", ("High")),("3", ("Very High"))],string="Ticket Priority",default="1")
    partner_id = fields.Many2one("res.partner", string="Contact")
    partner_name = fields.Char(string="Partner",readonly=1,force_save=1)
    partner_email = fields.Char(string="Email",readonly=1,force_save=1)
    last_stage_update = fields.Datetime(string="Last Stage Update", default=fields.Datetime.now)
    active = fields.Boolean(default=True)
    res_user_ids = fields.Many2many('res.users', string='Assigned Users')
    user_ids = fields.Many2many("res.users", related="helpdesk_team_id.res_user_ids", string="Users")
    company_id = fields.Many2one("res.company",string="Company",required=True,default=lambda self: self.env.company)
    description = fields.Html(required=True, sanitize_style=True)
    assigned_date = fields.Datetime(string="Assigned Date")
    closed_date = fields.Datetime(string="Closed Date")
    closed = fields.Boolean(related="helpdesk_stage_id.closed")
    team_sla = fields.Boolean(string="Team SLA", compute="_compute_team_sla")
    sla_ids = fields.Many2many('axis.helpdesk.ticket.sla.policy', 'helpdesk_sla_policy', 'ticket_id', 'sla_policy_id', string="SLAs", copy=False)
    sla_expired = fields.Boolean(string="SLA expired")
    helpdesk_sla_deadline = fields.Datetime(string="SLA deadline")
    helpdesk__sla_late = fields.Boolean("Has SLA reached late", compute='_compute_helpdesk__sla_late', compute_sudo=True,
                                      store=True)
    helpdesk_sla_state = fields.One2many('helpdesk.sla.status', 'ticket_id', string="SLA Status")
    ticket_channel_helpdesk_id = fields.Many2one("axis.helpdesk.channel",string="Channel")
    date = fields.Date('Created on', default=fields.Date.today())
    closed_hours = fields.Integer("Time to close (hours)", compute='helpdesk_ticket_close_hour', store=True)
    ticket_attach__no = fields.Integer(compute='_compute_ticket_attach__no', string="Number of Attachments")
    product_boolean = fields.Boolean()
    res_config_id = fields.Many2one('res.config.setting', deafult=_manage_product_config)
    product_ids = fields.Many2many('product.product', 'helpdesk_product_product', 'ticket_id', 'product_id',
                                   string="Products", deafult=_product_select_helpdesk)
    account_invoice_id = fields.Many2one('account.move')
    invoice_id = fields.Many2one('axis.helpdesk.ticket')
    account_invoice_ids = fields.Many2many('account.move', compute='_compute_invoice_ids', store=1,
                                      string='Invoice associated to this Ticket')
    invoice_count = fields.Integer("Invoice Count", compute='_compute_invoice_ids',
                                groups="website_axis_helpdesk_advance.group_invoice_helpdesk_ticket")
    sale_order_id = fields.Many2one('sale.order')
    sale_id = fields.Many2one('axis.helpdesk.ticket')
    sale_order_ids = fields.Many2many('sale.order', compute='_compute_sale_ids', store=1,
                                           string='Sale associated to this Ticket')
    sale_count = fields.Integer("Sale Count", compute='_compute_sale_ids',
                                   groups="website_axis_helpdesk_advance.group_sale_helpdesk_ticket")

    purchase_order_id = fields.Many2one('purchase.order')
    purchase_id = fields.Many2one('axis.helpdesk.ticket')
    purchase_order_ids = fields.Many2many('purchase.order', compute='_compute_purchase_ids', store=1,
                                      string='Purchase associated to this Ticket')
    purchase_count = fields.Integer("Purchase Count", compute='_compute_purchase_ids',
                                groups="website_axis_helpdesk_advance.group_purchase_helpdesk_ticket")
    crm_lead_id = fields.Many2one('crm.lead')
    crm_lead_ids = fields.Many2many('crm.lead', compute='_compute_crm_ids', store=1,
                                    string='CRM Lead associated to this Ticket')
    crm_count = fields.Integer("CRM Count", compute='_compute_crm_ids',
                                    groups="website_axis_helpdesk_advance.group_crm_helpdesk_ticket")
    crm_ticket_id = fields.Many2one("crm.lead")

    ticket_ids = fields.Many2many('helpdesk.ticket.merge', string="Tickets",compute='_compute_ticket_ids')
    ticket_count = fields.Integer("Ticket Count", compute='_compute_ticket_ids')
    merge_id = fields.Many2one('helpdesk.ticket.merge')
    is_merge = fields.Boolean()
    reopened_desc = fields.Text(string="Ticket Reopened Reason")
    re_open_bool = fields.Boolean()
    attachment_number = fields.Integer(compute='_compute_attachment_number', string="Number of Attachments")
    is_task = fields.Boolean()
    is_task_button = fields.Boolean()
    ticket_timesheet_ids = fields.One2many('account.analytic.line','ticket_id','Timesheet')
    ticket_invoice_ids = fields.One2many('helpdesk.ticket.invoice', 'ticket_id', 'Ticket Invoice')
    priority_new = fields.Selection(TICKET_PRIORITY, string='Customer Rating', default='0')
    comment = fields.Text(string='Comment')
    create_new_bool = fields.Boolean(string='Create New Ticket ?')
    assign_date = fields.Datetime("First assignation date")
    assign_hours = fields.Integer("Time to first assignation (hours)", compute='helpdesk_ticket_compute_assign_hr', store=True)
    date_last_stage_update = fields.Datetime("Last Stage Update", copy=False, readonly=True)
    project_project_id = fields.Many2one('project.project', string="Project")
    tag_ids = fields.Many2many('axis.helpdesk.ticket.tag', string='Tags')
    closed_by_partner = fields.Boolean('Closed by Partner')
    attachment_ids = fields.Many2many('ir.attachment', 'attachment_id', 'helpdesk_res_id',
                                      string="Attachment",
                                      help='You can attach the copy of your document', copy=False)
    is_ticket_closed = fields.Boolean(string='Is Ticket Closed')
    close_ticket_date = fields.Datetime(string='Close Ticket')
    is_customer_replied = fields.Boolean(string='Is Customer Replied')
    ticket_sla_policy_fail = fields.Boolean("Failed SLA Policy", compute='_compute_ticket_sla_policy_fail', search='_search_ticket_sla_policy_fail')
    ticket_sla_policy_success = fields.Boolean("Success SLA Policy", compute='_compute_ticket_sla_policy_success', search='_search_ticket_sla_policy_success')
    color = fields.Integer('Color Index', default=1)
    helpdesk_ticket_state = fields.Selection([
        ('normal', 'Grey'),
        ('done', 'Green'),
        ('blocked', 'Red')], string='Kanban State',
        default='normal', required=True)
    helpdesk_ticket_state_label = fields.Char(compute='_compute_helpdesk_ticket_state_label', string='Column Status', tracking=True)

    helpdesk_ticket_blocked = fields.Char(
        'Red Kanban Label', default=lambda s: _('Blocked'), translate=True, required=True)
    helpdesk_ticket_done = fields.Char(
        'Green Kanban Label', default=lambda s: _('Ready'), translate=True, required=True)
    helpdesk_ticket_normal = fields.Char(
        'Grey Kanban Label', default=lambda s: _('In Progress'), translate=True, required=True)
    is_invoice = fields.Boolean()
    ticket_invoice_ids = fields.One2many('helpdesk.ticket.invoice', 'ticket_id', 'Ticket Invoice')
    is_invoice_button = fields.Boolean()
    invoice_number = fields.Char(string="Invoice Number")
    account_detail = fields.Many2one('account.move', string='Account', track_visibility='onchange')
    account_total_data = fields.Float(string='Invoice Amount')
    based_on_ticket_type = fields.Boolean(string="Based on Ticket Type")
    domain_user_ids = fields.Many2many('res.users', compute='_compute_domain_user_ids')
    ticket_deadline = fields.Datetime("Ticket Deadline", tracking=True)
    esitmated_hours = fields.Integer("Estimated Hours")

    def _compute_attachment_number(self):
        read_group_res = self.env['ir.attachment'].read_group(
            [('res_model', '=', 'axis.helpdesk.ticket'), ('res_id', 'in', self.ids)],
            ['res_id'], ['res_id'])
        attach_data = {res['res_id']: res['res_id_count'] for res in read_group_res}
        for record in self:
            record.attachment_number = attach_data.get(record.id, 0)

    @api.depends('helpdesk_team_id')
    def _compute_domain_user_ids(self):
        for task in self:
            if task.helpdesk_team_id and task.helpdesk_team_id.visibility_res_user_ids:
                helpdesk_manager = self.env['res.users'].search(
                    [('groups_id', 'in', self.env.ref('website_axis_helpdesk_advance.group_helpdesk_ticket_users').id)])
                task.domain_user_ids = [(6, 0, (helpdesk_manager + task.helpdesk_team_id.visibility_res_user_ids).ids)]
            else:
                helpdesk_users = self.env['res.users'].search(
                    [('groups_id', 'in', self.env.ref('website_axis_helpdesk_advance.group_helpdesk_ticket_users').id)]).ids
                task.domain_user_ids = [(6, 0, helpdesk_users)]

    def invoice_action(self):
        self.is_invoice_button = True
        search_invoice = self.env['account.move'].search([('partner_id', '=', self.partner_id.id),
                                                          ('id', '=', self.invoice_number)])

        self.account_detail = search_invoice.id
        self.account_total_data = search_invoice.amount_residual

        return {
            'name': _('Create Invoice'),
            'view_mode': 'form',
            'res_model': 'account.move',
            'res_id': search_invoice.id,
            'type': 'ir.actions.act_window',
        }

    @api.depends('helpdesk_stage_id', 'helpdesk_ticket_state')
    def _compute_helpdesk_ticket_state_label(self):
        for task in self:
            if task.helpdesk_ticket_state == 'normal':
                task.helpdesk_ticket_state_label = task.helpdesk_ticket_normal
            elif task.helpdesk_ticket_state == 'blocked':
                task.helpdesk_ticket_state_label = task.helpdesk_ticket_blocked
            else:
                task.helpdesk_ticket_state_label = task.helpdesk_ticket_done

    @api.depends('helpdesk_sla_deadline', 'helpdesk__sla_late')
    def _compute_ticket_sla_policy_fail(self):
        now = fields.Datetime.now()
        for ticket in self:
            if ticket.helpdesk_sla_deadline:
                ticket.ticket_sla_policy_fail = (ticket.helpdesk_sla_deadline < now) or ticket.helpdesk__sla_late
            else:
                ticket.ticket_sla_policy_fail = ticket.helpdesk__sla_late

    @api.depends('helpdesk_sla_deadline', 'helpdesk__sla_late')
    def _compute_ticket_sla_policy_success(self):
        now = fields.Datetime.now()
        for ticket in self:
            ticket.ticket_sla_policy_success = (ticket.helpdesk_sla_deadline and ticket.helpdesk_sla_deadline > now)

    def _sla_assigning_rxeach(self):
        self.env['helpdesk.sla.status'].search([
            ('ticket_id', 'in', self.ids),
            ('reached_datetime', '=', False),
            ('deadline', '!=', False),
            ('target_type', '=', 'assigning')
        ]).write({'reached_datetime': fields.Datetime.now()})

    def close_action(self):
        self.is_ticket_closed = True
        self.closed_by_partner = True
        self.close_ticket_date = datetime.date.today()
        closing_stage = self.helpdesk_team_id._ticket_get_close_stage()
        if self.helpdesk_stage_id != closing_stage:
            self.write({'helpdesk_stage_id': closing_stage[0].id})

    def helpdesk_sal_policy_apply(self, keep_reached=False):
        sla_per_tickets = self.helpdesk_sal_policy_search()

        sla_status_value_list = []
        for tickets, slas in sla_per_tickets.items():
            sla_status_value_list += tickets.helpdesk_ticket_sla_generate_state(slas, keep_reached=keep_reached)

        sla_status_to_remove = self.mapped('helpdesk_sla_state')
        if keep_reached:
            sla_status_to_remove = sla_status_to_remove.filtered(lambda status: not status.reached_datetime)

        if sla_status_value_list:
            sla_status_to_remove.with_context(norecompute=True)

        sla_status_to_remove.unlink()
        return self.env['helpdesk.sla.status'].create(sla_status_value_list)

    def helpdesk_sal_policy_search(self):
        tickets_map = {}
        sla_domain_map = {}

        def helpdesk_ticket_generate(ticket):
            fields_list = self._helpdesk_sla_policy_reset()
            key = list()
            for field_name in fields_list:
                if ticket._fields[field_name].type == 'many2one':
                    key.append(ticket[field_name].id)
                else:
                    key.append(ticket[field_name])
            return tuple(key)

        for ticket in self:
            if ticket.helpdesk_team_id.use_sla:  # limit to the team using SLA
                key = helpdesk_ticket_generate(ticket)
                # group the ticket per key
                tickets_map.setdefault(key, self.env['axis.helpdesk.ticket'])
                tickets_map[key] |= ticket
                # group the SLA to apply, by key
                if key not in sla_domain_map:
                    sla_domain_map[key] = [('team_id', '=', ticket.helpdesk_team_id.id), ('priority', '<=', ticket.priority),
                                           ('helpdesk_stage_id.sequence', '>=', ticket.helpdesk_stage_id.sequence), '|',
                                           ('ticket_type_id', '=', ticket.helpdesk_ticket_type_id.id), ('ticket_type_id', '=', False)]

        result = {}
        for key, tickets in tickets_map.items():  # only one search per ticket group
            domain = sla_domain_map[key]
            slas = self.env['axis.helpdesk.ticket.sla.policy'].search(domain)
            result[tickets] = slas.filtered(lambda s: s.tag_ids <= tickets.tag_ids)  # SLA to apply on ticket subset
        return result

    def _sla_assigning_reach(self):
        self.env['helpdesk.sla.status'].search([
            ('ticket_id', 'in', self.ids),
            ('reached_datetime', '=', False),
            ('deadline', '!=', False),
            ('target_type', '=', 'assigning')
        ]).write({'reached_datetime': fields.Datetime.now()})


    def helpdesk_ticket_sla_generate_state(self, slas, keep_reached=False):
        status_to_keep = dict.fromkeys(self.ids, list())

        if keep_reached:
            for ticket in self:
                for status in ticket.helpdesk_sla_state:
                    if status.reached_datetime:
                        status_to_keep[ticket.id].append(status.sla_id.id)

        result = []
        for ticket in self:
            for sla in slas:
                if not (keep_reached and sla.id in status_to_keep[ticket.id]):
                    result.append({
                        'ticket_id': ticket.id,
                        'sla_id': sla.id,
                        'reached_datetime': fields.Datetime.now() if ticket.helpdesk_stage_id == sla.helpdesk_stage_id else False
                    })

        return result

    @api.depends('assign_date')
    def helpdesk_ticket_compute_assign_hr(self):
        for ticket in self:
            create_date = fields.Datetime.from_string(ticket.create_date)
            if create_date and ticket.assign_date:
                if ticket.helpdesk_team_id and ticket.helpdesk_team_id.resource_calendar_id:
                    duration_data = ticket.helpdesk_team_id.resource_calendar_id.get_work_duration_data(create_date,
                                                                                           fields.Datetime.from_string(
                                                                                               ticket.assign_date),
                                                                                           compute_leaves=True)
                    ticket.assign_hours = duration_data['hours']
                else:
                    ticket.assign_hours = False

    @api.onchange('partner_id')
    def _onchange_partner(self):
        for ticket in self:
            if ticket.partner_id:
                ticket.partner_name = ticket.partner_id.name
                ticket.partner_email = ticket.partner_id.email

    def create_task(self):
        self.is_task= True
        task_id = self.env['project.task'].create({
                'name': self.name,
                'project_id': self.project_project_id.id,
                'partner_id' : self.partner_id.id,
                'description': self.description,
                })

    def task_action(self):
        self.is_task_button = True
        search_record = self.env['project.task'].search([('name','=',self.name),('description','=',self.description),('project_id','=',self.project_project_id.id)])
        if search_record:
            return {
                'name': _('Create Task'),
                'view_mode': 'form',
                'res_model': 'project.task',
                'res_id': search_record.id,
                'type': 'ir.actions.act_window',
                }

    def action_get_attachment_tree_view(self):
        attachment_action = self.env.ref('base.action_attachment')
        action = attachment_action.read()[0]
        action['domain'] = str(['&', ('res_model', '=', self._name), ('res_id', 'in', self.ids)])
        return action


    def _compute_ticket_attach__no(self):
        read_group_res = self.env['ir.attachment'].read_group(
            [('res_model', '=', 'axis.helpdesk.ticket'), ('res_id', 'in', self.ids)],
            ['res_id'], ['res_id'])
        attach_data = { res['res_id']: res['res_id_count'] for res in read_group_res }
        for record in self:
            record.ticket_attach__no = attach_data.get(record.id, 0)

    @api.depends('helpdesk_sla_state.deadline', 'helpdesk_sla_state.reached_datetime')
    def _compute_helpdesk__sla_late(self):
        mapping = {}
        if self.ids:
            self.env.cr.execute("""
                    SELECT ticket_id, COUNT(id) AS reached_late_count
                    FROM helpdesk_sla_status
                    WHERE ticket_id IN %s AND deadline < reached_datetime
                    GROUP BY ticket_id
                """, (tuple(self.ids),))
            mapping = dict(self.env.cr.fetchall())

        for ticket in self:
            ticket.helpdesk__sla_late = mapping.get(ticket.id, 0) > 0

    @api.depends('crm_lead_id')
    def _compute_crm_ids(self):
        for ticket in self:
            ticket.crm_lead_ids = self.env['crm.lead'].search(
                [('crm_ticket_id', '=', ticket.id)])
            ticket.crm_count = len(ticket.crm_lead_ids)

    @api.onchange('stage_id')
    def _onchange_stage(self):
        if self.stage_id.name == "Re-Opened":
            self.re_open_bool = True
        else:
            self.re_open_bool = False


    @api.onchange('helpdesk_team_id', 'helpdesk_ticket_type_id')
    def _default_sla_policy(self):
        for ticket in self:
            lst = []
            sla_ids = self.env['axis.helpdesk.ticket.sla.policy'].search(
                [('team_id', '=', ticket.helpdesk_team_id.id), ('ticket_type_id', '=', ticket.helpdesk_ticket_type_id.id)])
            if sla_ids:
                for sla in sla_ids:
                    lst.append(sla.id)
            ticket.write({'sla_ids': [(6, 0, lst)]})
            for policy in ticket.sla_ids:
                if policy.days or policy.hours or policy.time_minutes:
                    deadline = ticket.date + timedelta(days=policy.days, hours=policy.hours,
                                                       minutes=policy.time_minutes)
                    ticket.write({'helpdesk_sla_deadline': deadline})
    @api.depends('account_invoice_id')
    def _compute_invoice_ids(self):
        for ticket in self:
            ticket.account_invoice_ids = self.env['account.move'].search(
                [('invoice_ticket_id', '=', ticket.id)])
            ticket.invoice_count = len(ticket.account_invoice_ids)

    def action_view_invoice(self):
        view_form_id = self.env.ref('account.view_move_form').id
        view_list_id = self.env.ref('account.view_invoice_tree').id
        action = {
            'type': 'ir.actions.act_window',
            'domain': [('id', 'in', self.account_invoice_ids.ids),('move_type', '=', 'out_invoice')],
            'view_mode': 'list,form',
            'name': ('Invoices'),
            'res_model': 'account.move',
        }
        if len(self.account_invoice_ids) == 1:
            action.update({'views': [(view_form_id, 'form')], 'res_id': self.account_invoice_ids.id})
        else:
            action['views'] = [(view_list_id, 'list'), (view_form_id, 'form')]
        return action

    @api.depends('sale_order_id')
    def _compute_sale_ids(self):
        for ticket in self:
            ticket.sale_order_ids = self.env['sale.order'].search(
                [('sale_ticket_id', '=', ticket.id)])
            ticket.sale_count = len(ticket.sale_order_ids)

    def action_view_sale(self):
        view_form_id = self.env.ref('sale.view_order_form').id
        view_list_id = self.env.ref('sale.view_order_tree').id
        action = {
            'type': 'ir.actions.act_window',
            'domain': [('id', 'in', self.sale_order_ids.ids)],
            'view_mode': 'list,form',
            'name': ('Sale Orders'),
            'res_model': 'sale.order',
        }
        if len(self.sale_order_ids) == 1:
            action.update({'views': [(view_form_id, 'form')], 'res_id': self.sale_order_ids.id})
        else:
            action['views'] = [(view_list_id, 'list'), (view_form_id, 'form')]
        return action

    @api.depends('purchase_order_id')
    def _compute_purchase_ids(self):
        for ticket in self:
            ticket.purchase_order_ids = self.env['purchase.order'].search(
                [('purchase_ticket_id', '=', ticket.id)])
            ticket.purchase_count = len(ticket.purchase_order_ids)

    def action_view_purchase(self):
        view_form_id = self.env.ref('purchase.purchase_order_form').id
        view_list_id = self.env.ref('purchase.purchase_order_view_tree').id
        action = {
            'type': 'ir.actions.act_window',
            'domain': [('id', 'in', self.purchase_order_ids.ids)],
            'view_mode': 'list,form',
            'name': ('Purchase Orders'),
            'res_model': 'purchase.order',
        }
        if len(self.purchase_order_ids) == 1:
            action.update({'views': [(view_form_id, 'form')], 'res_id': self.purchase_order_ids.id})
        else:
            action['views'] = [(view_list_id, 'list'), (view_form_id, 'form')]
        return action

    def action_view_crm(self):
        view_form_id = self.env.ref('crm.crm_lead_view_form').id
        view_list_id = self.env.ref('crm.crm_case_tree_view_leads').id
        action = {
            'type': 'ir.actions.act_window',
            'domain': [('id', 'in', self.crm_lead_ids.ids)],
            'view_mode': 'list,form',
            'name': ('CRM Lead'),
            'res_model': 'crm.lead',
        }
        if len(self.crm_lead_ids) == 1:
            action.update({'views': [(view_form_id, 'form')], 'res_id': self.crm_lead_ids.id})
        else:
            action['views'] = [(view_list_id, 'list'), (view_form_id, 'form')]
        return action

    @api.depends('ticket_ids')
    def _compute_ticket_ids(self):
        for ticket in self:
            ticket.ticket_ids = self.env['helpdesk.ticket.merge'].search(
                [('ticket_merge_id', '=', ticket.id)])
            ticket.ticket_count = len(ticket.ticket_ids)

    def action_view_tickets(self):
        view_form_id = self.env.ref('website_axis_helpdesk_advance.axis_helpdesk_ticket_form').id
        view_list_id = self.env.ref('website_axis_helpdesk_advance.axis_helpdesk_ticket_tree').id
        lst_id = []
        for ticket in self.ticket_ids:
            lst_id.append(ticket.ticket_id.id)
        action = {
            'type': 'ir.actions.act_window',
            'domain': [('id', 'in', lst_id)],
            'view_mode': 'list,form',
            'name': ('Helpdesk Tickets'),
            'res_model': 'helpdesk.ticket',
        }
        if len(self.ticket_ids) == 1:
            action.update({'views': [(view_form_id, 'form')], 'res_id': self.ticket_ids.id})
        else:
            action['views'] = [(view_list_id, 'list'), (view_form_id, 'form')]
        return action

    @api.depends('create_date', 'closed_date')
    def helpdesk_ticket_close_hour(self):
        for ticket in self:
            create_date = fields.Datetime.from_string(ticket.create_date)
            if create_date and ticket.closed_date and ticket.helpdesk_team_id and ticket.helpdesk_team_id.resource_calendar_id:
                duration_data = ticket.helpdesk_team_id.resource_calendar_id.get_work_duration_data(create_date,
                                                                                           fields.Datetime.from_string(
                                                                                               ticket.closed_date),
                                                                           compute_leaves=True)
                ticket.closed_hours = duration_data['hours']
            else:
                ticket.closed_hours = False

    def _compute_team_sla(self):
        for rec in self:
            rec.team_sla = rec.helpdesk_team_id.use_sla

    def assign_to_me(self):
        self.write({"res_user_id": self.env.user.id})

    def name_get(self):
        res = []
        for rec in self:
            res.append((rec.id, rec.number + " - " + rec.name))
        return res

    @api.model
    def _helpdesk_sla_policy_reset(self):
        return ['helpdesk_team_id', 'priority', 'helpdesk_ticket_type_id','tag_ids']

    @api.model_create_multi
    def create(self, list_value):
        now = fields.Datetime.now()
        teams = self.env['axis.helpdesk.ticket.team'].browse(
            [vals['helpdesk_team_id'] for vals in list_value if vals.get('helpdesk_team_id')])
        team_default_map = dict.fromkeys(teams.ids, dict())
        for team in teams:
            team_default_map[team.id] = {
                'helpdesk_stage_id': team._ticket_stage_define()[team.id].id,
                'user_id': team._ticket_define_to_user_assign()[team.id].id
            }

        for vals in list_value:
            if 'name' not in vals:
                vals['name'] = vals['number']
            if 'number' in vals:
                vals['description'] = vals['number']
            vals['number'] = self.env['ir.sequence'].next_by_code('helpdesk.ticket.sequence')
        for vals in list_value:
            if 'partner_name' in vals and 'partner_email' in vals and 'partner_id' not in vals:
                try:
                    partner_id = self.env['res.partner'].find_or_create(
                        tools.formataddr((vals['partner_name'], vals['partner_email']))
                    )
                    vals['partner_id'] = partner_id.id
                except UnicodeEncodeError:
                    vals['partner_id'].id = self.env['res.partner'].create({
                        'name': vals['partner_name'],
                        'email': vals['partner_email'],
                    }).id
            if 'fetchmail_cron_running' in self._context:
                if 'partner_email' in vals:
                    # Define the input string
                    input_str = vals['partner_email']
                    exist_partner = self.env['res.partner'].sudo().search([('email','=',vals['partner_email'])],limit=1)
                    # Regular expression pattern to extract name and email
                    pattern = r'"([^"]*)" <([^>]*)>'
                    # Using re.search to find the first match
                    match = re.search(pattern, input_str)
                    if match and not exist_partner:
                        name = match.group(1)  # Extract the name
                        email = match.group(2)  # Extract the email
                        Partner = self.env['res.partner']
                        new_partner = Partner.create({
                            'name': name,
                            'email': email,
                            # You can add more fields here as needed
                        })
                        vals['partner_id'] = new_partner.id
                    else:
                        vals['partner_id']=exist_partner.id
                    vals['helpdesk_stage_id'] = self.env["axis.helpdesk.stage"].sudo().search([],limit=1).id

        # determine partner email for ticket with partner but no email given
        partners = self.env['res.partner'].browse([vals['partner_id'] for vals in list_value if
                                                   'partner_id' in vals and vals.get(
                                                       'partner_id') and 'partner_email' not in vals])
        partner_email_map = {partner.id: partner.email for partner in partners}
        partner_name_map = {partner.id: partner.name for partner in partners}

        for vals in list_value:
            if vals.get('helpdesk_team_id'):
                team_default = team_default_map[vals['helpdesk_team_id']]
                # if 'helpdesk_stage_id' not in vals:
                #     vals['helpdesk_stage_id'] = team_default['helpdesk_stage_id']
                if 'res_user_id' not in vals:
                    vals['res_user_id'] = team_default['res_user_id']
                if vals.get(
                        'res_user_id'):  # if a user is finally assigned, force ticket assign_date and reset assign_hours
                    vals['assign_date'] = fields.Datetime.now()
                    vals['assign_hours'] = 0

            if vals.get('partner_id') in partner_email_map:
                vals['partner_email'] = partner_email_map.get(vals['partner_id'])
            if vals.get('partner_id') in partner_name_map:
                vals['partner_name'] = partner_name_map.get(vals['partner_id'])

            if vals.get('helpdesk_stage_id'):
                vals['date_last_stage_update'] = now

        tickets = super(axisHelpdeskTicket, self).create(list_value)
        template = self.env.ref('website_axis_helpdesk_advance.axis_helpdesk_ticket_new_create')
        mail = template.send_mail(tickets.id, force_send=True)

        for ticket in tickets:
            if 'fetchmail_cron_running' in self._context:
                ticket._onchange_partner()
            if ticket.partner_id:
                ticket.message_subscribe(partner_ids=ticket.partner_id.ids)
            if ticket.helpdesk_team_id.assigning_method == 'randomly' and ticket.helpdesk_team_id.res_user_ids:
                ticket.res_user_id=ticket.helpdesk_team_id.res_user_ids[0].id
            if ticket.team_id.assigning_method == 'randomly' and ticket.team_id.res_user_ids:
                ticket.res_user_id=ticket.team_id.res_user_ids[0].id
            if ticket.res_user_id:
                templateq = self.env.ref('website_axis_helpdesk_advance.assigned_request_email_template')
                templateq.send_mail(self.id, force_send=True)
            ticket.helpdesk_stage_id = self.env["axis.helpdesk.stage"].sudo().search([],limit=1).id

        tickets.sudo().helpdesk_sal_policy_apply()

        return tickets



    def _track_template(self, changes):
        res = super(axisHelpdeskTicket, self)._track_template(changes)
        ticket = self[0]
        if 'helpdesk_stage_id' in changes and ticket.helpdesk_stage_id.mail_template_id:
            res['helpdesk_stage_id'] = (ticket.helpdesk_stage_id.mail_template_id, {
                'auto_delete_keep_log': True,
                'subtype_id': self.env['ir.model.data']._xmlid_to_res_id('mail.mt_note'),
                'email_layout_xmlid': 'mail.mail_notification_light'
            }
                                        )
        if 'res_user_id' in changes:
            res['user_id'] = (self.env.ref('website_axis_helpdesk_advance.assigned_request_email_template'), {
                'auto_delete_keep_log': True,
                'subtype_id': self.env['ir.model.data']._xmlid_to_res_id('mail.mt_note'),
                'email_layout_xmlid': 'mail.mail_notification_light'
            }
                                        )
        return res
    def ticket_sla_policy_reach(self, stage_id):
        """ Flag the SLA status of current ticket for the given stage_id as reached, and even the unreached SLA applied
            on stage having a sequence lower than the given one.
        """
        stage = self.env['axis.helpdesk.stage'].browse(stage_id)
        stages = self.env['axis.helpdesk.stage'].search([('sequence', '<=', stage.sequence), (
        'team_ids', 'in', self.mapped('helpdesk_team_id').ids)])  # take previous stages
        self.env['helpdesk.sla.status'].search([
            ('ticket_id', 'in', self.ids),
            ('sla_stage_id', 'in', stages.ids),
            ('reached_datetime', '=', False),
            ('target_type', '=', 'stage')
        ]).write({'reached_datetime': fields.Datetime.now()})

        # For all SLA of type assigning, we compute deadline if they are not succeded (is succeded = has a reach_datetime)
        # and if they are linked to a specific stage.
        self.env['helpdesk.sla.status'].search([
            ('ticket_id', 'in', self.ids),
            ('sla_stage_id', '!=', False),
            ('reached_datetime', '=', False),
            ('target_type', '=', 'assigning')
        ]).ticket_state_deadline()

    def write(self, vals):
        assigned_tickets = closed_tickets = self.browse()
        if vals.get('res_user_id'):
            assigned_tickets = self.filtered(lambda ticket: not ticket.assign_date)

        if vals.get('helpdesk_stage_id'):
            if self.env['axis.helpdesk.stage'].browse(vals.get('helpdesk_stage_id')).is_close:
                closed_tickets = self.filtered(lambda ticket: not ticket.closed_date)
            else:  # auto reset the 'closed_by_partner' flag
                vals['closed_by_partner'] = False

        now = fields.Datetime.now()

        if 'helpdesk_stage_id' in vals:
            vals['date_last_stage_update'] = now

        res = super(axisHelpdeskTicket, self - assigned_tickets - closed_tickets).write(vals)
        res &= super(axisHelpdeskTicket, assigned_tickets - closed_tickets).write(dict(vals, **{
            'assign_date': now,
        }))
        res &= super(axisHelpdeskTicket, closed_tickets - assigned_tickets).write(dict(vals, **{
            'closed_date': now,
        }))
        res &= super(axisHelpdeskTicket, assigned_tickets & closed_tickets).write(dict(vals, **{
            'assign_date': now,
            'closed_date': now,
        }))

        if vals.get('partner_id'):
            self.message_subscribe([vals['partner_id']])

        # SLA business
        sla_triggers = self._helpdesk_sla_policy_reset()
        if any(field_name in sla_triggers for field_name in vals.keys()):
            self.sudo().helpdesk_sal_policy_apply(keep_reached=True)
        if 'helpdesk_stage_id' in vals:
            self.sudo().ticket_sla_policy_reach(vals['helpdesk_stage_id'])

        if 'helpdesk_stage_id' in vals or 'res_user_id' in vals:
            self.filtered(lambda ticket: ticket.res_user_id).sudo()._sla_assigning_reach()

        # # Handle ticket_deadline change
        # if vals.get('ticket_deadline'):
        #     old_value = self.ticket_deadline
        #     new_value = vals.get('ticket_deadline')
        #     message_body = f"Ticket Deadline has been changed: {old_value} → {new_value}"

        #     # Post message as a note (not an email)
        #     self.message_post(
        #         body=message_body,
        #         message_type='notification',  # Ensure it's not sent as an email
        #         subtype_id=self.env.ref('mail.mt_note').id,  # Make it a note
        #         partner_ids=[self.partner_id.id],  # Ensure the partner (portal user) sees it
        #     )
            
        # return res

    def _sla_reach(self, stage_id):
        stage = self.env['axis.helpdesk.stage'].browse(stage_id)
        stages = self.env['axis.helpdesk.stage'].search([('sequence', '<=', stage.sequence), (
        'team_ids', 'in', self.mapped('helpdesk_team_id').ids)])  # take previous stages
        self.env['helpdesk.sla.status'].search([
            ('ticket_id', 'in', self.ids),
            ('sla_stage_id', 'in', stages.ids),
            ('reached_datetime', '=', False),
            ('target_type', '=', 'stage')
        ]).write({'reached_datetime': fields.Datetime.now()})

        self.env['helpdesk.sla.status'].search([
            ('ticket_id', 'in', self.ids),
            ('sla_stage_id', '!=', False),
            ('reached_datetime', '=', False),
            ('target_type', '=', 'assigning')
        ])._compute_deadline()

    # EXTENDS portal portal.mixin
    def _compute_access_url(self):
        super()._compute_access_url()
        for ticket in self:
            ticket.access_url = f'/axis/helpdesk/ticket/{ticket.id}'

    def rating_get_access_token(self, partner=None):
        self.check_access_rights('read')
        self.check_access_rule('read')
        if not partner:
            partner = self.rating_get_partner_id()
        rated_partner = self.rating_get_rated_partner_id()
        ratings = self.rating_ids.sudo().filtered(lambda x: x.partner_id.id == partner.id and not x.consumed)
        if not ratings:
            rating = self.env['rating.rating'].sudo().create({
                'partner_id': partner.id,
                'rated_partner_id': rated_partner.id,
                'res_model_id': self.env['ir.model']._get_id(self._name),
                'res_id': self.id,
                'is_internal': False,
            })
        else:
            rating = ratings[0]
        return rating.access_token

    def rating_get_partner_id(self):
        if hasattr(self, 'partner_id') and self.partner_id:
            return self.partner_id
        return self.env['res.partner']

    def copy(self, default=None):
        self.ensure_one()
        if default is None:
            default = {}
        if "number" not in default:
            default["number"] = self._prepare_ticket_number(default)
        res = super().copy(default)
        return res

    def _prepare_ticket_number(self, values):
        seq = self.env["ir.sequence"]
        if "company_id" in values:
            seq = seq.with_context(force_company=values["company_id"])
        return seq.next_by_code("helpdesk.ticket.sequence") or "/"


    @api.model
    def get_helpdesk_ticket_month_wise(self):
        cr = self._cr

        query = """SELECT date FROM axis_helpdesk_ticket"""
        cr.execute(query)
        partner_data = cr.dictfetchall()
        data_dict = {}
        lst_val = []
        dict = {}

        for data in partner_data:
            if data['date']:
                mydate = data['date'].month
                for month_idx in range(0, 13):
                    if mydate == month_idx:
                        value = cal.month_name[month_idx]
                        lst_val.append(value)
                        lst_val = list(set(lst_val))
                        for record in lst_val:
                            count = 0
                            for rec in lst_val:
                                if rec == record:
                                    count = count + 1
                                dict.update({record: count})
                        keys, values = zip(*dict.items())
                        data_dict.update({"data": dict})

        return data_dict

    @api.model
    def get_helpdesk_ticket_week_wise(self):
        cr = self._cr
        query = """SELECT date FROM axis_helpdesk_ticket"""
        cr.execute(query)
        partner_data = cr.dictfetchall()
        data_dic = {}
        lst_val = []
        dict = {}
        days = ["Monday", "Tuesday", "Wednesday", "Thursday",
                "Friday", "Saturday", "Sunday"]
        for data in partner_data:
            if data['date']:
                mydate = data['date'].weekday()
                if mydate >= 0:
                    value = days[mydate]
                    lst_val.append(value)

                    lst_data_val = list(set(lst_val))

                    for record in lst_data_val:
                        count = 0
                        for rec in lst_val:
                            if rec == record:
                                count = count + 1
                            dict.update({record: count})
                        keys, values = zip(*dict.items())
                        data_dic.update({"data": dict})
        return data_dic

    @api.model
    def get_helpdesk_ticket_all(self):
        today = date.today()
        lst_date = []
        lst_last_month = []
        last_day_of_prev_month = date.today().replace(day=1) - timedelta(days=1)
        start_day_of_prev_month = date.today().replace(day=1) - timedelta(days=last_day_of_prev_month.day)

        sdate = start_day_of_prev_month  # start date
        edate = last_day_of_prev_month  # end date

        delta = edate - sdate  # as timedelta
        for i in range(delta.days + 1):
            day = sdate + timedelta(days=i)
            lst_last_month.append(day)

        last_month_ticket_id = self.env['axis.helpdesk.ticket'].sudo().search_count([('date', 'in', lst_last_month)])
        for i in range(7, 14):
            last_week_date = today - timedelta(days=i)
            lst_date.append(last_week_date)
        last_week_ticket = self.env['axis.helpdesk.ticket'].sudo().search_count([('date', 'in', lst_date)])

        # Check if the logged-in user is the admin
        if self._uid == self.env.ref('base.user_admin').id:
            domain = []
            print("Admin user detected, fetching all tickets.")
        else:
            # Get the teams where the logged-in user is a member
            teams = self.env['axis.helpdesk.ticket.team'].search([('res_user_ids', 'in', self.env.user.id)])
            print("Teams for logged-in user:", teams.mapped('name'))
            # Get the tickets for these teams
            domain = [
                    '|',  # OR condition to combine team membership and assigned tickets
                    ('helpdesk_team_id', 'in', teams.ids),  # Tickets for teams where the user is a member
                    ('res_user_id', '=', self.env.user.id)  # Tickets assigned to the logged-in user
                ]

        total_ticket = self.env['axis.helpdesk.ticket'].sudo().search_count(domain)
        today_ticket = self.env['axis.helpdesk.ticket'].sudo().search_count([('date', '=', fields.Date.today())])

        return {
            'total_ticket': total_ticket,
            'today_ticket': today_ticket,
            'last_week_ticket': last_week_ticket,
            'last_month_ticket': last_month_ticket_id,
        }
    @api.onchange('helpdesk_ticket_type_id','helpdesk_team_id')
    def _onchange_team(self):
        res = {}
        lst = []
        if self.based_on_ticket_type:
            if self.helpdesk_ticket_type_id.type_based_on == "helpdesk_team":
                helpdesk_team_id = self.env['axis.helpdesk.ticket.team'].search([('name', '=', self.helpdesk_team_id.name)])
                self.helpdesk_team_id = self.helpdesk_ticket_type_id.team_ids
                if helpdesk_team_id.visibility_res_user_ids:
                    for team_member in helpdesk_team_id.visibility_res_user_ids:
                        lst.append(team_member.id)
                    res['domain'] = {'res_user_id': [('id', 'in', lst)]}
                return res
            elif self.helpdesk_ticket_type_id.type_based_on == 'users':
                for ticket_data in self.helpdesk_ticket_type_id.user_ids:
                    lst.append(ticket_data.id)
                res['domain'] = {'res_user_id': [('id', 'in', lst)]}
                return res
            else:
                helpdesk_team_id = self.env['axis.helpdesk.ticket.team'].search([('name', '=', self.helpdesk_team_id.name)])
                if helpdesk_team_id.visibility_res_user_ids:
                    for team_member in helpdesk_team_id.visibility_res_user_ids:
                        lst.append(team_member.id)
                    res['domain'] = {'res_user_id': [('id', 'in', lst)]}
                    return res
        else:
            helpdesk_team_id = self.env['axis.helpdesk.ticket.team'].search([('name', '=', self.helpdesk_team_id.name)])
            if helpdesk_team_id.visibility_res_user_ids:
                for team_member in helpdesk_team_id.visibility_res_user_ids:
                    lst.append(team_member.id)
                res['domain'] = {'res_user_id': [('id', 'in', lst)]}
                return res
    def create_acount_move(self):
        account = self.env['account.account'].search([('company_id', '=', self.env.company.id)], limit=1)

        move = self.env['account.move'].create({
            'move_type': 'out_invoice',
            'partner_id': self.partner_id.id,
            'date': datetime.datetime.now(),
            'invoice_date': datetime.datetime.now(),
            'invoice_ticket_id': self.id
        })
        for product in self.product_ids:
            move.write({
                'invoice_line_ids': [
                    (0, 0, {
                        'product_id': product.id,
                        'name': product.name,
                        'quantity': 1,
                        'price_unit': float(product.list_price) or 0.0,
                        'move_id': move.id,
                        'account_id': account.id,
                        'price_subtotal': float(product.list_price * 1),
                        'tax_ids': product.taxes_id,
                    }),
                ]
            })
        move.action_post()
        self.update({'account_invoice_id': move.id,
                     })

    def create_invoice_move(self):
        self.is_invoice = True
        account_ticket_id = self.env['account.move'].search([('invoice_ticket_id','=',self.id)])
        if len(account_ticket_id) > 1:
            message_id = self.env['helpdesk.invoice.confirm'].create({'name': 'Are you sure you want to create more than 1 Invoice !','ticket_id': self.id})
            return {
                'name': _('Message'),
                'type': 'ir.actions.act_window',
                'view_mode': 'form',
                'res_model': 'helpdesk.invoice.confirm',
                'res_id': message_id.id,
                'ticket_id':message_id.id,
                'target': 'new'
            }
        else:
            self.create_acount_move()

    def create_sale_order(self):
        sale_order = self.env['sale.order']
        order_id = sale_order.create({
            'partner_id':self.partner_id.id,
            'sale_ticket_id':self.id,
        })
        for product in self.product_ids:
            order_id.order_line.create({
                'product_id':product.id,
                'name':product.name,
                'product_uom_qty':1,
                'price_unit':float(product.list_price) or 0.0,
                'order_id':order_id.id

            })
        self.update({'sale_order_id':order_id.id})

    def create_purchase_order(self):
        purchase_order = self.env['purchase.order']
        order_id = purchase_order.create({
            'partner_id': self.partner_id.id,
            'purchase_ticket_id': self.id,
        })
        for product in self.product_ids:
            order_id.order_line.create({
                'product_id': product.id,
                'name': product.name,
                'product_uom':product.uom_id.id,
                'product_qty': 1,
                'price_unit': float(product.list_price) or 0.0,
                'order_id': order_id.id,
                'date_planned': datetime.datetime.now(),

            })
        self.update({'purchase_order_id': order_id.id})

    def create_crm_lead(self):
        crm_lead = self.env['crm.lead']
        lead_id = crm_lead.create({
            'partner_id': self.partner_id.id,
            'crm_ticket_id': self.id,
            'name':self.name
        })
        self.update({'crm_lead_id': lead_id.id})

    def send_whatsapp_msg(self):
        return {'type': 'ir.actions.act_window',
                'name': _('Whatsapp Message'),
                'res_model': 'whatsapp.message.wizard',
                'target': 'new',
                'view_mode': 'form',
                'view_type': 'form',
                'context': {'default_res_user_id': self.partner_id,
                            'default_mobile':self.partner_id.mobile},
                }

class HelpdeskMergeTicket(models.Model):
    _name = "helpdesk.ticket.merge"

    name = fields.Char('Name')
    ticket_ids = fields.Many2many('axis.helpdesk.ticket')
    ticket_merge_id = fields.Many2one('axis.helpdesk.ticket')
    ticket_id = fields.Many2one('axis.helpdesk.ticket')
