/** @odoo-module **/

import { session } from '@web/session';
import { formatFloatTime } from '@web/views/fields/formatters';
import { formatFloat } from "@web/core/utils/numbers";
import { useService } from "@web/core/utils/hooks";
import { Component, useState, onWillStart } from "@odoo/owl";
import { KanbanRenderer } from "@web/views/kanban/kanban_renderer";
import { jsonrpc } from "@web/core/network/rpc_service";
import {
    renderToElement
} from "@web/core/utils/render";


export class TemplateDashboard extends Component {
    setup() {
//        this.action = useService('action');
        this.actionService = useService("action");
        this.orm = useService('orm');
        this.state = useState({
            dashboardValues: null,
        });
        this.url=[]
        this.value = "aaaaa"

        onWillStart(this.onWillStart);
    }

        async onWillStart() {
        const { errorData } = this.props;
        this.url.push(1)
        this.url.push(2)
        this.url.push(3)
        this.url.push(4)

          this.values = await this.orm.call("axis.helpdesk.ticket.team", "filter_stage_data_dashboard", [], {});

    }
    onDashboardActionClicked()
    {
         this.actionService.doAction({
            name: "Meetings",
            type: 'ir.actions.act_window',
            res_model: 'axis.helpdesk.ticket',
            view_mode: 'tree,kanban',
            view_type: 'list',
            views: [[false, 'list'],[false, 'kanban'],[false, 'form']],

            domain: [['helpdesk_stage_id.is_close','=',false]],
            target: 'current'
            })

    }

     onDashboardActionClickedInprogress()
    {
         this.actionService.doAction({
            name: "Meetings",
            type: 'ir.actions.act_window',
            res_model: 'axis.helpdesk.ticket',
            view_mode: 'tree,kanban',
            view_type: 'list',
            views: [[false, 'list'],[false, 'kanban'],[false, 'form']],

            domain: [['helpdesk_stage_id.name','=','In Progress']],
            target: 'current'
            })

    }

    onDashboardActionClickedSolved()
    {
         this.actionService.doAction({
            name: "Meetings",
            type: 'ir.actions.act_window',
            res_model: 'axis.helpdesk.ticket',
            view_mode: 'tree,kanban',
            view_type: 'list',
            views: [[false, 'list'],[false, 'kanban'],[false, 'form']],

            domain: [['helpdesk_stage_id.name','=','Solved']],
            target: 'current'
            })

    }
    onDashboardActionClickedClosed()
    {
         this.actionService.doAction({
            name: "Meetings",
            type: 'ir.actions.act_window',
            res_model: 'axis.helpdesk.ticket',
            view_mode: 'tree,kanban',
            view_type: 'list',
            views: [[false, 'list'],[false, 'kanban'],[false, 'form']],

            domain: [['helpdesk_stage_id.is_close','=',true]],
            target: 'current'
            })

    }
    onChangeTeamLead(el)
    {
//           var car_repair_dashboard = renderToElement('website_axis_helpdesk.TemplateDashboard', {});
            debugger;
//            var teamLead_id = document.getElementById('o_team_lead').find(':selected').val();
            var team_id = $(document.getElementById('o_team')).find(':selected').val();
            var assignUser_id = $(document.getElementById('o_assign')).find(':selected').val();
            var date_id = $(document.getElementById('date_filter')).find(':selected').val();

            if (date_id == 9) {
                $('.datepicker').css("display","flex");
            }
            else {
                $('.datepicker').css("display","none");
//                this._render()
            }

//            var custome_date_id = $('.custom_selection').val();

            jsonrpc('/getData', {
//                'teamLead_id': teamLead_id,
                'team_id':team_id,
                'assignUser_id': assignUser_id,
                'date_id' : date_id,
//                'custome_date_id': custome_date_id

            }).then(function(data) {
            console.log("RESULTTTTTTTTTTTTTTTTTTTTTTTTTT",data)
                var result = data;
                var count_val = 1
                $(document.getElementById("tbody_new")).empty();
                 for (const [key, value] of Object.entries(result)) {
                    var len = result['ticket_ids'].length
                    for(var i=0; i<len; i++) {
                    var count_stage = 0
                    var stage = result['ticket_ids'][i]['helpdesk_stage_id']
                    if (not_update_stage != stage){
                        var stage = "<tr><td colspan='6' style='background-color:#27c2b4; font-weight-bold;border: 1px solid #27c2b4'>"+result['ticket_ids'][i]['helpdesk_stage_id']+"</td><'tr>"
                        $(document.getElementById("tbody_new")).append(stage)
                        var html_header = "<tr style='background-color:#deeaff; font-weight-bold;border: 1px solid #27c2b4;border-right: 1px solid #dbd3d3;'><td><b>Ticket No</b></td><td><b>Customer Name</b></td><td><b>Create Date</b></td><td><b>Last Update Date</b></td><td><b>Assign User</b></td><td><b>Stage</b></td></tr>"
                       $(document.getElementById("tbody_new")).append(html_header);
                    }
                    var not_update_stage = result['ticket_ids'][i]['helpdesk_stage_id']
                    var html = "<tr style='border-right: 1px solid #dbd3d3;'><td style='border-right: 1px solid #dbd3d3;'>"+result['ticket_ids'][i]['number']+"</td><td style='border-right: 1px solid #dbd3d3;'>"+result['ticket_ids'][i]['partner_id']+"</td><td style='border-right: 1px solid #dbd3d3;'>"+result['ticket_ids'][i]['create_date']+"</td><td style='border-right: 1px solid #dbd3d3;'>"+result['ticket_ids'][i]['write_date']+"</td><td style='border-right: 1px solid #dbd3d3;'>"+result['ticket_ids'][i]['res_user_id']+"</td><td style='border-right: 1px solid #dbd3d3;'>"+result['ticket_ids'][i]['helpdesk_stage_id']+"</td></tr>"
                    count_stage += 1
                    $(document.getElementById("tbody_new")).append(html);
                    }
                 }
//                var result = data;
//                var teamdata_new = result.teamdata_new
//                var teamdata_inprogress = result.teamdata_inprogress
//                var teamdata_solved = result.teamdata_solved
//                var teamdata_cancelled = result.teamdata_cancelled
//                var teamdata_others = result.teamdata_others
//
//                var new_cnt = result.len_teamdata_new
//                var new_count = document.getElementById('new_count');
//                new_count.innerHTML = new_cnt
//
//                 var inprogrss_cnt = result.len_teamdata_inprogress
//                 var progress_count = document.getElementById('progress_count');
//                progress_count.innerHTML = inprogrss_cnt
//
//
//                 var solve_cnt = result.len_teamdata_solved
//                 var solved_count = document.getElementById('solved_count');
//                solved_count.innerHTML = solve_cnt
//
//                var cancel_cnt = result.len_teamdata_cancelled
//                 var cancel_count = document.getElementById('cancel_count');
//                cancel_count.innerHTML = cancel_cnt
//
//
//                var i;
//                for (const [key, value] of Object.entries(teamdata_new)) {
//                    var data_value = value;
//                    for (const [k, v] of Object.entries(data_value)) {
////                        console.log("k,v for new team data:",k, v);
//                    }
//                }
//                $("#tbody_new").empty();
//                for (const [key, value] of Object.entries(teamdata_new)) {
//                    var data_value = value;
//                    var html = "<tr><td>" + data_value.number + "</td><td>"+data_value.customer+"</td><td>"+data_value.create_date+"</td><td>"+data_value.write_date+"</td><td>"+data_value.assign_user+"</td><td>"+data_value.stage+"</td></tr>";
//                    $("#tbody_new").append(html);
//                }
//                $("#tbody_inProgress").empty();
//                for (const [key, value] of Object.entries(teamdata_inprogress)) {
//                    var data_value = value;
//                    var html = "<tr><td>" + data_value.number + "</td><td>"+data_value.customer+"</td><td>"+data_value.create_date+"</td><td>"+data_value.write_date+"</td><td>"+data_value.assign_user+"</td><td>"+data_value.stage+"</td></tr>";
//                    $("#tbody_inProgress").append(html);
//                }
//                $("#tbody_solved").empty();
//                for (const [key, value] of Object.entries(teamdata_solved)) {
//                    var data_value = value;
//                    var html = "<tr><td>" + data_value.number + "</td><td>"+data_value.customer+"</td><td>"+data_value.create_date+"</td><td>"+data_value.write_date+"</td><td>"+data_value.assign_user+"</td><td>"+data_value.stage+"</td></tr>";
//                    $("#tbody_solved").append(html);
//                }
//                $("#tbody_cancelled").empty();
//                for (const [key, value] of Object.entries(teamdata_cancelled)) {
//                    var data_value = value;
//                    var html = "<tr><td>" + data_value.number + "</td><td>"+data_value.customer+"</td><td>"+data_value.create_date+"</td><td>"+data_value.write_date+"</td><td>"+data_value.assign_user+"</td><td>"+data_value.stage+"</td></tr>";
//                    $("#tbody_cancelled").append(html);
//                }
//                $("#tbody_others").empty();
//                for (const [key, value] of Object.entries(teamdata_others)) {
//                    var data_value = value;
//                    var html = "<tr><td>" + data_value.number + "</td><td>"+data_value.customer+"</td><td>"+data_value.create_date+"</td><td>"+data_value.write_date+"</td><td>"+data_value.assign_user+"</td><td>"+data_value.stage+"</td></tr>";
//                    $("#tbody_others").append(html);
//                }
            });

    }




}

TemplateDashboard.components = {
    ...KanbanRenderer.components,

};
TemplateDashboard.template = 'website_axis_helpdesk_advance.TemplateDashboard';


