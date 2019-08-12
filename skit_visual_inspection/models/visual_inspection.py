# -*- coding: utf-8 -*-

'''
Created on 6 Aug 2019

@author: Srikesh Infotech
'''
from odoo import api, fields, models


class ProjectVisualInspection(models.Model):
    _name = 'project.visual.inspection'
    _description = "Visual Inspection"

    date = fields.Date(string='Date', required=True)
    description = fields.Text(string='Description', required=True)
    actual_accomplishment = fields.Float(string='Actual Accomplishment',
                                         required=True)
    task_id = fields.Many2one('project.task', 'Task')


class ProjectTask(models.Model):
    _inherit = 'project.task'

    actual_accomplishment = fields.Float(string="Actual Accomplishment",
                                         compute='update_actual_accomplishment')
    visual_inspection = fields.One2many(
        'project.visual.inspection', 'task_id', 'Visual Inspection',
        copy=True)

    @api.depends('visual_inspection.actual_accomplishment')
    def update_actual_accomplishment(self):
        self.actual_accomplishment = 0
        for visual in self.visual_inspection:
            self.actual_accomplishment += visual.actual_accomplishment
