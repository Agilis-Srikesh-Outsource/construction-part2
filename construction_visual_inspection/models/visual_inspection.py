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

    @api.multi
    def document_attach(self):
        """This method is to upload files in the
        visual inspection

        :rtype dict.

        :return returns the popup form to attach file

        """
        upload = self.env['project.document.attach'].search(
                         [('res_id', '=', self.id)])
        res_id = 0
        if upload:
            for line in upload:
                if line.res_id == self.id:
                    res_id = line.id
        ctx = dict(self._context, res_id=self.id)
        return {
            'type': 'ir.actions.act_window',
            'view_type': 'form',
            'view_mode': 'form',
            'res_model': 'project.document.attach',
            'res_id': res_id,
            'res_name': "Attach File",
            'create': False,
            'target': 'new',
            'context': ctx
        }


class ProjectTask(models.Model):
    _inherit = 'project.task'

    actual_accomplishment = fields.Float(string="Actual Accomplishment",
                                         compute='update_actual_accomplishment')
    visual_inspection = fields.One2many(
        'project.visual.inspection', 'task_id', 'Visual Inspection',
        copy=True)

    @api.depends('visual_inspection.actual_accomplishment')
    def update_actual_accomplishment(self):
        actual_accomplishment = 0
        for ids in self:
            if ids.visual_inspection:
                visual_size = len(ids.visual_inspection) - 1
                for visual in ids.visual_inspection[visual_size]:
                    actual_accomplishment += visual.actual_accomplishment
                    ids.update({'actual_accomplishment': actual_accomplishment})


class DocumentsAttach(models.Model):
    _name = 'project.document.attach'
    _description = "Attach documents for visual inspection"

    attachment_ids = fields.Many2many(
            'ir.attachment',
            string="Attachments",
            help="Attachments are linked to a document "
                 "through model / res_id"
    )
    res_id = fields.Integer('res_id')

    @api.multi
    def upload(self):

        """Save uploaded attachments

          :rtype: dict

          :return returns from saving

        """
        self.res_id = self.env.context['res_id']
        tasks = self.env['project.visual.inspection'].search(
                                 [('id', '=', self.res_id)])
        for line in tasks:
            line.attachment_ids = [(6, 0, self.attachment_ids.ids)]
