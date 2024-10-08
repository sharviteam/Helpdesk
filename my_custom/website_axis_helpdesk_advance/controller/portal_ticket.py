# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import http , _, SUPERUSER_ID
from odoo.addons.portal.controllers.portal import pager as portal_pager, CustomerPortal
import base64
import io
from werkzeug.utils import redirect
from datetime import datetime,date,timedelta
import calendar
# import datetime
from odoo import http
from odoo.http import request
from odoo.osv.expression import AND ,OR
import dateutil.relativedelta
from odoo.exceptions import AccessError, MissingError, UserError
from odoo.tools import groupby as groupbyelem
from operator import itemgetter

@http.route('/search_helpdesk_tickets', type='http', auth='user', website=True)
def search_helpdesk_tickets(self , **kwargs):
        ticket_ids = request.env['axis.helpdesk.ticket'].sudo().search([])
        return  request.render('website_axis_helpdesk_advance.helpdesk_ticket_search', {'ticket': ticket_ids})

class ViewPortalHelpdesk(CustomerPortal):

    def _prepare_portal_layout_values(self): # Change
        values = super(ViewPortalHelpdesk, self)._prepare_portal_layout_values()
        if values.get('sales_user', False):
            values['heading'] = _("Salesperson")
        return values
    #
    # def _prepare_home_portal_values(self):
        # values = self._prepare_home_portal_values()
        # return request.render("portal.portal_my_home", values)
        # values = super()._prepare_home_portal_values()
        # print("counters",self)
        # 5/0
        # if 'ticket_count' in counters:
        #     self['ticket_count'] = request.env['axis.helpdesk.ticket'].search_count([])
        # return values
    def _prepare_home_portal_values(self, counters):
        values = super()._prepare_home_portal_values(counters)
        if 'ticket_count' in counters:
            values['ticket_count'] = request.env['axis.helpdesk.ticket'].search_count([])
        return values

    def page_view__value_ticket(self, helpdesk_ticket, access_token, **kwargs):
        values = {
            'page_name': 'Helpdesk Ticket',
            'ticket': helpdesk_ticket,
        }
        return self._get_page_view_values(helpdesk_ticket, access_token, values, 'my_tickets_history', False, **kwargs)

    @http.route('/web/login', type='http', auth='public', website=True)
    def web_login(self, redirect=None, **kw):
        if request.httprequest.method == 'POST':
            # Perform the login
            login = request.params['login']
            password = request.params['password']
            uid = request.session.authenticate(request.session.db, login, password)
            if uid:
                # Redirect to the custom page after login
                return request.redirect('/#')
        # If not a POST request or login failed, show the login page
        return request.render('web.login', {})

    @http.route(['/my/tickets/dates'], type='json', auth="user",website=True)
    def tickets_dates(self, dates):
        print ("aaaaaaaaaaaaaaaaaaaa",dates)
        values = self._prepare_portal_layout_values()
        searchbar_sortings = {
            'stage': {'label': _('Stage'), 'order': 'helpdesk_stage_id'},
            'name': {'label': _('Subject'), 'order': 'name'},
            'reference': {'label': _('Reference'), 'order': 'id'},
            'update': {'label': _('Last Stage Update'), 'order': 'date_last_stage_update desc'},
            'date': {'label': _('Newest'), 'order': 'create_date desc'},
        }
        searchbar_filters = {
            'all': {'label': _('All'), 'domain': []},
            'assigned': {'label': _('Assigned'), 'domain': [('res_user_id', '!=', False)]},
            'unassigned': {'label': _('Unassigned'), 'domain': [('res_user_id', '=', False)]},
            'open': {'label': _('Open'), 'domain': [('closed_date', '=', False)]},
            'closed': {'label': _('Closed'), 'domain': [('closed_date', '!=', False)]},
            'last_message_sup': {'label': _('Last message is from support')},
            'last_message_cust': {'label': _('Last message is from customer')},
        }
        axis_ticket_search_status_data = {
            'id': {'input': 'id', 'label': _('Search in Reference')},
            'status': {'input': 'status', 'label': _('Search in Stage')},
            'message': {'input': 'message', 'label': _('Search in Messages')},
            'all': {'input': 'all', 'label': _('Search in All')},
            'customer': {'input': 'customer', 'label': _('Search in Customer')},
            'content': {'input': 'content', 'label': _('Search <span class="nolabel"> (in Content)</span>')},
        }
        searchbar_groupby = {
            'none': {'input': 'none', 'label': _('None')},
            'stage': {'input': 'helpdesk_stage_id', 'label': _('Stage')},
        }
        sortby = None
        # default sort by value
        if not sortby:
            sortby = 'date'
        order = searchbar_sortings[sortby]['order']
        #
        # if filterby in ['last_message_sup', 'last_message_cust']:
        #     discussion_subtype_id = request.env.ref('mail.mt_comment').id
        #     messages = request.env['mail.message'].sudo().search_read([('model', '=', 'axis.helpdesk.ticket'), ('subtype_id', '=', discussion_subtype_id)], fields=['res_id', 'author_id'], order='date desc')
        #     last_author_dict = {}
        #     for message in messages:
        #         if message['res_id'] not in last_author_dict:
        #             last_author_dict[message['res_id']] = message['author_id'][0]
        #
        #     ticket_author_list = request.env['axis.helpdesk.ticket'].sudo().search_read(fields=['id', 'partner_id'])
        #     ticket_author_dict = dict([(ticket_author['id'], ticket_author['partner_id'][0] if ticket_author['partner_id'] else False) for ticket_author in ticket_author_list])
        #
        #     last_message_cust = []
        #     last_message_sup = []
        #     for ticket_id in last_author_dict.keys():
        #         if last_author_dict[ticket_id] == ticket_author_dict[ticket_id]:
        #             last_message_cust.append(ticket_id)
        #         else:
        #             last_message_sup.append(ticket_id)
        #
        #     if filterby == 'last_message_cust':
        #         domain = [('id', 'in', last_message_cust)]
        #     else:
        #         domain = [('id', 'in', last_message_sup)]
        #
        # else:
        #     domain = searchbar_filters[filterby]['domain']
        #
        # if date_start and date_end:
        #     domain += [('create_date', '>', date_start), ('create_date', '<=', date_end)]
        #
        # # search
        # if search and search_in:
        #     axis_ticket_ids = []
        #     if search_in in ('id', 'all'):
        #         axis_ticket_ids = OR([axis_ticket_ids, [('id', 'ilike', search)]])
        #     if search_in in ('content', 'all'):
        #         axis_ticket_ids = OR([axis_ticket_ids, ['|', ('name', 'ilike', search), ('description', 'ilike', search)]])
        #     if search_in in ('customer', 'all'):
        #         axis_ticket_ids = OR([axis_ticket_ids, [('partner_id', 'ilike', search)]])
        #     if search_in in ('message', 'all'):
        #         discussion_subtype_id = request.env.ref('mail.mt_comment').id
        #         axis_ticket_ids = OR([axis_ticket_ids, [('message_ids.body', 'ilike', search), ('message_ids.subtype_id', '=', discussion_subtype_id)]])
        #     if search_in in ('status', 'all'):
        #         axis_ticket_ids = OR([axis_ticket_ids, [('helpdesk_stage_id', 'ilike', search)]])
        #     domain += axis_ticket_ids
        #
        # # pager
        # total_ticket_ids = len(request.env['axis.helpdesk.ticket'].sudo().search(domain))
        pager = portal_pager(
            url="/my/tickets",
            url_args={},
            total=100,
            page=1,
            step=self._items_per_page
        )
        tickets = request.env['axis.helpdesk.ticket'].sudo().search([('id','=',4)],  limit=self._items_per_page)

        request.session['my_tickets_history'] = tickets.ids[:100]
        groupby = 'stage'
        if groupby == 'stage':
            ticket_agam_help_id = [request.env['axis.helpdesk.ticket'].concat(*g) for k, g in groupbyelem(tickets, itemgetter(searchbar_groupby[groupby]['input']))]
        else:
            ticket_agam_help_id = [tickets]
        values.update({
            'ticket_agam_help_id': ticket_agam_help_id,
            'tickets': tickets,
            'page_name': 'ticket',
            'default_url': '/my/tickets',
            'pager': pager,
            'searchbar_sortings': searchbar_sortings,
            'searchbar_filters': searchbar_filters,
            'axis_ticket_search_status_data': axis_ticket_search_status_data,
            'searchbar_groupby': searchbar_groupby,
            'sortby': sortby,
            'groupby': groupby,
            'search_in': None,
            'search': None,
            'filterby': None,


        })
        return request.render("website_axis_helpdesk_advance.view_helpdesk_ticket_portal", values)


    @http.route(['/my/tickets', '/my/tickets/page/<int:page>'], type='http', auth="user", website=True)
    def axis_helpdesk_ticket(self, page=1, date_start=None, date_end=None, sortby=None, filterby='all', search=None, groupby='none', search_in='content', **kw):
        values = self._prepare_portal_layout_values()
        searchbar_sortings = {
            'stage': {'label': _('Stage'), 'order': 'helpdesk_stage_id'},
            'name': {'label': _('Subject'), 'order': 'name'},
            'reference': {'label': _('Reference'), 'order': 'id'},
            'update': {'label': _('Last Stage Update'), 'order': 'date_last_stage_update desc'},
            'date': {'label': _('Newest'), 'order': 'create_date desc'},
        }
        searchbar_filters = {
            'all': {'label': _('All'), 'domain': []},
            'assigned': {'label': _('Assigned'), 'domain': [('res_user_id', '!=', False)]},
            'unassigned': {'label': _('Unassigned'), 'domain': [('res_user_id', '=', False)]},
            'open': {'label': _('Open'), 'domain': [('closed_date', '=', False)]},
            'closed': {'label': _('Closed'), 'domain': [('closed_date', '!=', False)]},
            'last_message_sup': {'label': _('Last message is from support')},
            'last_message_cust': {'label': _('Last message is from customer')},
        }
        axis_ticket_search_status_data = {
            'id': {'input': 'id', 'label': _('Search in Reference')},
            'status': {'input': 'status', 'label': _('Search in Stage')},
            'message': {'input': 'message', 'label': _('Search in Messages')},
            'all': {'input': 'all', 'label': _('Search in All')},
            'customer': {'input': 'customer', 'label': _('Search in Customer')},
            'content': {'input': 'content', 'label': _('Search <span class="nolabel"> (in Content)</span>')},
        }
        searchbar_groupby = {
            'none': {'input': 'none', 'label': _('None')},
            'stage': {'input': 'helpdesk_stage_id', 'label': _('Stage')},
        }

        # default sort by value
        if not sortby:
            sortby = 'date'
        order = searchbar_sortings[sortby]['order']

        # Get the logged-in user
        user = request.env.user

        # Adjust the domain for filtering tickets
        if user.has_group('base.group_system'):  # Admin can see all tickets
            domain = searchbar_filters[filterby]['domain']
        else:  # Regular user (internal or portal) sees only their own tickets
            domain = searchbar_filters[filterby]['domain'] + [
                '|',
                ('res_user_id', '=', user.id),  # Assigned to the user
                ('partner_id', '=', user.partner_id.id)  # Or created by the user (portal user)
            ]
        # Handle special filters like last_message_sup or last_message_cust
        if filterby in ['last_message_sup', 'last_message_cust']:
            discussion_subtype_id = request.env.ref('mail.mt_comment').id
            messages = request.env['mail.message'].sudo().search_read(
                [('model', '=', 'axis.helpdesk.ticket'), ('subtype_id', '=', discussion_subtype_id)],
                fields=['res_id', 'author_id'], order='date desc')
            last_author_dict = {}
            for message in messages:
                if message['res_id'] not in last_author_dict:
                    last_author_dict[message['res_id']] = message['author_id'][0]

            ticket_author_list = request.env['axis.helpdesk.ticket'].sudo().search_read(fields=['id', 'partner_id'])
            ticket_author_dict = dict([(ticket_author['id'], ticket_author['partner_id'][0] if ticket_author['partner_id'] else False) for ticket_author in ticket_author_list])

            last_message_cust = []
            last_message_sup = []
            for ticket_id in last_author_dict.keys():
                if last_author_dict[ticket_id] == ticket_author_dict[ticket_id]:
                    last_message_cust.append(ticket_id)
                else:
                    last_message_sup.append(ticket_id)

            if filterby == 'last_message_cust':
                domain = [('id', 'in', last_message_cust)]
            else:
                domain = [('id', 'in', last_message_sup)]

        else:
            domain = searchbar_filters[filterby]['domain']

        if date_start and date_end:
            domain += [('create_date', '>', date_start), ('create_date', '<=', date_end)]

        # search logic
        if search and search_in:
            axis_ticket_ids = []
            if search_in in ('id', 'all'):
                axis_ticket_ids = OR([axis_ticket_ids, [('id', 'ilike', search)]])
            if search_in in ('content', 'all'):
                axis_ticket_ids = OR([axis_ticket_ids, ['|', ('name', 'ilike', search), ('description', 'ilike', search)]])
            if search_in in ('customer', 'all'):
                axis_ticket_ids = OR([axis_ticket_ids, [('partner_id', 'ilike', search)]])
            if search_in in ('message', 'all'):
                discussion_subtype_id = request.env.ref('mail.mt_comment').id
                axis_ticket_ids = OR([axis_ticket_ids, [('message_ids.body', 'ilike', search), ('message_ids.subtype_id', '=', discussion_subtype_id)]])
            if search_in in ('status', 'all'):
                axis_ticket_ids = OR([axis_ticket_ids, [('helpdesk_stage_id', 'ilike', search)]])
            domain += axis_ticket_ids

        # pager
        total_ticket_ids = len(request.env['axis.helpdesk.ticket'].sudo().search(domain))
        pager = portal_pager(
            url="/my/tickets",
            url_args={'date_start': date_start, 'date_end': date_end, 'sortby': sortby, 'search_in': search_in, 'search': search},
            total=total_ticket_ids,
            page=page,
            step=self._items_per_page
        )
        tickets = request.env['axis.helpdesk.ticket'].sudo().search(domain, order=order, limit=self._items_per_page, offset=pager['offset'])

        if groupby == 'stage':
            ticket_agam_help_id = [request.env['axis.helpdesk.ticket'].concat(*g) for k, g in groupbyelem(tickets, itemgetter(searchbar_groupby[groupby]['input']))]
        else:
            ticket_agam_help_id = [tickets]

        values.update({
            'date': date_start,
            'ticket_agam_help_id': ticket_agam_help_id,
            'tickets': tickets,
            'page_name': 'ticket',
            'default_url': '/my/tickets',
            'pager': pager,
            'searchbar_sortings': searchbar_sortings,
            'searchbar_filters': searchbar_filters,
            'axis_ticket_search_status_data': axis_ticket_search_status_data,
            'searchbar_groupby': searchbar_groupby,
            'sortby': sortby,
            'groupby': groupby,
            'search_in': search_in,
            'search': search,
            'filterby': filterby,
        })
        return request.render("website_axis_helpdesk_advance.view_helpdesk_ticket_portal", values)
        
    def helpdesk_ticket_view_page_val(self, ticket, access_token, **kwargs):
        values = {
            'page_name': 'ticket',
            'ticket': ticket,
        }
        return self._get_page_view_values(ticket, access_token, values, 'my_tickets_history', False, **kwargs)

    @http.route([
        "/axis/helpdesk/ticket/<int:ticket_id>",
        "/axis/helpdesk/ticket/<int:ticket_id>/<access_token>",
        '/axis/my/ticket/<int:ticket_id>',
        '/axis/my/ticket/<int:ticket_id>/<access_token>'
    ], type='http', auth="public", website=True)
    def helpdesk_ticket_view_form_portal(self, ticket_id=None, access_token=None, **kw):
        try:
            ticket_sudo = self._document_check_access('axis.helpdesk.ticket', ticket_id, access_token)
        except (AccessError, MissingError):
            return request.redirect('/my')

        values = self.helpdesk_ticket_view_page_val(ticket_sudo, access_token, **kw)
        values.update({
            'ticket': ticket_sudo,
            'message_ids': ticket_sudo.message_ids.sudo(),
            # Pass res_model and res_id to the chatter initialization
            'res_model': 'axis.helpdesk.ticket',
            'res_id': ticket_sudo.id,
        })
        return request.render("website_axis_helpdesk_advance.axis_helpdesk_ticket_portal_view", values)
    @http.route([
        '/my/ticket/close/<int:ticket_id>',
        '/my/ticket/close/<int:ticket_id>/<access_token>',
    ], type='http', auth="public", website=True)
    def ticket_close(self, ticket_id=None, access_token=None, **kw):

        current_date = datetime.now()
        try:
            ticket_sudo = self._document_check_access('axis.helpdesk.ticket', ticket_id, access_token)
        except (AccessError, MissingError):
            return request.redirect('/my')

        if not ticket_sudo.helpdesk_team_id.allow_portal_ticket_closing:
            raise UserError(_("The team does not allow ticket closing through portal"))

        if not ticket_sudo.closed_by_partner:
            closing_stage = ticket_sudo.helpdesk_team_id._ticket_get_close_stage()
            if ticket_sudo.helpdesk_stage_id != closing_stage:

                ticket_sudo.write({'helpdesk_stage_id': closing_stage[0].id,
                                   'closed_by_partner': True,
                                   'close_ticket_date': current_date})
            else:
                ticket_sudo.write({'closed_by_partner': True, 'close_ticket_date': current_date})
            body = _('Ticket closed by the customer')
            print("access tokken >>>>>>>>>>>>>>>>>>>",access_token)
            # 5/0
            ticket_sudo.with_context(mail_create_nosubscribe=True).message_post(body=body, message_type='comment', subtype_xmlid='mail.mt_note')
        return request.redirect('/axis/helpdesk/ticket/%s' % (ticket_id))

    @http.route(['/helpdesk/rating/submit'], type='http', auth="public", website=True)
    def index_submit(self, access_token=None, **post):
        ticket = request.env['axis.helpdesk.ticket'].sudo().search([('id','=',post.get('id'))])
        if post.get('rating') == 'poor':
            ticket.priority_new = '1'
        if post.get('rating') == 'average':
            ticket.priority_new = '2'
        if post.get('rating') == 'good':
            ticket.priority_new = '3'
        if post.get('rating') == 'excellent':
            ticket.priority_new = '4'
        if post.get('comment'):
            ticket.write({'comment': post.get('comment')})
        return request.render('website_axis_helpdesk_advance.rating_submit')

class axisHelpdeskTicket(http.Controller):

    def helpdesk_ticket_view_page_val(self, helpdesk_ticket, access_token, **kwargs):
        values = {
            'page_name': 'Helpdesk Ticket',
            'ticket': helpdesk_ticket,
        }
        return self._get_page_view_values(helpdesk_ticket, access_token, values, 'my_tickets_history', False, **kwargs)

    @http.route('/getData', type='json', auth='public', website=True)
    def getData(self, **kwargs):
        domain = []
        if kwargs.get('teamLead_id'):
            teamlead_id = int(kwargs.get('teamLead_id'))
            domain.append(('res_user_id', '=', teamlead_id))
        if kwargs.get('team_id'):
            team_id = int(kwargs.get('helpdesk_team_id'))
            domain.append(('helpdesk_team_id', '=', team_id))
        if kwargs.get('ticket_type_id'):
            ticket_type_id = int(kwargs.get('ticket_type_id'))
            domain.append(('helpdesk_ticket_type_id', '=', ticket_type_id))
        if kwargs.get('assignUser_id'):
            assignUser_id = int(kwargs.get('assignUser_id'))
            domain.append(('res_user_id', '=', assignUser_id))

        if kwargs.get('custome_date_id'):
            custome_date_id = kwargs.get('custome_date_id')
            if custome_date_id:
                date_str = custome_date_id
                date_obj = datetime.strptime(date_str, '%Y-%m-%d')
                today = date.today()
                start_date = date_obj
                end_date = datetime(today.year, today.month, today.day, 23, 59, 59)
                domain.append(('create_date', '>=', start_date))
                domain.append(('create_date', '<=', end_date))

        if kwargs.get('date_id'):
            date_id = int(kwargs.get('date_id'))
            if date_id == 1:
                today = date.today()
                start_date = datetime(today.year, today.month, today.day)
                end_date = datetime(today.year, today.month, today.day, 23, 59, 59)
                domain.append(('create_date', '>=', start_date))
                domain.append(('create_date', '<=', end_date))
            if date_id == 2:
                today = date.today()
                yesterday = today - timedelta(days=1)
                start_date = datetime(yesterday.year, yesterday.month, yesterday.day)
                end_date = datetime(yesterday.year, yesterday.month, yesterday.day, 23, 59, 59)
                domain.append(('create_date', '>=', start_date))
                domain.append(('create_date', '<=', end_date))
            if date_id == 3:
                date_obj = date.today()
                start_of_week = date_obj - timedelta(days=date_obj.weekday())  # Monday
                end_of_week = start_of_week + timedelta(days=6)  # Sunday
                domain.append(('create_date', '>=', start_of_week))
                domain.append(('create_date', '<=', end_of_week))

            if date_id == 4:
                date_obj = date.today()
                start_of_week = date_obj + timedelta(days=-date_obj.weekday(), weeks=-1)  # Monday
                end_of_week = date_obj + timedelta(-date_obj.weekday() - 1)  # Sunday
                domain.append(('create_date', '>=', start_of_week))
                domain.append(('create_date', '<=', end_of_week))
            if date_id == 5:
                date_obj = date.today()
                start_of_month = date_obj.replace(day=1)
                end_of_month = date_obj.replace(day=calendar.monthrange(date_obj.year, date_obj.month)[1])
                domain.append(('create_date', '>=', start_of_month))
                domain.append(('create_date', '<=', end_of_month))
            if date_id == 6:
                date_obj = date.today()
                date_obj = date_obj + dateutil.relativedelta.relativedelta(months=-1)
                start_of_month = date_obj.replace(day=1)
                end_of_month = date_obj.replace(day=calendar.monthrange(date_obj.year, date_obj.month)[1])
                domain.append(('create_date', '>=', start_of_month))
                domain.append(('create_date', '<=', end_of_month))

            if date_id == 7:
                date_obj = date.today()
                x = ('%s-01-01' % (date_obj.year))
                y = ('%s-12-31' % (date_obj.year))
                start_of_year = datetime.strptime(x, '%Y-%m-%d')
                end_of_year = datetime.strptime(y, '%Y-%m-%d')
                domain.append(('create_date', '>=', start_of_year))
                domain.append(('create_date', '<=', end_of_year))

            if date_id == 8:
                date_obj = date.today()
                x = ('%s-01-01' % (date_obj.year - 1))
                y = ('%s-12-31' % (date_obj.year - 1))
                start_of_year = datetime.strptime(x, '%Y-%m-%d')
                end_of_year = datetime.strptime(y, '%Y-%m-%d')
                domain.append(('create_date', '>=', start_of_year))
                domain.append(('create_date', '<=', end_of_year))

            if date_id == 9:
                date_str = '2021-07-06'
                date_obj = datetime.strptime(date_str, '%Y-%m-%d')
                start_of_week = date_obj - timedelta(days=date_obj.weekday())  # Monday

        ticket_ids_filter = request.env['axis.helpdesk.ticket'].sudo().search(domain,order='helpdesk_stage_id asc')
        user_company_id = request.env.user.company_id
        lst_stage = []
        for ticket_data in ticket_ids_filter:
            lst_stage.append({'helpdesk_stage_id': ticket_data.helpdesk_stage_id.name,
                'number': ticket_data.number or "",
                'partner_id': ticket_data.partner_id.name or "",
                'create_date': ticket_data.create_date or "",
                'write_date': ticket_data.write_date or "",
                'res_user_id': ticket_data.res_user_id.name or "",
            })
        result = {
            'ticket_ids':lst_stage,
        }
        return result

    @http.route('/search_helpdesk_tickets', type='http', auth='user', website=True)
    def search_create_helpdesk_tickets_details(self, **kwargs):
        helpdesk_tickets = request.env['axis.helpdesk.ticket'].sudo().search([])
        return request.render('website_axis_helpdesk_advance.helpdesk_ticket_search', {'ticket': helpdesk_tickets})


    @http.route(['/helpdesk/search/ticket'], type='http', methods=['POST'], auth='user', website=True, csrf=False)
    def helpdesk_search_ticket(self, **kwargs):
        # ticket_id = request.env['axis.helpdesk.ticket'].search([('number', '=', kwargs.get('search'))])
        ticket_id = request.env['axis.helpdesk.ticket'].sudo().search([('number', 'like', kwargs.get('search'))], limit=1,
                                                               order='number asc')
        if ticket_id:
            return request.redirect('/axis/helpdesk/ticket/%s' % (ticket_id.id))
        else:
            return request.render('website_axis_helpdesk_advance.helpdesk_error_message', {'error_message': ticket_id})

    @http.route(['/helpdesk/form'], type='http', auth="public", website=True)
    def helpdesk_form(self, **post):
        helpdesk_tickets = request.env['axis.helpdesk.ticket'].sudo().search([])
        helpdesk_tickets_type = request.env['axis.helpdesk.ticket.type'].sudo().search([])
        res_config_param = request.env['res.config.settings'].sudo().search([])
        if res_config_param:
            res_config = request.env['res.config.settings'].sudo().search([])[-1]
        else:
            res_config = res_config_param


        # context = request._context
        # current_uid = context.get('uid')
        user = request.env['res.users'].browse(request.uid)
        if user:
            partner_name = user.name
            partner_email =user.email
        else:
            partner_name = ""
            partner_email = ""
        return request.render("website_axis_helpdesk_advance.helpdesk_create_ticket_from_front_end",
                              {'my_tickets': helpdesk_tickets,
                               'ticket_types': helpdesk_tickets_type,
                               'partner_name': partner_name,
                               'partner_email': partner_email,
                               'is_attachment': res_config.is_attachment,})

    @http.route(['/helpdesk/form/submit'], type='http', auth="public", website=True)
    def helpdesk_form_submit(self, **post):
        tickettype_id = request.env['axis.helpdesk.ticket.type'].sudo().search([('id','=', post.get('ticket_type_id'))], limit=1)
        res_user_id = ''
        if tickettype_id.team_ids.assigning_method == 'randomly':
            if tickettype_id.team_ids.res_user_ids:
                res_user_id = tickettype_id.team_ids.res_user_ids[0].id

        #WORKING 
        stage = request.env['axis.helpdesk.stage'].sudo().search([('name','=', 'New')])
        ticket = request.env['axis.helpdesk.ticket'].sudo().create({
            'helpdesk_ticket_type_id': post.get('ticket_type_id'),
            'name': post.get('name'),
            'partner_name': post.get('partner_name'),
            'partner_email': post.get('partner_email'),
            'priority': post.get('priority'),
            'description': post.get('description'),
            'product_boolean':True,
            'helpdesk_stage_id': stage.id,
            'helpdesk_team_id': tickettype_id.team_ids.id,
            'client_id': tickettype_id.team_ids.client_id.id,
            'res_user_id': res_user_id,

        })
        if post.get('attachment'):
            file = post.get('attachment')
            name = post.get('attachment').filename

            attachment_id = request.env['ir.attachment'].sudo().create({
                'name': name,
                'res_name': name,
                'type': 'binary',
                'datas': base64.b64encode(file.read()),
                'res_model': 'axis.helpdesk.ticket',
                'res_id': ticket.id
            })

            ticket.sudo().write({'attachment_ids': [(6, 0, attachment_id.ids)]})
        # config_id = request.env['res.config.settings'].search([], limit=1, order='id desc')
        # if config_id.manage_product:
        #     ticket.product_boolean = True
        vals = {
            'ticket': ticket,
        }
        return request.render("website_axis_helpdesk_advance.view_helpdesk_ticket_sla_policy_success", vals)

    @http.route(['/ticket/attachment/download/<int:attachment_id>'], type='http', auth="user", website=True)
    def download_attcahment_tickets(self, attachment_id=None, **post):
        attachment = request.env['ir.attachment'].sudo().search_read(
            [('id', '=', int(attachment_id))],
            ["name", "datas", "type", "res_model", "res_id", "type", "url"]
        )
        if attachment:
            attachment = attachment[0]
        else:
            return redirect('//ticket/attachment/download/%s' % attachment_id)

        if attachment["type"] == "url":
            if attachment["url"]:
                return redirect(attachment["url"])
            else:
                return request.not_found()
        elif attachment["datas"]:
            data = io.BytesIO(base64.standard_b64decode(attachment["datas"]))
            return http.send_file(data, filename=attachment['name'], as_attachment=True)
        else:
            return request.not_found()

    @http.route(['/portal/get_id'], type='json', auth="user", website=True, csrf=False)
    def get_ticket_id(self, **post):
        base_value = request.params['id']
        send_data = request.env['axis.helpdesk.ticket'].sudo().search([('id', '=', base_value)])
        if request.env.is_admin():
            send_data.is_customer_replied = False
        else:
            send_data.is_customer_replied = True

class TicketRating(http.Controller):

    @http.route(['/helpdesk/rating', '/helpdesk/rating/<model("axis.helpdesk.ticket.team"):team>'], type='http', auth="public", website=True, sitemap=True)
    def page(self, team=False, **kw):
        user = request.env.user
        team_domain = [('id', '=', team.id)] if team else []
        if user.has_group('website_axis_helpdesk_advance.group_helpdesk_ticket_manager'):
            domain = AND([[('use_rating', '=', True)], team_domain])
        else:
            domain = AND([[('use_rating', '=', True), ('portal_show_rating', '=', True)], team_domain])
        teams = request.env['axis.helpdesk.ticket.team'].sudo().search(domain)
        team_values = []
        for team in teams:
            tickets = request.env['axis.helpdesk.ticket'].sudo().search([('helpdesk_team_id', '=', team.id)])
            domain = [
                ('res_model', '=', 'axis.helpdesk.ticket'), ('res_id', 'in', tickets.ids),
                ('consumed', '=', True), ('rating', '>=', 1),
            ]
            ratings = request.env['rating.rating'].sudo().search(domain, order="id desc", limit=100)

            yesterday = (datetime.date.today()-datetime.timedelta(days=-1)).strftime('%Y-%m-%d 23:59:59')
            stats = {}
            any_rating = False
            for x in (7, 30, 90):
                todate = (datetime.date.today()-datetime.timedelta(days=x)).strftime('%Y-%m-%d 00:00:00')
                domdate = domain + [('create_date', '<=', yesterday), ('create_date', '>=', todate)]
                stats[x] = {1: 0, 3: 0, 5: 0}
                val_rating = request.env['rating.rating'].sudo().read_group(domdate, [], ['rating'])
                total = sum(st['rating_count'] for st in val_rating)
                for rate in val_rating:
                    any_rating = True
                    stats[x][rate['rating']] = (rate['rating_count'] * 100) / total
            values = {
                'team': team,
                'ratings': ratings if any_rating else False,
                'stats': stats,
            }
            team_values.append(values)
        return request.render('website_axis_helpdesk_advance.view_helpdesk_ticket_rating', {'page_name': 'rating', 'teams': team_values})

    @http.route('/reopen_ticket/<int:ticket_id>', type='http', auth="user", methods=['POST'], website=True)
    def reopen_ticket(self, ticket_id):
        # Find the ticket
        ticket = request.env['axis.helpdesk.ticket'].browse(ticket_id)
        
        # Get the "New" stage
        new_stage = request.env['axis.helpdesk.stage'].search([('name', '=', 'New')], limit=1)
        
        # Ensure the ticket exists and the stage was found
        if ticket and new_stage:
            # Update the stage of the ticket to "New"
            ticket.sudo().write({'helpdesk_stage_id': new_stage.id})

        # Redirect back to the ticket page or another relevant page
        return request.redirect('/my/tickets')