'''
Created on 24 June 2019

@author: Dennis
'''
from odoo import api, fields, models, tools, SUPERUSER_ID, _
from odoo.exceptions import UserError, ValidationError

class ProjectProjectionAccomplishment(models.Model):
    _name = 'project.projection.accomplishment'
    _order = 'date'

    project_id = fields.Many2one('project.project', string="Project")
    date = fields.Date(string="Date")
    projected = fields.Float(string="Projected Percentage")
    actual = fields.Float(string="Actual Percentage")

class Project(models.Model):
    _name = "project.project"
    _inherit = ['mail.activity.mixin', 'project.project']

    def _compute_phase_count(self):
        phase_data = self.env['project.phase'].read_group([('project_id', 'in', self.ids)], ['project_id'], ['project_id'])
        result = dict((data['project_id'][0], data['project_id_count']) for data in phase_data)
        for project in self:
            project.phase_count = result.get(project.id, 0)

    project_type = fields.Selection([('project', 'Project'),
                                     ('porfolio', 'Porfolio')], string="Project Type", default='project')
    phase_ids = fields.One2many('project.phase', 'project_id', string="Project Phases", readonly=True, states={'draft': [('readonly', False)]})
    phase_count = fields.Integer(compute='_compute_phase_count', string="Phases")
    start_date = fields.Date('Start Date')
    end_date = fields.Date('End Date')
    state = fields.Selection([('draft', 'Draft'),
                              ('inprogress', 'In Progress'),
                              ('closed', 'Closed'),
                              ('canceled', 'Canceled'),
                              ('halted', 'Halted')], string="Status", readonly=True, default='draft')
    stock_location_id = fields.Many2one('stock.location', string="Project Inventory Location")
    boq_setting = fields.Selection([('1', 'Project + Phase + Task + BOQ'),
                                    ('2', 'Project + Phase + Task + BOQ')], string="Project Setting", default="1")
    projection_accomplishment_ids = fields.One2many('project.projection.accomplishment', 'project_id', string="Projection Accomplishment Timeline")
    projection_set = fields.Boolean()
    # Budget And Actual Expeditures
    #Todo: Make all this field a "Computed fields" Badget: based on the BOQs; Expense: Based on the actual expense recored in the Analytic Account
    material_budget = fields.Float(string="Material Budget", store=True, compute="_get_budget_summary")
    material_expense = fields.Float(string="Material Expense")
    service_budget= fields.Float(string="Service Budget", store=True, compute="_get_budget_summary")
    service_expense = fields.Float(string="Service Expense")
    labor_budget = fields.Float(string="Labor Budget", store=True, compute="_get_budget_summary")
    labor_expense = fields.Float(string="Labor Expense")
    equipment_budget = fields.Float(string="Equipment Budget", store=True, compute="_get_budget_summary")
    equipment_expense = fields.Float(string="Equipment Expense")
    overhead_budget = fields.Float(string="Overhead Budget", store=True, compute="_get_budget_summary")
    overhead_expense = fields.Float(string="Overhead Expense")
    total_budget = fields.Float(string="Total Budget", store=True, compute="_get_budget_summary")
    total_expense = fields.Float(string="Total Expense")

    #Porfolio
    parent_id = fields.Many2one("project.project", string="Portfolio", domain="[('project_type', 'in', ['porfolio'])]")
    project_count = fields.Integer(string="Projects", compute="_compute_project_count")

    @api.onchange('parent_id', 'name')
    def _onchange_portfolio(self):
        # data = self.search([('project_type', 'in', ['porfolio'])])
        # raise ValidationError(_('Data: %s'%(str(data))))
        for i in self:
            if i.parent_id:
                i.user_id = i.parent_id.user_id.id
                i.partner_id = i.parent_id.partner_id.id

    def _compute_project_count(self):
        for record in self:
            record.project_count = self.env['project.project'].search_count([('project_type','=','project'),('parent_id','=',record.id)])

    @api.model
    def create(self, vals):
        res = super(Project, self).create(vals)
        if not res.project_type in ['portfolio', False]:
            res.analytic_account_id.write({'parent_id':res.parent_id and res.parent_id.analytic_account_id.id or False})
        return res

    @api.multi
    def write(self, vals):
        res = super(Project, self).write(vals)
        self.analytic_account_id.write({'parent_id': self.parent_id and self.parent_id.analytic_account_id.id or False})
        return res


    @api.depends('task_ids', 'task_ids.material_budget', 'task_ids.service_budget', 'task_ids.overhead_budget', 'task_ids.equipment_budget', 'task_ids.labor_budget')
    def _get_budget_summary(self):
        for i in self:
            material = service = labor = equipment = overhead = 0.0
            for task in i.task_ids:
                material += task.material_budget
                service += task.service_budget
                labor += task.labor_budget
                equipment += task.equipment_budget
                overhead += task.overhead_budget
            i.material_budget = material
            i.service_budget = service
            i.labor_budget = labor
            i.equipment_budget = equipment
            i.overhead_budget = overhead
            i.total_budget = sum([material, service, labor, equipment, overhead])


    @api.multi
    def view_phases(self):
        tree_id = self.env.ref('construction_project_management_base.project_phase_view_tree').id
        form_id = self.env.ref('construction_project_management_base.project_phase_view_form').id
        return {'name': 'Phases',
                'type': 'ir.actions.act_window',
                'res_model': 'project.phase',
                'view_mode': 'form',
                'view_type': 'form',
                'views':[(tree_id,'tree'),(form_id,'form')],
                'target': 'main',
                'domain':[('project_id','=',active_id)],
                'context':{'default_project_id': active_id,
                           'default_user_id': self._user_id,
                           }
                }

    @api.multi
    def lock_projection(self):
        for i in self:
            i.write({'projection_set': True})
        return True

    @api.multi
    def set_inprogress(self):
        for i in self:
            if not i.stock_location_id or not i.start_date:
                raise ValidationError(_('You must supply value on the fields:\n 1. Start Date\n 2. Project Inventory Location'))
            i.write({'state': 'inprogress'})
        return True

    @api.multi
    def set_close(self):
        for i in self:
            if not i.end_date:
                raise ValidationError(_('You must supply value on the fields:\n 1. End Date'))
            i.write({'state': 'closed'})
        return True

    @api.multi
    def set_cancel(self):
        for i in self:
            i.write({'state': 'canceled'})
        return True

    @api.multi
    def set_halt(self):
        for i in self:
            i.write({'state': 'halted'})
        return True
