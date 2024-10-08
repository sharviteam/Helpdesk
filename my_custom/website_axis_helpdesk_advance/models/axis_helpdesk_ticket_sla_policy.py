# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import fields, models, api
from datetime import datetime
from odoo.osv import expression
from odoo.addons.website_axis_helpdesk_advance.models.axis_helpdesk_ticket import TICKET_PRIORITY



class HelpdeskTicketSla(models.Model):
    _name = "axis.helpdesk.ticket.sla.policy"
    _description = "Helpdesk Ticket SLA Policy"

    name = fields.Char(string="Name", required=True)
    helpdesk_stage_id = fields.Many2one("axis.helpdesk.stage", string="Stage")
    days = fields.Integer(string="Days", default=0, required=True)
    hours = fields.Integer(string="Hours", default=0, required=True)
    note = fields.Char(string="Note")
    target_type = fields.Selection([('stage', 'Reaching Stage'), ('assigning', 'Assigning Ticket')], default='stage',
                                   required=True)
    priority = fields.Selection(
        TICKET_PRIORITY, string='Minimum Priority',
        default='0', required=True)
    exclude_stage_ids = fields.Many2many(
        'axis.helpdesk.stage', string='Exclude Stages',
        compute='_compute_exclude_stage_ids', store=True, readonly=False, copy=True,
        domain="[('id', '!=', helpdesk_stage_id.id)]")
    team_id = fields.Many2one('axis.helpdesk.ticket.team', 'Team', required=True)
    ticket_type_id = fields.Many2one(
        'axis.helpdesk.ticket.type', "Ticket Type")
    tag_ids = fields.Many2many(
        'axis.helpdesk.ticket.tag', string='Tags')
    time_minutes = fields.Integer(
        'Minutes', default=0, inverse='_inverse_time_minutes', required=True)
    tag_ids = fields.Many2many(
    'axis.helpdesk.ticket.tag', string='Tags')

    def _inverse_time_minutes(self):
        for sla in self:
            sla.time_minutes = max(0, sla.time_minutes)
            if sla.time_minutes >= 60:
                sla.hours += sla.time_minutes / 60
                sla.time_minutes = sla.time_minutes % 60

    @api.depends('target_type')
    def _compute_exclude_stage_ids(self):
        self.update({'exclude_stage_ids': False})

    def ticket_sla_policy_test(self):
        slas = self.search([("helpdesk_team_ids", "!=", False)])
        for sla in slas:
            for team in sla.helpdesk_team_ids:
                if team.ticket_ids:
                    sla.check_ticket_sla(team.ticket_ids)

    def check_ticket_sla(self, ticket_ids):
        for ticket in ticket_ids.filtered(lambda t: not t.helpdesk_stage_id.closed):
            deadline = ticket.create_date
            working_calendar = ticket.team_id.resource_calendar_id

            if self.days > 0:
                deadline = working_calendar.plan_days(
                    self.days + 1, deadline, compute_leaves=True
                )
                create_date = ticket.create_date

                deadline = deadline.replace(
                    hour=create_date.hour,
                    minute=create_date.minute,
                    second=create_date.second,
                    microsecond=create_date.microsecond,
                )

                deadline_for_working_cal = working_calendar.plan_hours(0, deadline)

                if (
                    deadline_for_working_cal
                    and deadline.day < deadline_for_working_cal.day
                ):
                    deadline = deadline.replace(
                        hour=0, minute=0, second=0, microsecond=0
                    )

            deadline = working_calendar.plan_hours(
                self.hours, deadline, compute_leaves=True
            )
            ticket.helpdesk_sla_deadline = deadline
            if ticket.helpdesk_sla_deadline < datetime.today().now():
                ticket.sla_expired = True
            else:
                ticket.sla_expired = False

class HelpdeskSLAStatus(models.Model):
    _name = 'helpdesk.sla.status'
    _description = "Ticket SLA Status"
    _table = 'helpdesk_sla_status'
    _order = 'deadline ASC, sla_stage_id'
    _rec_name = 'sla_id'

    ticket_id = fields.Many2one('axis.helpdesk.ticket', string='Ticket', required=True, ondelete='cascade', index=True)
    sla_id = fields.Many2one('axis.helpdesk.ticket.sla.policy', required=True, ondelete='cascade')
    sla_stage_id = fields.Many2one('axis.helpdesk.stage', related='sla_id.helpdesk_stage_id', store=True)  # need to be stored for the search in `ticket_sla_policy_reach`
    target_type = fields.Selection(related='sla_id.target_type', store=True)
    deadline = fields.Datetime("Deadline", compute='ticket_state_deadline', compute_sudo=True, store=True)
    reached_datetime = fields.Datetime("Reached Date")
    status = fields.Selection([('failed', 'Failed'), ('reached', 'Reached'), ('ongoing', 'Ongoing')], string="Status", compute='helpdesk_status_compute', compute_sudo=True, search='helpdesk_search_status_compute')
    color = fields.Integer("Color Index", compute='helpdesk_sla_policy_color')
    exceeded_days = fields.Float("Excedeed Working Days", compute='helpdesk_sla_policy_exceed', compute_sudo=True, store=True, help="Working days exceeded for reached SLAs compared with deadline. Positive number means the SLA was eached after the deadline.")
    time_days = fields.Integer('Days', default=0, required=True)

    @api.depends('ticket_id.create_date', 'sla_id', 'ticket_id.helpdesk_stage_id')
    def ticket_state_deadline(self):
        for status in self:
            if (status.deadline and status.reached_datetime) or (status.deadline and status.target_type == 'stage' and not status.sla_id.exclude_stage_ids) or (status.status == 'failed'):
                continue
            if status.target_type == 'assigning' and status.sla_stage_id == status.ticket_id.helpdesk_stage_id:
                deadline = fields.Datetime.now()
            elif status.target_type == 'assigning' and status.sla_stage_id:
                status.deadline = False
                continue
            else:
                deadline = status.ticket_id.create_date
            working_calendar = status.ticket_id.helpdesk_team_id.resource_calendar_id
            if not working_calendar:
                # Normally, having a working_calendar is mandatory
                status.deadline = deadline
                continue

            if status.target_type == 'stage' and status.sla_id.exclude_stage_ids:
                if status.ticket_id.helpdesk_stage_id in status.sla_id.exclude_stage_ids:
                    # We are in the freezed time stage: No deadline
                    status.deadline = False
                    continue

            days = status.sla_id.days
            if days and (status.sla_id.target_type == 'stage' or status.sla_id.target_type == 'assigning' and not status.sla_id.stage_id):
                deadline = working_calendar.plan_days(days + 1, deadline, compute_leaves=True)
                create_dt = status.ticket_id.create_date
                deadline = deadline.replace(hour=create_dt.hour, minute=create_dt.minute, second=create_dt.second, microsecond=create_dt.microsecond)
            elif days and status.target_type == 'assigning' and status.sla_stage_id == status.ticket_id.stage_id:
                deadline = working_calendar.plan_days(days + 1, deadline, compute_leaves=True)
                reached_stage_dt = fields.Datetime.now()
                deadline = deadline.replace(hour=reached_stage_dt.hour, minute=reached_stage_dt.minute, second=reached_stage_dt.second, microsecond=reached_stage_dt.microsecond)

            sla_hours = status.sla_id.hours + (status.sla_id.time_minutes / 60)

            if status.target_type == 'stage' and status.sla_id.exclude_stage_ids:
                sla_hours += status._get_freezed_hours(working_calendar)

                deadline_for_working_cal = working_calendar.plan_hours(0, deadline)
                if deadline_for_working_cal and deadline.day < deadline_for_working_cal.day:
                    deadline = deadline.replace(hour=0, minute=0, second=0, microsecond=0)
            status.deadline = working_calendar.plan_hours(sla_hours, deadline, compute_leaves=True)

    @api.depends('deadline', 'reached_datetime')
    def helpdesk_status_compute(self):
        for status in self:
            if status.reached_datetime and status.deadline:  # if reached_datetime, SLA is finished: either failed or succeeded
                status.status = 'reached' if status.reached_datetime < status.deadline else 'failed'
            else:
                status.status = 'ongoing' if not status.deadline or status.deadline > fields.Datetime.now() else 'failed'

    @api.model
    def helpdesk_search_status_compute(self, operator, value):
        datetime_now = fields.Datetime.now()
        positive_domain = {
            'failed': ['|', '&', ('reached_datetime', '=', True), ('deadline', '<=', 'reached_datetime'), '&', ('reached_datetime', '=', False), ('deadline', '<=', fields.Datetime.to_string(datetime_now))],
            'reached': ['&', ('reached_datetime', '=', True), ('reached_datetime', '<', 'deadline')],
            'ongoing': ['&', ('reached_datetime', '=', False), ('deadline', '<=', fields.Datetime.to_string(datetime_now))]
        }
        if not isinstance(value, list):
            value = [value]
        if operator in expression.NEGATIVE_TERM_OPERATORS:
            domains_to_keep = [dom for key, dom in positive_domain if key not in value]
            return expression.OR(domains_to_keep)
        else:
            return expression.OR(positive_domain[value_item] for value_item in value)

    @api.depends('status')
    def helpdesk_sla_policy_color(self):
        for status in self:
            if status.status == 'failed':
                status.color = 1
            elif status.status == 'reached':
                status.color = 10
            else:
                status.color = 0

    @api.depends('deadline', 'reached_datetime')
    def helpdesk_sla_policy_exceed(self):
        for status in self:
            if status.reached_datetime and status.deadline and status.ticket_id.helpdesk_team_id.resource_calendar_id:
                if status.reached_datetime <= status.deadline:
                    start_dt = status.reached_datetime
                    end_dt = status.deadline
                    factor = -1
                else:
                    start_dt = status.deadline
                    end_dt = status.reached_datetime
                    factor = 1
                duration_data = status.ticket_id.helpdesk_team_id.resource_calendar_id.get_work_duration_data(start_dt, end_dt, compute_leaves=True)
                status.exceeded_days = duration_data['days'] * factor
            else:
                status.exceeded_days = False

    def _get_freezed_hours(self, working_calendar):
        self.ensure_one()
        hours_freezed = 0

        field_stage = self.env['ir.model.fields']._get(self.ticket_id._name, "helpdesk_stage_id")
        freeze_stages = self.sla_id.exclude_stage_ids.ids
        tracking_lines = self.ticket_id.message_ids.tracking_value_ids.filtered(lambda tv: tv.field == field_stage).sorted(key="create_date")

        if not tracking_lines:
            return 0

        old_time = self.ticket_id.create_date
        for tracking_line in tracking_lines:
            if tracking_line.old_value_integer in freeze_stages:
                hours_freezed += working_calendar.get_work_hours_count(old_time, tracking_line.create_date)
            old_time = tracking_line.create_date
        if tracking_lines[-1].new_value_integer in freeze_stages:
            hours_freezed += working_calendar.get_work_hours_count(old_time, fields.Datetime.now())
        return hours_freezed
