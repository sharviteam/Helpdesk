# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.
import ast
from odoo import api, fields, models,_
from datetime import datetime,date

from dateutil import relativedelta
from ast import literal_eval
from odoo.osv import expression
from datetime import date
from odoo.addons.http_routing.models.ir_http import slug
from odoo.exceptions import  ValidationError
import pytz
import logging

_logger = logging.getLogger(__name__)


class axisHelpdeskTeam(models.Model):
    _name = "axis.helpdesk.ticket.team"
    _description = "Helpdesk Team"
    _inherit = ['mail.alias.mixin', 'mail.thread', 'rating.parent.mixin']

    def _default_domain_res_user_ids(self):
        return [('groups_id', 'in', self.env.ref('website_axis_helpdesk_advance.group_helpdesk_ticket_users').id)]

    def _default_stage_ids(self):
        pass


    name = fields.Char(string="Name",required=1)
    res_user_ids = fields.Many2many("res.users",string="Team Members", domain=[('id','!=',2)])
    use_alias = fields.Boolean('Email alias', default=True)
    email_alias_id = fields.Many2one("mail.alias",string="Email Alias",ondelete="restrict")
    # alias_user_id = fields.Many2many('res.users', 'Owner')
    team_leader_id = fields.Many2one("res.users",string="Team Leader")
    allow_timesheet = fields.Boolean(string="Allow Timesheet")
    use_sla = fields.Boolean(string="Use SLA")
    company_id = fields.Many2one(comodel_name="res.company",string="Company",default=lambda self: self.env.company)
    calendar_id = fields.Many2one("resource.calendar",string="Working Hours",domain="['|', ('company_id', '=', False), ('company_id', '=', company_id)]")
    project_id = fields.Many2one("project.project",string="Default Project")
    helpdesk_type_ids = fields.Many2many("axis.helpdesk.ticket.type",string="Ticket Type")
    helpdesk_ticket_ids = fields.One2many("axis.helpdesk.ticket","helpdesk_team_id",string="Tickets")
    assigning_method = fields.Selection([
        ('manual', 'Manually'),
        ('randomly', 'Randomly'),
        ('balanced', 'Equally')], string='Ticket Assigment Method',
        default='manual', required=True,compute='_compute_assign_method', store=True, readonly=False)
    visibility_res_user_ids = fields.Many2many('res.users', 'helpdesk_visibility_team', string='Team Visibility',
                                             domain=lambda self: self._default_domain_res_user_ids(), required=1)
    helpdesk_category_ids = fields.Many2many("axis.helpdesk.ticket.category", string="Category")
    active = fields.Boolean(default=True)
    use_sla = fields.Boolean(string="Use SLA")
    resource_calendar_id = fields.Many2one("resource.calendar","Working Hours",default=lambda self: self.env.company.resource_calendar_id)
    color = fields.Integer(string="Color Index", default=0)
    upcoming_ticket_sla_policy_fail_tickets = fields.Integer(string='Upcoming SLA Fail Tickets', compute='_compute_fail_sla_tickets')
    use_rating = fields.Boolean('Ratings on tickets')
    partner_id = fields.Many2one("res.partner", string="Contact")
    client_id = fields.Many2one("res.users", string="Contact")
    partner_name = fields.Char(string="Partner",readonly=1,force_save=1)
    partner_email = fields.Char(string="Email",readonly=1,force_save=1)
    portal_rating_url = fields.Char('URL to Submit an Issue', readonly=True, compute='_compute_portal_rating_url')
    portal_show_rating = fields.Boolean(
        'Display Rating on Customer Portal', compute='_compute_portal_show_rating', store=True,
        readonly=False)
    allow_portal_ticket_closing = fields.Boolean('Ticket closing', help="Allow customers to close their tickets")
    stage_ids = fields.Many2many(
        'axis.helpdesk.stage', relation='team_stage_rel', string='Stages',
        default=_default_stage_ids,
        help="Stages the team will use. This team's tickets will only be able to be in these stages.")

    @api.model
    def create(self, vals):
        team = super(axisHelpdeskTeam, self).create(vals)
        print("Creating team:", team.name)
        team._update_user_helpdesk_teams()
        return team

    def write(self, vals):
        old_clients = {user.id for user in self.client_id}
        res = super(axisHelpdeskTeam, self).write(vals)
        new_clients = {user.id for user in self.client_id}
        removed_clients = old_clients - new_clients
        added_clients = new_clients - old_clients
        print("Updating team:", self.name)
        self._update_user_helpdesk_teams(removed_clients, added_clients)
        return res

    def _update_user_helpdesk_teams(self, removed_clients=None, added_clients=None):
        for team in self:
            print("Updating users for team:", team.name)
            if removed_clients:
                for user_id in removed_clients:
                    user = self.env['res.users'].browse(user_id)
                    print("Removing team from user:", user.name)
                    user.helpdesk_team_ids = [(3, team.id)]
            if added_clients:
                for user_id in added_clients:
                    user = self.env['res.users'].browse(user_id)
                    print("Adding team to user:", user.name)
                    user.helpdesk_team_ids = [(4, team.id)]
            if not removed_clients and not added_clients:
                if team.client_id:
                    for user in team.client_id:
                        print("Adding team to user:", user.name)
                        user.helpdesk_team_ids = [(4, team.id)]
                else:
                    # If no client_id, remove the team from all users
                    users = self.env['res.users'].search([('helpdesk_team_ids', 'in', self.id)])
                    for user in users:
                        print("Removing team from user:", user.name)
                        user.helpdesk_team_ids = [(3, self.id)]

    def _alias_get_creation_values(self):
        values = super(axisHelpdeskTeam, self)._alias_get_creation_values()

        values['alias_model_id'] = self.env['ir.model']._get('axis.helpdesk.ticket').id
        if self.id:
            values['alias_defaults'] = defaults = ast.literal_eval(self.alias_defaults or "{}")
            defaults['team_id'] = self.id
        return values
    def _ticket_get_close_stage(self):
        """
            Return the first closing kanban stage or the last stage of the pipe if none
        """
        closed_stage = self.stage_ids.filtered(lambda stage: stage.is_close)
        if not closed_stage:
            print(self.stage_ids,"-------------------------------------")
            closed_stage = self.stage_ids[-1]
        return closed_stage


    @api.onchange('res_user_ids')
    def _onchange_res_user_ids(self):
        team_id = self.env['axis.helpdesk.ticket.team'].search([])
        user_ids = self.env['res.users'].search([('id','!=',2)])
        lst = []
        for team in team_id:
            for user in user_ids:
                if user.has_group('website_axis_helpdesk_advance.group_helpdesk_ticket_users') or user.has_group(
                        'website_axis_helpdesk_advance.group_helpdesk_ticket_manager'):
                    user_manager = self.env['res.users'].search([('id', '=', user.id)])
                    for manager in user_manager:
                        for member in team.res_user_ids.ids:
                            if manager.id == member:
                                lst.append(team.id)
                        manager.write({'helpdesk_team_ids': [(6, 0, lst)]})

    @api.depends('res_user_ids', 'visibility_res_user_ids')
    def _compute_assign_method(self):
        with_manual = self.filtered(lambda t: not t.res_user_ids and not t.visibility_res_user_ids)
        with_manual.update({'assigning_method': 'manual'})

    @api.constrains('assigning_method', 'res_user_ids', 'visibility_res_user_ids')
    def _check_member_assignation(self):
        if not self.res_user_ids and not self.visibility_res_user_ids and self.assigning_method != 'manual':
            raise ValidationError(_("You must have team members assigned to change the assignment method."))

    def _ticket_stage_define(self):
        """ Get a dict with the stage (per team) that should be set as first to a created ticket
            :returns a mapping of team identifier with the stage (maybe an empty record).
            :rtype : dict (key=team_id, value=record of helpdesk.stage)
        """
        result = dict.fromkeys(self.ids, self.env['axis.helpdesk.stage'])
        for team in self:
            result[team.id] = self.env['axis.helpdesk.stage'].search([('team_ids', 'in', team.id)], order='sequence',
                                                                limit=1)
        return result

    def _ticket_define_to_user_assign(self):
        """ Get a dict with the user (per team) that should be assign to the nearly created ticket according to the team policy
            :returns a mapping of team identifier with the "to assign" user (maybe an empty record).
            :rtype : dict (key=team_id, value=record of res.users)
        """
        result = dict.fromkeys(self.ids, self.env['res.users'])
        for team in self:
            res_user_ids = sorted(team.res_user_ids.ids) if team.res_user_ids else sorted(team.visibility_res_user_ids.ids)
            if res_user_ids:
                if team.assigning_method == 'randomly':  # randomly means new tickets get uniformly distributed
                    last_assigned_user = self.env['axis.helpdesk.ticket'].search([('helpdesk_team_id', '=', team.id)],
                                                                            order='create_date desc, id desc',
                                                                            limit=1).res_user_id
                    index = 0
                    if last_assigned_user and last_assigned_user.id in res_user_ids:
                        previous_index = res_user_ids.index(last_assigned_user.id)
                        index = (previous_index + 1) % len(res_user_ids)
                    result[team.id] = self.env['res.users'].browse(res_user_ids[index])
                elif team.assigning_method == 'balanced':  # find the member with the least open ticket
                    ticket_count_data = self.env['axis.helpdesk.ticket'].read_group(
                        [('helpdesk_stage_id.is_close', '=', False), ('res_user_id', 'in', res_user_ids), ('helpdesk_team_id', '=', team.id)],
                        ['res_user_id'], ['res_user_id'])
                    open_ticket_per_user_map = dict.fromkeys(res_user_ids, 0)  # dict: user_id -> open ticket count
                    open_ticket_per_user_map.update(
                        (item['res_user_id'][0], item['user_id_count']) for item in ticket_count_data)
                    result[team.id] = self.env['res.users'].browse(
                        min(open_ticket_per_user_map, key=open_ticket_per_user_map.get))
        return result

    @api.depends('use_rating')
    def _compute_portal_show_rating(self):
        without_rating = self.filtered(lambda t: not t.use_rating)
        without_rating.update({'portal_show_rating': False})


    @api.depends('name', 'portal_show_rating')
    def _compute_portal_rating_url(self):
        base_url = self.env['ir.config_parameter'].sudo().get_param('web.base.url')
        for team in self:
            if team.name and team.portal_show_rating and team.id:
                team.portal_rating_url = '%s/helpdesk/rating/%s' % (base_url, slug(team))
            else:
                team.portal_rating_url = False



    def _alias_get_creation_values(self):
        values = super(axisHelpdeskTeam, self)._alias_get_creation_values()
        values['alias_model_id'] = self.env['ir.model']._get('axis.helpdesk.ticket').id
        if self.id:
            values['alias_defaults'] = defaults = ast.literal_eval(self.alias_defaults or "{}")
            defaults['team_id'] = self.id
        return values

    @api.onchange('use_alias', 'name')
    def onchange_alias_data(self):
        if not self.use_alias:
            self.alias_name = False

    def _compute_fail_sla_tickets(self):
        ticket_id = self.env['axis.helpdesk.ticket'].read_group([
            ('helpdesk_team_id', 'in', self.ids),
            ('helpdesk_sla_deadline', '!=', False),
            ('helpdesk_sla_deadline', '<=', fields.Datetime.to_string((date.today() + relativedelta.relativedelta(days=1)))),
        ], ['helpdesk_team_id'], ['helpdesk_team_id'])
        data = dict((data['helpdesk_team_id'][0], data['helpdesk_team_id_count']) for data in ticket_id)
        for team in self:
            team.upcoming_ticket_sla_policy_fail_tickets = data.get(team.id, 0)



    def stage_set(self):
        result = dict.fromkeys(self.ids, self.env['axis.helpdesk.stage'])
        for team in self:
            result[team.id] = self.env['axis.helpdesk.stage'].search([('team_ids', 'in', team.id)],
                                                                            order='sequence', limit=1)
        return result
    def assign_user_to_team(self):
        result = dict.fromkeys(self.ids, self.env['res.users'])
        for team in self:
            res_user_ids = sorted(team.res_user_ids.ids)
            if res_user_ids:
                if team.assigning_method == 'randomly':  # randomly means new tickets get uniformly distributed
                    last_assigned_user = self.env['axis.helpdesk.ticket'].search([('team_id', '=', team.id)], order='create_date desc, id desc', limit=1).res_user_id
                    index = 0
                    if last_assigned_user and last_assigned_user.id in res_user_ids:
                        previous_index = res_user_ids.index(last_assigned_user.id)
                        index = (previous_index + 1) % len(res_user_ids)
                    result[team.id] = self.env['res.users'].browse(res_user_ids[index])
                elif team.assigning_method == 'balanced':  # find the member with the least open ticket
                    ticket_count_data = self.env['axis.helpdesk.ticket'].read_group([('helpdesk_stage_id.is_close', '=', False), ('res_user_id', 'in', res_user_ids)], ['res_user_id'], ['res_user_id'])
                    open_ticket_per_user_map = dict.fromkeys(res_user_ids, 0)  # dict: user_id -> open ticket count
                    open_ticket_per_user_map.update((item['res_user_id'][0], item['user_id_count']) for item in ticket_count_data)
                    result[team.id] = self.env['res.users'].browse(min(open_ticket_per_user_map, key=open_ticket_per_user_map.get))
        return result

    @api.model
    def filter_stage_data_dashboard(self):
        now = datetime.now()
        dt_string = now.strftime("%Y-%m-%d %H:%M:%S")
        datetime_object = datetime.strptime(dt_string, '%Y-%m-%d %H:%M:%S')

        domain = [
                '|',  # Start OR condition
                ('res_user_id', '=', self.env.user.id),  # Tickets assigned to the logged-in user
                ('helpdesk_team_id.res_user_ids', 'in', self.env.user.id)  # User is in the helpdesk team
            ]

        # If admin user, remove the domain restriction
        if self._uid == self.env.ref('base.user_admin').id:
            domain = []

        # Define domain for tickets assigned to the logged-in user
        assigned_user_domain = [('res_user_id', '=', self.env.user.id)]
        # Define domains for different stages
        closed_stage_domain = domain + [('helpdesk_stage_id.closed', '=', True)]
        pending_stage_domain = domain +  [('helpdesk_stage_id.closed', '=', False), ('helpdesk_stage_id.not_start', '=', False), ('helpdesk_stage_id.is_close', '=', False)]
        success_stage_domain = domain + [('helpdesk_stage_id.closed', '=', False), ('helpdesk_stage_id.not_start', '=', False), ('helpdesk_stage_id.is_close', '=', False)]

        # Fetch SLA data
        sla_complete = self.env['axis.helpdesk.ticket'].sudo().search_read(domain + [('helpdesk_stage_id', '=', 'Done'), ('helpdesk_sla_deadline', '<=', datetime_object)])
        sla_pending = self.env['axis.helpdesk.ticket'].sudo().search_read(domain + [('helpdesk_stage_id', '!=', 'Done'), ('helpdesk_sla_deadline', '>=', datetime_object)])
        sla_missed = self.env['axis.helpdesk.ticket'].sudo().search_read(domain + [('helpdesk_stage_id', '=', 'Done'), ('helpdesk_sla_deadline', '<=', datetime_object)])

        # Group fields and list fields setup
        group_fields = ['priority', 'create_date', 'helpdesk_stage_id', 'closed_hours']
        list_fields = ['priority', 'create_date', 'helpdesk_stage_id', 'closed_hours']

        user_uses_sla = self.user_has_groups('helpdesk.group_use_sla') and \
            bool(self.env['axis.helpdesk.ticket.team'].sudo().search(
                [('use_sla', '=', True), '|', ('res_user_ids', 'in', self._uid), ('res_user_ids', '=', False)]))

        user_id = self.env['res.users'].sudo().search_read([], limit=1)
        team_id = self.env['axis.helpdesk.ticket.team'].sudo().search_read([])

        ticket_type_id = self.env['axis.helpdesk.ticket.type'].sudo().search_read([])

        if self.env['ir.config_parameter'].sudo().get_param('stage_ids'):
            stage_ids = literal_eval(self.env['ir.config_parameter'].sudo().get_param('stage_ids'))
            stage_ids = self.env['axis.helpdesk.stage'].sudo().browse(stage_ids)
        else:
            stage_ids = []

        if self.env['ir.config_parameter'].sudo().get_param('filter_ids'):
            filter_ids = literal_eval(self.env['ir.config_parameter'].sudo().get_param('filter_ids'))
            filter_ids = self.env['axis.helpdesk.stage'].sudo().browse(filter_ids)
        else:
            filter_ids = []

        stage_dict = {}
        filter_dict = {}

        for i in stage_ids:
            stage_dict[i.id] = i.name
        for i in filter_ids:
            filter_dict[i.id] = i.name

        if user_uses_sla:
            group_fields.insert(1, 'helpdesk_sla_deadline:year')
            group_fields.insert(2, 'helpdesk_sla_deadline:hour')
            group_fields.insert(3, 'helpdesk__sla_late')
            list_fields.insert(1, 'helpdesk_sla_deadline')
            list_fields.insert(2, 'helpdesk__sla_late')

        # Fetch tickets based on domains
        HelpdeskTicket = self.env['axis.helpdesk.ticket']
        all_tickets = HelpdeskTicket.sudo().search_read(expression.AND([domain, [('name', '!=', False)]]),
                                                        ['helpdesk_sla_deadline', 'closed_hours', 'helpdesk__sla_late', 'priority','helpdesk_stage_id','res_user_id'])
        closed_tickets = HelpdeskTicket.sudo().search_read(closed_stage_domain,
                                                           ['helpdesk_sla_deadline', 'closed_hours', 'helpdesk__sla_late', 'priority', 'helpdesk_stage_id', 'res_user_id'])
        success_tickets = HelpdeskTicket.sudo().search_read(success_stage_domain,
                                                           ['helpdesk_sla_deadline', 'closed_hours', 'helpdesk__sla_late', 'priority', 'helpdesk_stage_id', 'res_user_id'])
        pending_tickets = HelpdeskTicket.sudo().search_read(pending_stage_domain,
                                                           ['helpdesk_sla_deadline', 'closed_hours', 'helpdesk__sla_late', 'priority', 'helpdesk_stage_id', 'res_user_id'])
        print("%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%", len(all_tickets))

        user_company_id = self.env.user.company_id
        stage_ids = self.env['axis.helpdesk.stage'].sudo().search_read([('id', 'in', user_company_id.helpdesk_stage_ids.ids)])

        cr = self._cr
        query = """SELECT id,name,number,write_date,helpdesk_stage_id,create_date,res_user_id,partner_id FROM axis_helpdesk_ticket"""
        cr.execute(query)
        ticket_ids = []
        ticket_id_all_data = cr.dictfetchall()

        for ticket_data in ticket_id_all_data:
            stage_id = self.env['axis.helpdesk.stage'].sudo().search([('id', '=', ticket_data['helpdesk_stage_id'])])
            partner_id = self.env['res.partner'].sudo().search([('id', '=', ticket_data['partner_id'])])
            user_id = self.env['res.users'].sudo().search([('id', '=', ticket_data['res_user_id'])])

            ticket_dic = {
                'helpdesk_stage_id': stage_id.name,
                'number': ticket_data['number'],
                'partner_id': partner_id.name,
                'create_date': ticket_data['create_date'],
                'write_date': ticket_data['write_date'],
                'res_user_id': user_id.name,
            }
            ticket_ids.append(ticket_dic)

        stage_lst = []

        for stage_id in stage_ids:
            ticket_id = self.env['axis.helpdesk.ticket'].sudo().search([('helpdesk_stage_id', '=', stage_id['id'])])
            data_dic = {
                'stage_id': stage_id['name'],
                'stage_count': len(ticket_id)
            }
            stage_lst.append(data_dic)

        result = {
            'user_id': user_id,
            'team_id': team_id,
            'ticket_type_id': ticket_type_id,
            'assingUser_id': user_id,
            'stage_config': stage_ids,
            'stage_count': stage_lst,
            'ticket_ids': ticket_ids,
            'user_id_serach': user_id,
            'stage_dict': stage_dict,
            'helpdesk_target_closed': self.env.user.helpdesk_ticket_target_closed,
            'helpdesk_target_rating': self.env.user.helpdesk_ticket_target_rating,
            'helpdesk_target_success': self.env.user.helpdesk_ticket_target_success,
            'today': {'count': 0, 'rating': 0, 'success': 0},
            'yesterday': {'count': 0, 'rating': 0, 'success': 0},
            'sevendays': {'count': 0, 'rating': 0, 'success': 0},
            'month': {'count': 0, 'rating': 0, 'success': 0},
            'year': {'count': 0, 'rating': 0, 'success': 0},
            'my_all': {'count': 0, 'hours': 0, 'failed': 0},
            'my_all_tickets': {'count': 0, 'hours': 0, 'failed': 0},
            'my_closed_tickets': {'count': 0, 'hours': 0, 'failed': 0},
            'my_high': {'count': 0, 'hours': 0, 'failed': 0},
            'my_low': {'count': 0, 'hours': 0, 'failed': 0},
            'my_medium': {'count': 0, 'hours': 0, 'failed': 0},
            'my_urgent': {'count': 0, 'hours': 0, 'failed': 0},
            'rating_enable': False,
            'show_demo': not bool(HelpdeskTicket.sudo().search([], limit=1)),
            'success_rate_enable': user_uses_sla,
            'cuurent_date': date.today(),
            'my_pending_count': len(pending_tickets),
            'my_closed_count': len(closed_tickets),
            'my_success_count': len(success_tickets),
            'sla_complete': sla_complete,
            'sla_pending': sla_pending,
            'sla_missed': sla_missed,
            'len_sla_complete': len(sla_complete),
            'len_sla_pending': len(sla_pending),
            'len_sla_missed': len(sla_missed),
            'current_user': self.env.uid
        }

        def failed_sla_ticket(data):
            deadline = data.get('helpdesk_sla_deadline')
            return deadline and datetime.now() > datetime.strptime(deadline, '%Y-%m-%d %H:%M:%S')

        # def ticket_to_add(ticket, key="my_all"):
        #     result[key]['count'] += 1
        #     result[key]['hours'] += ticket['closed_hours']
        #     if failed_sla_ticket(ticket):
        #         result[key]['failed'] += 1

        def ticket_to_add(ticket, key="my_all"):
            # Check if the ticket is closed and the stage is "Solved"
            print("@@@@@@@@@@@@@",key)
            solved_stage = self.env['axis.helpdesk.stage'].search([('name', '=', 'On Hold')], limit=1)
            
            if ticket.get('helpdesk_stage_id') and ticket['helpdesk_stage_id'][0] == solved_stage.id:
                result[key]['count'] += 1
                result[key]['hours'] += ticket.get('closed_hours', 0)
                if failed_sla_ticket(ticket):
                    result[key]['failed'] += 1

        # def all_add_to(ticket, key="my_all_tickets"):
        #     result[key]['count'] += 1
        #     result[key]['hours'] += ticket['closed_hours']
        #     if failed_sla_ticket(ticket):
        #         result[key]['failed'] += 1

        def close_to(ticket, key="my_closed_tickets"):
            result[key]['count'] += 1
            result[key]['hours'] += ticket['closed_hours']
            if failed_sla_ticket(ticket):
                result[key]['failed'] += 1

        # Process tickets for each category
        for ticket in closed_tickets:
            close_to(ticket, "my_closed_tickets")
        for ticket in pending_tickets:
            print("^^^^^^^^^^^^^%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%",pending_tickets)
            ticket_to_add(ticket, "my_all")
        # for ticket in pending_tickets:
        #     all_add_to(ticket, "my_all_tickets")

        def all_add_to_ticket(ticket, key="my_all_tickets"):
            # Check if the ticket is assigned to the logged-in user
            if ticket.get('res_user_id') and ticket['res_user_id'][0] == self.env.uid:
                result[key]['count'] += 1
                result[key]['hours'] += ticket.get('closed_hours', 0)
                if failed_sla_ticket(ticket):
                    result[key]['failed'] += 1

        def all_add_to_closed_ticket(ticket, key="my_closed_tickets"):
            # Check if the ticket is closed and the stage is "Solved"
            solved_stage = self.env['axis.helpdesk.stage'].search([('name', 'in', ['Solved','Cancelled', 'Done '])])
            
            if ticket.get('helpdesk_stage_id') and ticket['helpdesk_stage_id'][0] in solved_stage.ids:
                result[key]['count'] += 1
                result[key]['hours'] += ticket.get('closed_hours', 0)
                if failed_sla_ticket(ticket):
                    result[key]['failed'] += 1

        def all_add_to_solved_ticket(ticket, key="today"):
            # Debugging: Print the stage information to see what is being returned
            print("Ticket Stage Data:", ticket.get('helpdesk_stage_id'))

            # Fetch the stages "Solved" and "Done"
            solved_stages = self.env['axis.helpdesk.stage'].search([('name', 'in', ['Solved', 'Done '])])

            # Check if the ticket's stage is in the solved or done stages by comparing IDs
            if ticket.get('helpdesk_stage_id') and ticket['helpdesk_stage_id'][0] in solved_stages.ids:
                result[key]['count'] += 1

        def all_add_to_pending_ticket(ticket, key="my_all"):
            # Debugging: Print the stage information to see what is being returned
            print("Ticket Stage Data:", ticket.get('helpdesk_stage_id'))

            # Fetch the stages "Solved" and "Done"
            solved_stages = self.env['axis.helpdesk.stage'].search([('name', 'not in', ['Solved', 'Done ','Cancelled'])])

            # Check if the ticket's stage is in the solved or done stages by comparing IDs
            if ticket.get('helpdesk_stage_id') and ticket['helpdesk_stage_id'][0] in solved_stages.ids:
                result[key]['count'] += 1
                # Optionally, you can count closed hours or failed SLA tickets here
                # result[key]['hours'] += ticket.get('closed_hours', 0)
                # if failed_sla_ticket(ticket):
                #     result[key]['failed'] += 1

        def all_add_to_low_priority(ticket, key="my_low"):
            # Check if the ticket priority is 0
            if ticket.get('priority') == '0':
                result[key]['count'] += 1
                result[key]['hours'] += ticket.get('closed_hours', 0)
                if failed_sla_ticket(ticket):
                    result[key]['failed'] += 1

        def all_add_to_medium_priority(ticket, key="my_medium"):
            # Check if the ticket priority is 0
            if ticket.get('priority') == '1':
                result[key]['count'] += 1
                result[key]['hours'] += ticket.get('closed_hours', 0)
                if failed_sla_ticket(ticket):
                    result[key]['failed'] += 1

        def all_add_to_high_priority(ticket, key="my_high"):
            # Check if the ticket priority is 0
            if ticket.get('priority') == '2':
                result[key]['count'] += 1
                result[key]['hours'] += ticket.get('closed_hours', 0)
                if failed_sla_ticket(ticket):
                    result[key]['failed'] += 1

        def all_add_to_urgent_priority(ticket, key="my_urgent"):
            # Check if the ticket priority is 0
            if ticket.get('priority') == '3':
                result[key]['count'] += 1
                result[key]['hours'] += ticket.get('closed_hours', 0)
                if failed_sla_ticket(ticket):
                    result[key]['failed'] += 1

        # Debugging statements
        print("******", all_tickets)
        for ticket in all_tickets:
            all_add_to_ticket(ticket, 'my_all_tickets')  # Count my tickets
            all_add_to_closed_ticket(ticket, 'my_closed_tickets')  # Count closed
            all_add_to_solved_ticket(ticket, 'today')
            all_add_to_pending_ticket(ticket, 'my_all')
            all_add_to_low_priority(ticket, 'my_low')
            all_add_to_medium_priority(ticket, 'my_medium')
            all_add_to_high_priority(ticket, 'my_high')
            all_add_to_urgent_priority(ticket, 'my_urgent')


        result['my_all_tickets']['hours'] = round(
            result['my_all_tickets']['hours'] / (result['my_all_tickets']['count'] or 1), 2
        )


        return result
