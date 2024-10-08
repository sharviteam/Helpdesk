/** @odoo-module **/
const { DateTime } = luxon;
import { serializeDate } from "@web/core/l10n/dates";

import {
    registry
} from "@web/core/registry";
import {
    useService
} from "@web/core/utils/hooks";
import {
    Component,
    EventBus,
    onWillStart,
    useSubEnv,
    useState,
    onMounted,
    onPatched
} from "@odoo/owl";
import {
    renderToElement
} from "@web/core/utils/render";

export class HelpdeskTicketDashboard extends Component {
    init() {
        this._super.apply(this, arguments);
        this.rpc = this.bindService("rpc");
    }
    setup() {
        this.orm = useService("orm");
        this.actionService = useService("action");

        this.variants = [];
        this.warehouses = [];
        this.showVariants = false;
        this.uomName = "";
        this.extraColumnCount = 0;
        this.unfoldedIds = new Set();
        this.state = useState({
            showOptions: {
                uom: false,
                availabilities: false || Boolean(this.props.action.context.activate_availabilities),
                costs: true,
                operations: true,
                leadTimes: true,
                attachments: false,
            },
            currentWarehouse: null,
            currentVariantId: null,
            bomData: {},
            precision: 2,
            bomQuantity: null,
        });

        useSubEnv({
            overviewBus: new EventBus(),
        });

        onWillStart(async () => {
            var self = this;
            await self.render_dashboards();
            await self.render_graphs();
            await self.render_graphsmonthly_car();
        });
        onMounted(() => {
            // do something
            var self = this;
            self.datadisplay();
            self.render_graphs();
            self.render_graphsmonthly_car();
//            self.get_order();
//            self.get_customer_count();
//            self.get_sale_order_cancel();
        });
        onPatched(() => {
            // do something
            var self = this;
            self.render_dashboards();
        });
    }
    action_my() {
        this.actionService.doAction({
            name: "Helpdesk Ticket",
            type: 'ir.actions.act_window',
            res_model: 'axis.helpdesk.ticket',
            view_mode: 'tree,form',
            view_type: 'list',
            views: [
                [false, 'list'],
                [false, 'form']
            ],
            views: [
                [false, 'list'],
                [false, 'form']
            ],
//            domain: [
//                ['state', '=', 'done']
            context: {
                        'search_default_my_ticket':true,
                        'search_default_is_open': false,
                    },
//            ],
            target: 'current'
        }, )
    }
    action_my_pending() {
        this.actionService.doAction({
            name: "Helpdesk Ticket",
            type: 'ir.actions.act_window',
            res_model: 'axis.helpdesk.ticket',
            view_mode: 'tree,form',
            view_type: 'list',
            views: [
                [false, 'list'],
                [false, 'form']
            ],
            views: [
                [false, 'list'],
                [false, 'form']
            ],
            context: {
                        'search_default_my_ticket':true,
                    },
         domain: [
            '|', // Start of OR condition
            ['helpdesk_stage_id.is_close', '=', false], // Not closed
            ['helpdesk_stage_id.name', '=', 'On Hold'] // Stage name is "On Hold"
        ],
        }, )
    }
    action_close_appointment() {
        this.actionService.doAction({
            name: "Helpdesk Ticket Pending",
            type: 'ir.actions.act_window',
            res_model: 'axis.helpdesk.ticket',
            view_mode: 'tree,form',
            view_type: 'list',
            views: [
                [false, 'list'],
                [false, 'form']
            ],
            domain: [
                ['helpdesk_stage_id.is_close', '=', true],
                ['helpdesk_stage_id.name', '!=', 'On Hold'],
                ['helpdesk_stage_id.name', '=', 'Done ']
            ],
            target: 'current'
        });
    }


        urgent() {

        this.actionService.doAction({
            name: "Urgent Ticket",
            type: 'ir.actions.act_window',
            res_model: 'axis.helpdesk.ticket',
            view_mode: 'tree,form',
            view_type: 'list',
            views: [
                [false, 'list'],
                [false, 'form']
            ],
            views: [
                [false, 'list'],
                [false, 'form']
            ],
            domain: [
                ['priority', '=', 3],
                // ['res_user_id', '>=', this.values.current_user]
            ],
            target: 'current'
        }, )
    }

            high_priority() {
        this.actionService.doAction({
            name: "High Priority Ticket",
            type: 'ir.actions.act_window',
            res_model: 'axis.helpdesk.ticket',
            view_mode: 'tree,form',
            view_type: 'list',
            views: [
                [false, 'list'],
                [false, 'form']
            ],
            views: [
                [false, 'list'],
                [false, 'form']
            ],
            domain: [
                ['priority', '=', 2],
                // ['res_user_id', '>=', this.values.current_user]
            ],
            target: 'current'
        }, )
    }

                medium() {
        this.actionService.doAction({
            name: "Medium Ticket",
            type: 'ir.actions.act_window',
            res_model: 'axis.helpdesk.ticket',
            view_mode: 'tree,form',
            view_type: 'list',
            views: [
                [false, 'list'],
                [false, 'form']
            ],
            views: [
                [false, 'list'],
                [false, 'form']
            ],
            domain: [
                ['priority', '=', 1],
                // ['res_user_id', '>=', this.values.current_user]
            ],
            target: 'current'
        }, )
    }

                low() {
        this.actionService.doAction({
            name: "Low Ticket",
            type: 'ir.actions.act_window',
            res_model: 'axis.helpdesk.ticket',
            view_mode: 'tree,form',
            view_type: 'list',
            views: [
                [false, 'list'],
                [false, 'form']
            ],
            views: [
                [false, 'list'],
                [false, 'form']
            ],
            domain: [
                ['priority', '=', 0],
            ],
            target: 'current'
        }, )
    }
            this_month() {
        let today = new Date();
            var firstDay = new Date(today.getFullYear(), today.getMonth(), 1);
                var lastDay = new Date(today.getFullYear(), today.getMonth() + 1, 0);


////        let yesterday = new Date(today);
//        today.setDate(today.getMonth() + 1);
//        var formattedYesterday = today.toISOString().slice(0, 10);
        console.log("MONTH________11______",firstDay.toISOString().slice(0, 10))
        console.log("MONTH______________",lastDay.toISOString().slice(0, 10))
        this.actionService.doAction({
            name: "This Month Count",
            type: 'ir.actions.act_window',
            res_model: 'axis.helpdesk.ticket',
            view_mode: 'tree,form',
            view_type: 'list',
            views: [
                [false, 'list'],
                [false, 'form']
            ],
            views: [
                [false, 'list'],
                [false, 'form']
            ],
            domain: [
//                ['helpdesk_stage_id.is_close', '=', true],
                ['create_date', '>=', firstDay.toISOString().slice(0, 10)],
                ['create_date', '<=', lastDay.toISOString().slice(0, 10)],
//                ['res_user_id', '=', this.values.current_user]
            ],
            target: 'current'
        }, )
    }

    this_week() {
        let today = new Date();

        let yesterday = new Date(today);
        yesterday.setDate(today.getDate() - 6);
        var formattedYesterday = yesterday.toISOString().slice(0, 10);
        this.actionService.doAction({
            name: "This Week Count",
            type: 'ir.actions.act_window',
            res_model: 'axis.helpdesk.ticket',
            view_mode: 'tree,form',
            view_type: 'list',
            views: [
                [false, 'list'],
                [false, 'form']
            ],
            views: [
                [false, 'list'],
                [false, 'form']
            ],
            domain: [
//                ['helpdesk_stage_id.is_close', '=', true],
                ['create_date', '>=', formattedYesterday],
            ],
            target: 'current'
        }, )
    }

    this_year() {
        let today = new Date();
            // Get the first day of the current year
    var firstDayOfYear = new Date(today.getFullYear(), 0, 1);

    // Get the last day of the current year
    var lastDayOfYear = new Date(today.getFullYear(), 11, 31);
//        let yesterday = new Date(today);
//        yesterday.setDate(today.getDate() - 365);
//        var formattedYesterday = yesterday.toISOString().slice(0, 10);
        this.actionService.doAction({
            name: "Total",
            type: 'ir.actions.act_window',
            res_model: 'axis.helpdesk.ticket',
            view_mode: 'tree,form',
            view_type: 'list',
            views: [
                [false, 'list'],
                [false, 'form']
            ],
            views: [
                [false, 'list'],
                [false, 'form']
            ],
            domain: [
//                ['helpdesk_stage_id.is_close', '=', true],
                ['create_date', '>=', firstDayOfYear.toISOString().slice(0, 10)],
                ['create_date', '<=', lastDayOfYear.toISOString().slice(0, 10)],
            ],
            target: 'current'
        }, )
    }

    action_success_tickets() {
        this.actionService.doAction({
            name: "Helpdesk Ticket",
            type: 'ir.actions.act_window',
            res_model: 'axis.helpdesk.ticket',
            view_mode: 'tree,form',
            view_type: 'list',
            views: [
                [false, 'list'],
                [false, 'form']
            ],
            domain: [
                ['helpdesk_stage_id.is_close', '=', true], // Closed tickets
                ['helpdesk_stage_id.name', '!=', 'On Hold'] // Exclude On Hold stage
            ],
            target: 'current'
        });
    }
    job_card() {
        this.actionService.doAction({
            name: "Job Roles",
            type: 'ir.actions.act_window',
            res_model: 'job.roles',
            view_mode: 'tree,form',
            view_type: 'list',
            views: [
                [false, 'list'],
                [false, 'form']
            ],
            views: [
                [false, 'list'],
                [false, 'form']
            ],
            target: 'current'
        }, )
    }
    card_contan() {
        this.actionService.doAction({
            name: "Car Parts",
            type: 'ir.actions.act_window',
            res_model: 'car.parts',
            view_mode: 'tree,form',
            view_type: 'list',
            views: [
                [false, 'list'],
                [false, 'form']
            ],
            views: [
                [false, 'list'],
                [false, 'form']
            ],
            target: 'current'
        }, )
    }
    card_maintence() {
        this.actionService.doAction({
            name: "Service Repair CheckList",
            type: 'ir.actions.act_window',
            res_model: 'maintenance.checklist',
            view_mode: 'tree,form',
            view_type: 'list',
            views: [
                [false, 'list'],
                [false, 'form']
            ],
            views: [
                [false, 'list'],
                [false, 'form']
            ],
            target: 'current'
        });
    }
    getRandomColor() {
        var letters = '0123456789ABCDEF'.split('');
        var color = '#';
        for (var i = 0; i < 6; i++) {
            color += letters[Math.floor(Math.random() * 16)];
        }
        return color;
    }
//    async get_order()
//    {
//        var self = this;
//        var result = await this.orm.call("sale.order", "get_sale_table", [])
//
//                if(result){
//
//                    var res = result.order
//                    var dataSet = []
//                    for(var i=0;i<res.length;i++){
//                        dataSet.push([res[i].order_reference, res[i].partner_name,res[i].date_order,res[i].delievery_date,'<span class="label label-success">' + '</span>'])
//                    }
//                    if(dataSet.length > 0){
//                        $('.sale').DataTable( {
//                            lengthChange : false,
//                            info: false,
//                            "destroy": true,
//                            "responsive": false,
//                            pagingType: 'simple',
//                            "pageLength": 4,
//                            language: {
//                                paginate: {
//                                    next: '<button type="button" class="btn btn-box-tool"><i class="fa fa-angle-right" /></button>',
//                                    previous: '<button type="button" class="btn btn-box-tool"><i class="fa fa-angle-left" /></button>'
//                                }
//                            },
//                            searching: false,
//                            data: dataSet,
//                            columns: [
//                                { title: "Order Reference" },
//                                { title: "Customer Name" },
//                                { title: "Creation Order" },
//                                { title: "Delivery Date" }
//                            ]
//                        });
//                    }
//                }
//
//    }
    action_today_appointment()
    {
    let today = new Date();

        let yesterday = new Date(today);
        var formattedDate = today.getFullYear() + '-' + ('0' + (today.getMonth() + 1)).slice(-2) + '-' + ('0' + today.getDate()).slice(-2);
        this.actionService.doAction({
            name: "Meetings",
            type: 'ir.actions.act_window',
            res_model: 'axis.helpdesk.ticket',
            view_mode: 'calendar,tree,form',
            view_type: 'list',
            views: [[false, 'list'],[false, 'calendar'],[false, 'form']],
            domain: [['create_date','>=',serializeDate(luxon.DateTime.now().plus({ days: 0 }))]],
            target: 'current'
        });
    }
    action_rejected_appointment()
    {
        this.actionService.doAction({
            name: "Meetings",
            type: 'ir.actions.act_window',
            res_model: 'calendar.event',
            view_mode: 'calendar,tree,form',
            view_type: 'list',
            views: [[false, 'list'],[false, 'calendar'],[false, 'form']],
            context: {
                        'search_default_rejected_appointment':true,
                    },
            domain: [['attendee_ids.state','in',['declined']]],
            target: 'current'
        });
    }
    action_sla_comp()
    {
     let today = new Date();

        let yesterday = new Date(today);
        var formattedDate = today.getFullYear() + '-' + ('0' + (today.getMonth() + 1)).slice(-2) + '-' + ('0' + today.getDate()).slice(-2);
        this.actionService.doAction({
            name: "SLA Complete",
            type: 'ir.actions.act_window',
            res_model: 'axis.helpdesk.ticket',
            view_mode: 'calendar,tree,form',
            view_type: 'list',
            views: [[false, 'list'],[false, 'form']],

            domain: [['helpdesk_stage_id.name', '=', 'Done'],['helpdesk_sla_deadline','<=',formattedDate]],
            target: 'current'
        });
    }

        action_sla_pending()
    {
     let today = new Date();

        let yesterday = new Date(today);
        var formattedDate = today.getFullYear() + '-' + ('0' + (today.getMonth() + 1)).slice(-2) + '-' + ('0' + today.getDate()).slice(-2);
        this.actionService.doAction({
            name: "SLA Pending",
            type: 'ir.actions.act_window',
            res_model: 'axis.helpdesk.ticket',
            view_mode: 'calendar,tree,form',
            view_type: 'list',
            views: [[false, 'list'],[false, 'form']],

            domain: [['helpdesk_stage_id.name', '!=', 'Done'],['helpdesk_sla_deadline','>=',formattedDate]],
            target: 'current'
        });
    }

        action_sla_missed()
    {
     let today = new Date();

        let yesterday = new Date(today);
        var formattedDate = today.getFullYear() + '-' + ('0' + (today.getMonth() + 1)).slice(-2) + '-' + ('0' + today.getDate()).slice(-2);
        this.actionService.doAction({
            name: "SLA Missed",
            type: 'ir.actions.act_window',
            res_model: 'axis.helpdesk.ticket',
            view_mode: 'calendar,tree,form',
            view_type: 'list',
            views: [[false, 'list'],[false, 'form']],

            domain: [['helpdesk_stage_id.name', '=', 'Done'],['helpdesk_sla_deadline','<=',formattedDate]],
            target: 'current'
        });
    }
    action_pending_appointment()
    {
         this.actionService.doAction({
            name: "Meetings",
            type: 'ir.actions.act_window',
            res_model: 'calendar.event',
            view_mode: 'calendar,tree,form',
            view_type: 'list',
            views: [[false, 'list'],[false, 'calendar'],[false, 'form']],
            context: {
                        'search_default_pending_appointment':true,
                    },
            domain: [['attendee_ids.state','in',['needsAction']]],
            target: 'current'
        });
    }
    action_view_calendar_event_calendar()
    {
        this.actionService.doAction({
            name: "Meetings",
            type: 'ir.actions.act_window',
            res_model: 'calendar.event',
            view_mode: 'calendar,tree,form',
            view_type: 'list',
            views: [[false, 'list'],[false, 'calendar'],[false, 'form']],
            target: 'current'
        });
    }
    action_appointment_group() {
        this.actionService.doAction({
            name: "Appointment Group",
            type: 'ir.actions.act_window',
            res_model: 'appointment.group',
            view_mode: 'tree,form',
            view_type: 'list',
            views: [
                [false, 'list'],
                [false, 'form']
            ],
            views: [
                [false, 'list'],
                [false, 'form']
            ],
            target: 'current'
        });
    }
//    async get_customer_count()
//    {
//         var self = this;
//        var result = await this.orm.call("sale.order", "get_sale_table", [])
//
//                if(result){
//                    var res = result.count_customer
//                    var dataSet = []
//                    for(var i=0;i<res.length;i++){
//                        dataSet.push([res[i].customer_name,'<span class="label label-success">' + '</span>'])
//                    }
//                    if(dataSet.length > 0){
//                        $('.customer').DataTable( {
//                            lengthChange : false,
//                            info: false,
//                            "destroy": true,
//                            "responsive": false,
//                            pagingType: 'simple',
//                            "pageLength": 10,
//                            language: {
//                                paginate: {
//                                    next: '<button type="button" class="btn btn-box-tool"><i class="fa fa-angle-right" /></button>',
//                                    previous: '<button type="button" class="btn btn-box-tool"><i class="fa fa-angle-left" /></button>'
//                                }
//                            },
//                            searching: false,
//                            data: dataSet,
//                            columns: [
//                                { title: "Customer Name" },
//
//                            ]
//                        });
//                    }
//                }
////            });
//    }
     async get_sale_order_cancel()
    {
         var self = this;
        var result = await this.orm.call("sale.order", "get_sale_table", [])

                if(result){
                    var res = result.sale_cancel
                    var dataSet = []
                    for(var i=0;i<res.length;i++){
                        dataSet.push([res[i].customer_name,'<span class="label label-success">' + '</span>'])
                    }
                    if(dataSet.length > 0){
                        $('.sale-cancel').DataTable( {
                            lengthChange : false,
                            info: false,
                            "destroy": true,
                            "responsive": false,
                            pagingType: 'simple',
                            "pageLength": 10,
                            language: {
                                paginate: {
                                    next: '<button type="button" class="btn btn-box-tool"><i class="fa fa-angle-right" /></button>',
                                    previous: '<button type="button" class="btn btn-box-tool"><i class="fa fa-angle-left" /></button>'
                                }
                            },
                            searching: false,
                            data: dataSet,
                            columns: [
                                { title: "Customer Name" },

                            ]
                        });
                    }
                }
//            });
    }
    async datadisplay() {
        var result = await this.orm.call("axis.helpdesk.ticket", "get_helpdesk_ticket_all", [])
        $('.total-ticket').text(result.total_ticket)
        $('.last-week-ticket').text(result.last_week_ticket)
        $('.last-month-ticket').text(result.last_month_ticket)
        $('.today-ticket').text(result.today_ticket)

        var result1 = await this.orm.call("axis.helpdesk.ticket.team", "filter_stage_data_dashboard", [])
        this.values = result1
        $('.my_all_tickets').text(result1.my_all_tickets.count)
        $('.my_all').text(result1.my_all.count)
        $('.my_closed_tickets').text(result1.my_closed_tickets.count)
        $('.today').text(result1.today.count)

        $('.year').text(result1.year.count)
        $('.month').text(result1.month.count)
        $('.7days').text(result1.sevendays.count)
        $('.yesterday').text(result1.yesterday.count)
        $('.today_due').text(result1.today.count)


        $('.my_urgent').text(result1.my_urgent.count)
        $('.my_high').text(result1.my_high.count)
        $('.my_medium').text(result1.my_medium.count)
        $('.my_low').text(result1.my_low.count)

        $('.len_sla_complete').text(result1.len_sla_complete.count)
        $('.len_sla_pending').text(result1.len_sla_pending.count)
        $('.len_sla_missed').text(result1.len_sla_missed.count)
    }
    async render_dashboards() {
     var self = this;
     var result = await this.orm.call("axis.helpdesk.ticket", "get_helpdesk_ticket_all", [])
     this.vals = result
    this.values = result
        var appointment_dashboard = renderToElement('HelpdeskDashboardView', {});
        return appointment_dashboard

    }
    async render_graphsmonthly_car() {
        var self = this;
        var ctx = $('#MonthlyTickets')
        if (Chart.plugins)
        {
            Chart.plugins.register({
            beforeDraw: function(chartInstance) {
                var ctx = chartInstance.chart.ctx;
                ctx.fillStyle = "white";
                ctx.fillRect(0, 0, chartInstance.chart.width, chartInstance.chart.height);
            }
        });
        }
        var bg_color_list = []
        for (var i = 0; i <= 12; i++) {
            bg_color_list.push(self.getRandomColor())
        }
        //        rpc.query({
        //                model: 'car.repair.form',
        //                method: 'get_car_repair_statistics_data',
        //            })
        var result = await this.orm.call("axis.helpdesk.ticket", "get_helpdesk_ticket_month_wise", [])
        if (result) {
            var data = result.data
            var months = ['January', 'February', 'March', 'April', 'May', 'June', 'July',
                'August', 'September', 'October', 'November', 'December'
            ]
            var month_data = [];

            if (data) {
                for (var i = 0; i < months.length; i++) {
                    months[i] == data[months[i]]
                    var day_data = months[i];
                    var month_count = data[months[i]];
                    if (!month_count) {
                        month_count = 0;
                    }
                    month_data[i] = month_count

                }
            }
            var myChart = new Chart(ctx, {
                type: 'bar',
                data: {

                    labels: months,
                    datasets: [{
                        label: 'Tickets',
                        data: month_data,
                        backgroundColor: bg_color_list,
                        borderColor: bg_color_list,
                        borderWidth: 1,
                        pointBorderColor: 'white',
                        pointBackgroundColor: 'red',
                        pointRadius: 1,
                        pointHoverRadius: 10,
                        pointHitRadius: 30,
                        pointBorderWidth: 1,
                        pointStyle: 'rectRounded'
                    }]
                },
                options: {
                    scales: {
                        yAxes: [{
                            ticks: {
                                min: 0,
                                max: Math.max.apply(null, month_data),
                            }
                        }]
                    },
                    responsive: true,
                    maintainAspectRatio: true,
                    leged: {
                        display: true,
                        labels: {
                            fontColor: 'black'
                        }
                    },
                },
            });

        };

    }
    async render_graphs() {
        var self = this;
        var ctx = $('#WeeklyTickets')
        if (Chart.plugins)
        {
            Chart.plugins.register({
            beforeDraw: function(chartInstance) {
                var ctx = chartInstance.chart.ctx;
                ctx.fillStyle = "white";
                ctx.fillRect(0, 0, chartInstance.chart.width, chartInstance.chart.height);
            }
        });
        }
        var bg_color_list = []
        for (var i = 0; i <= 12; i++) {
            bg_color_list.push(self.getRandomColor())
        }
        var result = await this.orm.call("axis.helpdesk.ticket", "get_helpdesk_ticket_week_wise", [])
        if (result) {
            var data = result.data;
            var day = ["Monday", "Tuesday", "Wednesday", "Thursday",
                "Friday", "Saturday", "Sunday"
            ]
            var week_data = [];
            if (data) {
                for (var i = 0; i < day.length; i++) {
                    day[i] == data[day[i]]
                    var day_data = day[i];
                    var day_count = data[day[i]];
                    if (!day_count) {
                        day_count = 0;
                    }
                    week_data[i] = day_count

                }
            }

            var myChart = new Chart(ctx, {
                type: 'bar',
                data: {

                    labels: day,
                    datasets: [{
                        label: 'Tickets',
                        data: week_data,
                        backgroundColor: bg_color_list,
                        borderColor: bg_color_list,
                        borderWidth: 1,
                        pointBorderColor: 'white',
                        pointBackgroundColor: 'red',
                        pointRadius: 5,
                        pointHoverRadius: 10,
                        pointHitRadius: 30,
                        pointBorderWidth: 2,
                        pointStyle: 'rectRounded'
                    }]
                },
                options: {
                    scales: {
                        yAxes: [{
                            ticks: {
                                min: 0,
                                max: Math.max.apply(null, week_data),
                            }
                        }]
                    },
                    responsive: true,
                    maintainAspectRatio: true,
                    leged: {
                        display: true,
                        labels: {
                            fontColor: 'black'
                        }
                    },
                },
            });
        };
    }

}

HelpdeskTicketDashboard.template = "HelpdeskDashboardView";

registry.category("actions").add("helpdesk_ticket_dashboard", HelpdeskTicketDashboard);
