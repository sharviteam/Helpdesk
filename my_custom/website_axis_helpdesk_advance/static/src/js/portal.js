/** @odoo-module **/

import dom from "@web/legacy/js/core/dom";
import publicWidget from "@web/legacy/js/public/public_widget";
import PortalSidebar from "@portal/js/portal_sidebar";
import { _t } from "@web/core/l10n/translation";


publicWidget.registry.TicketPortal = publicWidget.Widget.extend({
    selector: '#custom_helpdesk_id',
    events: {
        'click .apply_filter': 'apply_filter_action',
    },
        init() {
        this._super(...arguments);
        this.rpc = this.bindService("rpc");
        this.orm = this.bindService("orm");
    },
async apply_filter_action() {
    var startDate = $('#startDate').val();
    var endDate = $('#endDate').val();
    debugger;
    if (startDate && endDate) {
//        window.location.href = window.location.origin + '/my/tickets'
        window.location.href = `/my/tickets?date_start=${startDate}&date_end=${endDate}`
//        await this.rpc("/my/tickets", {
//            page:1,
//            date_start:startDate,
//            date_end:endDate,
//            sortby : 'date',
//            groupby : 'none',
//            search:'null'
//        });

//        await this.orm.call("res.users","process_dates",[startDate, endDate])
//        .then(result => {
//            if (result.message) {
//                alert(result.message);
//            } else if (result.error) {
//                alert(result.error);
//            }
//            else
//            {
//            console.log("AAAA")
//            }
//        })
    }
     else {
        alert(_t('Please fill in both the start date and end date.'));
    }
}


})