/** @odoo-module */

import { KanbanController } from "@web/views/kanban/kanban_controller";
import { kanbanView } from "@web/views/kanban/kanban_view";
import { registry } from "@web/core/registry";
import { TemplateDashboard } from '@website_axis_helpdesk_advance/js/helpdesk_ticket_filter_stage_component';

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
    useService
} from "@web/core/utils/hooks";

// the controller usually contains the Layout and the renderer.
class CustomKanbanController extends KanbanController {
        static template = "CustomKanbanView";
    setup() {
        super.setup();
        this.orm = useService("orm");
        this.actionService = useService("action");
        var self = this;
    }
        }
CustomKanbanController.template = "website_axis_helpdesk_advance.CustomKanbanView";
export const customKanbanView = {
    ...kanbanView, // contains the default Renderer/Controller/Model
    Controller: CustomKanbanController,
    Renderer:TemplateDashboard,

};
// Register it to the views registry
registry.category("views").add("helpdesk_ticket_filter", customKanbanView);
