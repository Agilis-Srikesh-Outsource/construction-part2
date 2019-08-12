# -*- coding: utf-8 -*-

from odoo import api, fields, models, _
from odoo.addons import decimal_precision as dp


class ProjectTask(models.Model):
    _inherit = 'project.task'

    qty = fields.Float(string="Quantity")
    material_consumption_progress = fields.Float(string="Material Consumption Progress")
    material_consumption = fields.One2many(
        'project.material.consumption', 'task_id', 'Material Consumption',
        copy=True)
    waste_management = fields.One2many(
        'project.waste.management', 'task_id', 'Waste Management',
        copy=True, readonly=True)
    scrap_products = fields.One2many(
        'project.scrap.products', 'task_id', 'Scrap Products',
        copy=True, readonly=True)
    boq_ref = fields.Many2one('project.boq', 'BOQ Reference')
    phase_id = fields.Many2one('project.phase', string="Project Phase",
                               domain="[('project_id', '=', project_id)]")


class ProjectMaterialConsumption(models.Model):
    _name = 'project.material.consumption'
    _description = "Material Consumption"

    product_id = fields.Many2one('product.product', string="Product")
    estimated_qty = fields.Float(string='Estimated Quantity')
    tot_stock_received = fields.Float(string='Total Stock Received')
    uom = fields.Many2one('product.uom', string="Unit of Measure")
    used_qty = fields.Float(string='Used Quantity', readonly=True)
    available_stock = fields.Float(string='Available Stock', readonly=True)
    consumption_progress = fields.Float(string="Consumption Progress")
    wastage_percent = fields.Float(string="Wastage Percentage")
    scrap_percent = fields.Float(string="Scrap Percentage")
    task_id = fields.Many2one('project.task', 'Task')

    @api.depends('tot_stock_received')
    def _compute_tot_stock(self):
        vals = self.search([('id', '=', self.id)])
        waste_management = self.env['project.waste.management'].search([
            ('task_id', '=', vals.task_id.id), ('product_id', '=', self.product_id.id)])
        scrap_product = self.env['project.scrap.products'].search([
            ('task_id', '=', vals.task_id.id), ('product_id', '=', self.product_id.id)])
        waste_qty = 0
        scrap = 0
        for waste in waste_management:
            waste_qty += waste.qty
        for scraps in scrap_product:
            scrap += scraps.qty
        self.available_stock = self.tot_stock_received - (self.used_qty + waste_qty + scrap)

    @api.multi
    def action_used_qty(self):
        return {
                'name': _('Used Quantity'),
                'type': 'ir.actions.act_window',
                'res_model': 'project.used.quantity',
                'view_type': 'form',
                'view_mode': 'form',
                'view_id': self.env.ref('skit_construction_project_mgmt_base.project_used_quantity_form').ids,
                'target': 'new',
                'context': {
                    'default_product_id': self.product_id.id,
                    'default_quantity': self.used_qty,
                    'default_material_id': self.id,
                    'task_id': self.task_id.id,
                    'received': self.tot_stock_received
                }
            }

    @api.multi
    def action_waste_percent(self):
        return {
                'name': _('Waste Process'),
                'type': 'ir.actions.act_window',
                'res_model': 'wizard.waste.process',
                'view_type': 'form',
                'view_mode': 'form',
                'view_id': self.env.ref('skit_construction_project_mgmt_base.project_waste_process_form').ids,
                'target': 'new',
                'context': {
                    'default_product_id': self.product_id.id,
                    'default_material_id': self.id,
                    'task_id': self.task_id.id,
                    'uom': self.uom.id,
                }
            }

    @api.multi
    def action_scrap_percent(self):
        return {
                'name': _('Scrap Move'),
                'type': 'ir.actions.act_window',
                'res_model': 'wizard.scrap.move',
                'view_type': 'form',
                'view_mode': 'form',
                'view_id': self.env.ref('skit_construction_project_mgmt_base.project_scrap_move_form').ids,
                'target': 'new',
                'context': {
                    'default_product_id': self.product_id.id,
                    'default_material_id': self.id,
                    'default_uom': self.uom.id,
                    'task_id': self.task_id.id,
                }
            }


class ProjectWasteManagement(models.Model):
    _name = 'project.waste.management'
    _description = "Waste Management"

    product_id = fields.Many2one('product.product', string="Product")
    uom = fields.Many2one('product.uom', string="Unit of Measure")
    qty = fields.Float(string='Quantity')
    wastage_percent = fields.Float(string='Wastage Percentage')
    date_recorded = fields.Date(string='Date Recorded')
    task_id = fields.Many2one('project.task', 'Task')


class ProjectScrapProducts(models.Model):
    _name = 'project.scrap.products'
    _description = "Scrap Products"

    product_id = fields.Many2one('product.product', string="Product")
    uom = fields.Many2one('product.uom', string="Unit of Measure")
    qty = fields.Float(string='Quantity')
    scrap_percent = fields.Float(string='Scrap Percentage')
    scrap_reason = fields.Text(string='Scrap Reason')
    date_recorded = fields.Date(string='Date Recorded',
                                default=fields.Date.context_today)
    task_id = fields.Many2one('project.task', 'Task')
