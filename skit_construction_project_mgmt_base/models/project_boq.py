# -*- coding: utf-8 -*-

from odoo import fields, models, api, _
from odoo.exceptions import UserError
from odoo.addons import decimal_precision as dp
from datetime import datetime


class SkitProjectBOQ(models.Model):
    _name = 'project.boq'
    _description = 'Bill Of Quantity'

    name = fields.Char(string='Reference Number', index=True, readonly=True,
                       copy=False, default=lambda self: _('New'))
    project_id = fields.Many2one('project.project', string="Project")
    phase_id = fields.Many2one('project.phase', string="Phase",
                               domain="[('project_id', '=', project_id)]")
    task_id = fields.Many2one('project.task', string="Task",
                              domain="[('project_id', '=', project_id),('phase_id', '=', phase_id)]")
    allocated_budget = fields.Integer(string="Allocated Budget", readonly=True)
    qty = fields.Float(string="Quantity", readonly=True,
                       digits=dp.get_precision('Product Price'))
    uom_id = fields.Many2one('product.uom', string="UOM", readonly=True,
                             help="Unit of Measure")
    state = fields.Selection([('draft', 'Draft'),
                              ('confirmed', 'Confirmed'),
                              ('verified', 'Verified'),
                              ('approved', 'Approved'),
                              ('cancelled', 'Cancelled')], string='Status',
                             readonly=True, copy=False,
                             index=True,
                             track_visibility='onchange', default='draft')

    labor_total = fields.Float(string="Labor", compute='_compute_boq_labor')
    equipment_total = fields.Float(string="Equipment",
                                   compute='_compute_boq_equipment')
    scservice_total = fields.Float(string="Sub-Contractor Services",
                                   compute='_compute_boq_scservice')
    material_total = fields.Float(string="Material",
                                  compute='_compute_boq_material')
    overheadothers_total = fields.Float(string="Overheads and Others",
                                        compute='_compute_boq_overhead')
    total_boq = fields.Float(string="Total BOQ",
                             compute='_compute_tot_boq')
    notes = fields.Text("Notes")
    submitted_by = fields.Char("Submitted By", readonly=True)
    confirmed_by = fields.Char("Confirmed By", readonly=True)
    cancelled_by = fields.Char("Cancelled By", readonly=True)
    verified_by = fields.Char("Verified By", readonly=True)
    approved_by = fields.Char("Approved By", readonly=True)
    submitted_date = fields.Datetime("Submitted Date", readonly=True)
    confirmed_date = fields.Datetime("Confirmed Date", readonly=True)
    cancelled_date = fields.Datetime("Cancelled Date", readonly=True)
    verified_date = fields.Datetime("Verified Date", readonly=True)
    approved_date = fields.Datetime("Approved Date", readonly=True)
    change_order_count = fields.Integer(string='# of Change Order',
                                        readonly=True)
    boq_material_ids = fields.One2many('boq.material', 'boq_id',
                                       string='Materials')
    boq_equipment_ids = fields.One2many('boq.equipment', 'boq_id',
                                        string='Equipment')
    boq_scservice_ids = fields.One2many('boq.scservice', 'boq_id',
                                        string='SubContractor Service')
    boq_labor_ids = fields.One2many('boq.labor', 'boq_id', string="Labor")
    boq_overhead_ids = fields.One2many('boq.overhead', 'boq_id',
                                       string="OverHead")

    @api.depends('boq_material_ids')
    def _compute_boq_material(self):
        material_total = 0
        for material in self.boq_material_ids:
            material_total = material_total+material.subtotal
        self.material_total = material_total

    @api.depends('boq_equipment_ids')
    def _compute_boq_equipment(self):
        equipment_total = 0
        for equipment in self.boq_equipment_ids:
            equipment_total = equipment_total+equipment.subtotal
        self.equipment_total = equipment_total

    @api.depends('boq_scservice_ids')
    def _compute_boq_scservice(self):
        scservice_total = 0
        for service in self.boq_scservice_ids:
            scservice_total = scservice_total + service.subtotal
        self.scservice_total = scservice_total

    @api.depends('boq_labor_ids')
    def _compute_boq_labor(self):
        labor_total = 0
        for labor in self.boq_labor_ids:
            labor_total = labor_total + labor.labor_total
        self.labor_total = labor_total

    @api.depends('boq_overhead_ids')
    def _compute_boq_overhead(self):
        overhead_total = 0
        for overhead in self.boq_overhead_ids:
            overhead_total = overhead_total+overhead.subtotal
        self.overheadothers_total = overhead_total

    @api.depends('total_boq')
    def _compute_tot_boq(self):
        tot_val = (self.labor_total+self.equipment_total+self.scservice_total+self.material_total+self.overheadothers_total)
        self.total_boq = tot_val

    @api.onchange('task_id')
    def onchange_task(self):
        if self.task_id:
            task_id = self.task_id
            self.allocated_budget = task_id.task_budget
            self.qty = task_id.qty
            self.uom_id = task_id.uom_id.id

    @api.model
    def create(self, vals):
        if 'task_id' in vals:
            task_id = vals['task_id']
            task = self.env['project.task'].search([('id', '=', task_id)])
            vals['allocated_budget'] = task.task_budget
            vals['qty'] = task.qty
            vals['uom_id'] = task.uom_id.id
        result = super(SkitProjectBOQ, self).create(vals)
        return result

    @api.multi
    def action_view_change_order(self):
        return True

    @api.multi
    def write(self, values):
        if 'task_id' in values:
            task_id = values['task_id']
            task = self.env['project.task'].search([('id', '=', task_id)])
            values['allocated_budget'] = task.task_budget
            values['qty'] = task.qty
            values['uom_id'] = task.uom_id.id
        result = super(SkitProjectBOQ, self).write(values)
        return result

    @api.multi
    def boq_action_submit(self):
        self.state = 'confirmed'
        user = self.env['res.users'].browse(self.env.uid)
        self.submitted_by = user.name
        self.submitted_date = datetime.today()
        self.confirmed_by = user.name
        self.confirmed_date = datetime.today()
        if self.name == 'New':
            val = self.env['ir.sequence'].next_by_code('project.boq')
            self.write({'name': val})
        if self.task_id:
            task_id = self.task_id.id
            task = self.env['project.task'].search([('id', '=', task_id)])
            if(not task.stock_location_id or not task.picking_type_id):
                raise UserError(_('Select Task Inventory Location and Picking Operation in Material status tab.'))

    @api.multi
    def boq_action_verify(self):
        user = self.env['res.users'].browse(self.env.uid)
        self.verified_by = user.name
        self.verified_date = datetime.today()
        return self.write({'state': 'verified'})

    @api.multi
    def boq_action_approve(self):
        self.write({'state': 'approved'})
        user = self.env['res.users'].browse(self.env.uid)
        self.approved_by = user.name
        self.approved_date = datetime.today()
        for material in self.boq_material_ids:
            self.task_id.material_consumption.create({
                                    'product_id': material.name.id,
                                    'task_id': self.task_id.id,
                                    'uom': material.uom_id.id,
                                    'estimated_qty': material.qty
                                     })

    @api.multi
    def boq_action_cancel(self):
        user = self.env['res.users'].browse(self.env.uid)
        self.cancelled_by = user.name
        self.cancelled_date = datetime.today()
        return self.write({'state': 'cancelled'})

    @api.multi
    def boq_action_draft(self):
        orders = self.filtered(lambda s: s.state in ['cancelled'])
        return orders.write({
            'state': 'draft',
        })


class SkitMaterial(models.Model):
    _name = 'boq.material'

    name = fields.Many2one('product.product', string="Name",
                           domain=[('type', 'in', ('consu', 'product'))])
    qty = fields.Float(string="Quantity",
                       digits=dp.get_precision('Product Price'))
    uom_id = fields.Many2one('product.uom', string="UOM",
                             help="Unit of Measure")
    unit_rate = fields.Float(string="Unit Rate",
                             digits=dp.get_precision('Product Price'))
    labor_cost = fields.Float(string="Labor Cost",
                              digits=dp.get_precision('Product Price'))
    equipment_cost = fields.Float(string="Equipment Cost",
                                  digits=dp.get_precision('Product Price'))
    subtotal = fields.Float(string="Subtotal",
                            compute='_compute_material_subtotal',
                            digits=dp.get_precision('Product Price'))
    boq_id = fields.Many2one('project.boq', string='BOQ',
                             required=True, ondelete='cascade',
                             index=True, copy=False)

    @api.depends('qty', 'unit_rate', 'labor_cost', 'equipment_cost')
    def _compute_material_subtotal(self):
        for material in self:
            subtotal = (material.unit_rate + material.labor_cost + material.equipment_cost) * material.qty
            material.subtotal = subtotal


class SkitEquipment(models.Model):
    _name = 'boq.equipment'

    name = fields.Char(string='Name')
    qty = fields.Float(string="Quantity",
                       digits=dp.get_precision('Product Price'))
    uom_id = fields.Many2one('product.uom', string="UOM",
                             help="Unit of Measure")
    unit_rate = fields.Float(string="Unit Rate",
                             digits=dp.get_precision('Product Price'))
    no_of_hrs = fields.Float(string="No. of Hours",
                             digits=dp.get_precision('Product Price'))
    subtotal = fields.Float(string="Subtotal",
                            compute='_compute_equipment_subtotal',
                            digits=dp.get_precision('Product Price'))
    boq_id = fields.Many2one('project.boq', string='BOQ',
                             required=True, ondelete='cascade',
                             index=True, copy=False)

    @api.depends('qty', 'unit_rate', 'no_of_hrs')
    def _compute_equipment_subtotal(self):
        for eqp in self:
            subtotal = (eqp.no_of_hrs * eqp.unit_rate * eqp.qty)
            eqp.subtotal = subtotal


class SkitSubContractorService(models.Model):
    _name = 'boq.scservice'

    name = fields.Many2one('product.product', string="Name",
                           domain=[('type', '=', ('service'))])
    qty = fields.Float(string="Quantity",
                       digits=dp.get_precision('Product Price'))
    uom_id = fields.Many2one('product.uom', string="UOM",
                             help="Unit of Measure")
    unit_rate = fields.Float(string="Unit Rate",
                             digits=dp.get_precision('Product Price'))
    description = fields.Char(string='Description')
    subtotal = fields.Float(string="Subtotal",
                            compute='_compute_scservice_subtotal',
                            digits=dp.get_precision('Product Price'))
    boq_id = fields.Many2one('project.boq', string='BOQ',
                             required=True, ondelete='cascade',
                             index=True, copy=False)

    @api.depends('qty', 'unit_rate')
    def _compute_scservice_subtotal(self):
        for service in self:
            subtotal = (service.unit_rate * service.qty)
            service.subtotal = subtotal

    @api.onchange('name')
    def _onchange_product(self):
        self.description = self.name.description_pickingout


class SkitLabor(models.Model):
    _name = 'boq.labor'

    name = fields.Many2one('hr.job', string='Name')
    description = fields.Char(string='Description')
    head_count = fields.Integer("Head Count")
    budget_head_count = fields.Integer("Budget/Head Count")
    uom_id = fields.Many2one('product.uom', string="UOM",
                             help="Unit of Measure")
    dur_payment_term = fields.Float("Duration of Payment Terms",
                                    digits=dp.get_precision('Product Price'))
    labor_subtotal = fields.Float(string="Subtotal",
                                  compute='_compute_labor_subtotal',
                                  digits=dp.get_precision('Product Price'))
    labor_total = fields.Float(string="Total", compute='_compute_labor_total',
                               digits=dp.get_precision('Product Price'))
    boq_id = fields.Many2one('project.boq', string='BOQ',
                             ondelete='cascade', index=True, copy=False)

    @api.depends('head_count', 'budget_head_count')
    def _compute_labor_subtotal(self):
        for labor in self:
            subtotal = (labor.head_count*labor.budget_head_count)
            labor.labor_subtotal = subtotal

    @api.depends('labor_subtotal', 'dur_payment_term')
    def _compute_labor_total(self):
        for labor in self:
            total = (labor.labor_subtotal*labor.dur_payment_term)
            labor.labor_total = total

    @api.onchange('name')
    def _onchange_hr_jobs(self):
        self.description = self.name.description


class SkitOverheads(models.Model):
    _name = 'boq.overhead'

    category_id = fields.Many2one('boq.overhead.category', string='Category')
    name = fields.Char(string='Name')
    qty = fields.Float(string="Quantity",
                       digits=dp.get_precision('Product Price'))
    uom_id = fields.Many2one('product.uom', string="UOM",
                             help="Unit of Measure")
    unit_rate = fields.Float(string="Unit Rate",
                             digits=dp.get_precision('Product Price'))
    subtotal = fields.Float(string="Subtotal",
                            compute='_compute_overhead_subtotal',
                            digits=dp.get_precision('Product Price'))
    boq_id = fields.Many2one('project.boq', string='BOQ',
                             ondelete='cascade', index=True, copy=False)

    @api.depends('qty', 'unit_rate')
    def _compute_overhead_subtotal(self):
        for overhead in self:
            subtotal = (overhead.unit_rate * overhead.qty)
            overhead.subtotal = subtotal


class skitoverheadcategory(models.Model):
    _name = 'boq.overhead.category'

    name = fields.Char("Name", required=True)