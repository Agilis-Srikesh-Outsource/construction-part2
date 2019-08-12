# -*- coding: utf-8 -*-

from odoo import fields, models,api,_
from datetime import datetime



class SkitMaterialReq(models.Model):
    _name = 'material.requisition.bom'
    
    name = fields.Char(string='Reference Number', index=True, readonly=True, copy=False, default=lambda self: _('New'))
    project_id = fields.Many2one('project.project', required=True, string="Project")
    phase_id = fields.Many2one('project.phase',required=True, string="Phase",domain="[('project_id', '=', project_id)]")
    task_id = fields.Many2one('project.task',required=True, string="Task",domain="[('project_id', '=', project_id),('phase_id', '=', phase_id)]")
    required_date = fields.Date("Required Date",required=True)
    date = fields.Datetime("Date", required=True, index=True, copy=False, default=fields.Date.context_today)
    state = fields.Selection([('draft', 'Draft'),
                              ('confirmed', 'Confirmed'),
                              ('verified', 'Verified'),
                              ('approved', 'Approved'),
                              ('cancelled', 'Cancelled')], string='Status', readonly=True, copy=False, 
                             index=True, track_visibility='onchange', default='draft')
    operation_id =fields.Many2one('stock.picking.type',"Stock Picking Operation",readonly=True)
    company_id = fields.Many2one('res.company', required = True,
                                  default=lambda self: self.env['res.company']._company_default_get('material.requisition.bom'))
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
    company_count = fields.Integer("Company Count", compute="_get_company_count") 
    mr_material_ids = fields.One2many('mr.bom.material','mr_id',"Material")
    
    @api.depends('date')   
    def _get_company_count(self):
        user = self.env['res.users'].browse(self.env.uid)
        company_count = len(user.company_ids)
        self.company_count = company_count
 
    @api.multi
    def mr_action_submit(self):
        self.state = 'confirmed'
        user = self.env['res.users'].browse(self.env.uid)
        self.submitted_by = user.name
        self.submitted_date = datetime.today()
        self.confirmed_by = user.name
        self.confirmed_date = datetime.today()
        if self.name == 'New':
            val = self.env['ir.sequence'].next_by_code('material.requisition.bom')
            self.write({'name': val})

    @api.multi
    def mr_action_verify(self):
        user = self.env['res.users'].browse(self.env.uid)
        self.verified_by = user.name
        self.verified_date = datetime.today()
        return self.write({'state': 'verified'})

    @api.multi
    def mr_action_approve(self):
        user = self.env['res.users'].browse(self.env.uid)
        task_id =self.task_id
        mr_ids = self.env['material.requisition.bom'].search([('project_id','=',self.project_id.id),('phase_id','=',self.phase_id.id),
                                                              ('task_id','=',self.task_id.id),('state','=','approved')])
        material_ids = self.env['mr.bom.material'].search([('mr_id','in',mr_ids.ids)])
        delivery_qty = 0
        for consumption in task_id.material_consumption:
            for material in material_ids:
                if consumption.product_id.id == material.product_id.id:
                    mr_bom_material = self.env['mr.bom.material'].search([('material_consumption_id','=',consumption.id),('mr_id','=',self.id),
                                                                         ('product_id','=',consumption.product_id.id)])
                    delivery_qty = delivery_qty + material.mr_qty
            total_qty =  consumption.tot_stock_received+ delivery_qty+mr_bom_material.mr_qty   
            if total_qty > consumption.estimated_qty:
                mr_bom_material.update({'exceeded_qty':True})
            delivery_qty = 0   
        self.approved_by = user.name
        self.approved_date = datetime.today()
        self.write({'state': 'approved'})

    @api.multi
    def mr_action_cancel(self):
        user = self.env['res.users'].browse(self.env.uid)
        self.cancelled_by = user.name
        self.cancelled_date = datetime.today()
        return self.write({'state': 'cancelled'})

    @api.multi
    def mr_action_draft(self):
        orders = self.filtered(lambda s: s.state in ['cancelled'])
        return orders.write({
            'state': 'draft',
        })
        
    @api.multi
    def mr_load_task_bom(self):
        task_id =self.task_id
        mr_material = self.env['mr.bom.material']
        mr_ids = self.env['material.requisition.bom'].search([('project_id','=',self.project_id.id),('phase_id','=',self.phase_id.id),
                                                              ('task_id','=',self.task_id.id),('state','=','approved')])
        material_ids = self.env['mr.bom.material'].search([('mr_id','in',mr_ids.ids)])
        delivery_qty = 0
        for consumption in task_id.material_consumption:
            mr_bom_material = self.env['mr.bom.material'].search([('material_consumption_id','=',consumption.id),('mr_id','=',self.id)])
            for material in material_ids:
                if consumption.product_id.id == material.product_id.id:
                    delivery_qty = delivery_qty + material.mr_qty
                
            if not mr_bom_material:
                val = mr_material.create({'product_id':consumption.product_id.id,
                                'mr_qty':(consumption.estimated_qty-(consumption.tot_stock_received+delivery_qty)),
                                'uom_id':consumption.uom.id,
                                'mr_id':self.id,
                                'material_consumption_id':consumption.id
                                })
            delivery_qty = 0 
              
    @api.onchange('task_id')
    def _onchange_task_operation_type(self):
        task_id = self.task_id.id
        task = self.env['project.task'].browse(task_id)
        if task.picking_type_id:
            self.operation_id = task.picking_type_id.id
    
    @api.model
    def create(self, vals):
        if 'task_id' in vals:
            task_id = vals['task_id']
            task = self.env['project.task'].search([('id', '=', task_id)])
            if task.picking_type_id:
                vals['operation_id'] = task.picking_type_id.id
        result = super(SkitMaterialReq, self).create(vals)
        return result

    @api.multi
    def write(self, values):
        if 'task_id' in values:
            task_id = values['task_id']
            task = self.env['project.task'].search([('id', '=', task_id)])
            if task.picking_type_id:
                values['operation_id'] = task.picking_type_id.id
        result = super(SkitMaterialReq, self).write(values)
        return result
        
class SkitMRMaterial(models.Model):
    _name='mr.bom.material'
    
    mr_id = fields.Many2one('material.requisition.bom',"Material Requisition")
    product_id = fields.Many2one('product.product','Product')
    mr_qty = fields.Float("Quantity")
    uom_id = fields.Many2one('product.uom',"Unit of Measure")
    exceeded_qty = fields.Boolean("Exceeded the Required Quantity",default=False)
    not_task_bom = fields.Boolean("Not a Task's BOM",default=False)
    material_consumption_id = fields.Many2one('project.material.consumption','Material Consumption')
    
    @api.onchange('product_id')
    def product_onchange(self):
        task_id =self.mr_id.task_id
        if self.product_id:
            product_id = self.env['project.material.consumption'].search([('product_id','=',self.product_id.id),('task_id','=',task_id.id)])
            if not product_id:
                self.not_task_bom = True
                
    @api.onchange('mr_qty')
    def qty_onchange(self):
        project_id = self.mr_id.project_id
        phase_id = self.mr_id.phase_id
        task_id = self.mr_id.task_id
        product_id =self.product_id
        consumption_id = self._origin.material_consumption_id
        estimate_qty = consumption_id.estimated_qty
        received_qty =consumption_id.tot_stock_received
        qty =0
        if estimate_qty>0:
            mr_ids = self.env['material.requisition.bom'].search([('project_id','=',project_id.id),('phase_id','=',phase_id.id),
                                                                  ('task_id','=',task_id.id),('state','=','approved')])
            material_ids = self.env['mr.bom.material'].search([('mr_id','in',mr_ids.ids),('product_id','=',product_id.id)])
            for material in material_ids:
                qty = qty + material.mr_qty
            tot_stock_qty = received_qty+qty+self.mr_qty
            if tot_stock_qty > estimate_qty:
                self.exceeded_qty = True    
    
#Material Requisition(Non-BOM)    
class SkitMaterialReqNonBOM(models.Model):
    _name = 'material.requisition.nonbom'
    
    name = fields.Char(string='Reference Number', index=True, readonly=True, copy=False, default=lambda self: _('New'))
    required_date = fields.Date("Required Date",required=True)
    date = fields.Datetime("Date", required=True, index=True, copy=False, default=fields.Date.context_today)
    state = fields.Selection([('draft', 'Draft'),
                              ('confirmed', 'Confirmed'),
                              ('verified', 'Verified'),
                              ('approved', 'Approved'),
                              ('cancelled', 'Cancelled')], string='Status', readonly=True, copy=False, 
                             index=True, track_visibility='onchange', default='draft')
    operation_id =fields.Many2one('stock.picking.type',"Stock Picking Operation")
    company_id = fields.Many2one('res.company',required = True)
    analytic_account_id =fields.Many2one('account.analytic.account','Analytic Account')
    notes = fields.Text("Notes")
    mr_material_nonbom_ids = fields.One2many('mr.nonbom.material','mr_nonbom_id',"Material")
    
    @api.multi
    def mr_nonbom_action_submit(self):
        self.state = 'confirmed'
        if self.name == 'New':
            val = self.env['ir.sequence'].next_by_code('material.requisition.nonbom')
            self.write({'name': val})

    @api.multi
    def mr_nonbom_action_verify(self):
        return self.write({'state': 'verified'})

    @api.multi
    def mr_nonbom_action_approve(self):
        self.write({'state': 'approved'})

    @api.multi
    def mr_nonbom_action_cancel(self):
        return self.write({'state': 'cancelled'})

    @api.multi
    def mr_nonbom_action_draft(self):
        orders = self.filtered(lambda s: s.state in ['cancelled'])
        return orders.write({
            'state': 'draft',
        }) 

class SkitMRNonBOMMaterial(models.Model):
    _name='mr.nonbom.material'
        
    mr_nonbom_id = fields.Many2one('material.requisition.nonbom',"Material Requisition Non-BOM")
    product_id = fields.Many2one('product.product','Product')
    mr_qty = fields.Float("Quantity")
    uom_id = fields.Many2one('product.uom',"Unit of Measure")
    exceeded_qty = fields.Boolean("Exceeded the Required Quantity",default=False)
    not_task_bom = fields.Boolean("Not a Task's BOM",default=False)
    
class SkitStockPicking(models.Model):
    _inherit = 'stock.picking'
    
    mr_bom_id = fields.Many2one('material.requisition.bom',"BOM")
