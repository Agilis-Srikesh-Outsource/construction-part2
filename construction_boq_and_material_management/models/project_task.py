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
    boq_id = fields.Many2one('project.boq', 'BOM/BOQ Reference',
                             readonly=True)
    phase_id = fields.Many2one('project.phase', string="Project Phase",
                               domain="[('project_id', '=', project_id)]")
    stock_location_id = fields.Many2one('stock.location',
                                        string="Task Inventory Location",
                                        domain="[('location_id', '=', project_stock_location_id),('usage', '!=', 'view')]")


class ProjectMaterialConsumption(models.Model):
    _name = 'project.material.consumption'
    _description = "Material Consumption"

    product_id = fields.Many2one('product.product', string="Product")
    estimated_qty = fields.Float(string='Estimated Quantity')
    tot_stock_received = fields.Float(string='Total Stock Received',
                                      compute='_update_tot_stock')
    uom_id = fields.Many2one('product.uom', string="Unit of Measure")
    used_qty = fields.Float(string='Used Quantity', readonly=True)
    available_stock = fields.Float(string='Available Stock',
                                   compute='_compute_tot_stock', readonly=True)
    consumption_progress = fields.Float(string="Consumption Progress")
    wastage_percent = fields.Float(string="Wastage Percentage",
                                   compute='_compute_waste_percent')
    scrap_percent = fields.Float(string="Scrap Percentage",
                                 compute='_compute_scrap_percent')
    task_id = fields.Many2one('project.task', 'Task')

    @api.depends('task_id')
    def _compute_waste_percent(self):
        for material in self:
            waste_mgmt = self.env['project.waste.management'].search([
                ('task_id', '=', material.task_id.id),
                ('product_id', '=', material.product_id.id)])
            qty = 0
            for waste in waste_mgmt:
                qty += waste.qty
                material.update({'wastage_percent': qty})

    @api.depends('task_id')
    def _compute_scrap_percent(self):
        for material in self:
            scrap_product = self.env['project.scrap.products'].search([
                ('task_id', '=', material.task_id.id),
                ('product_id', '=', material.product_id.id)])
            qty = 0
            for scrap in scrap_product:
                qty += scrap.qty
                material.update({'scrap_percent': qty})

    @api.depends('task_id.stock_location_id')
    def _update_tot_stock(self):
        for material in self:
            product = material.product_id.id
            material_request = self.env['material.requisition.bom'].search([
                ('task_id', '=', material.task_id.id)])
            qty = 0
            for mr_val in material_request:
                location_id = mr_val.picking_id.location_dest_id.id
                move = self.env['stock.move'].search([
                    ('picking_id', '=', mr_val.picking_id.id),
                    ('product_id', '=', product)])
                for vals in move:
                    qty += vals.quantity_done
                material.update({'tot_stock_received': qty})

    @api.depends('tot_stock_received')
    def _compute_tot_stock(self):
        for material in self:
            if not isinstance(material.task_id.id, models.NewId):
                vals = material.search([('id', '=', material.id)])
                waste_management = self.env['project.waste.management'].search([
                        ('task_id', '=', vals.task_id.id),
                        ('product_id', '=', material.product_id.id)])
                scrap_product = self.env['project.scrap.products'].search([
                        ('task_id', '=', vals.task_id.id),
                        ('product_id', '=', material.product_id.id)])
                waste_qty = 0
                scrap = 0
                for waste in waste_management:
                    if waste.is_cutted is False:
                        waste_qty += waste.qty
                for scraps in scrap_product:
                    scrap += scraps.qty
                avail_stock = material.tot_stock_received - (material.used_qty + waste_qty + scrap)
                material.update({'available_stock': avail_stock})
            else:
                if material.tot_stock_received:
                    material.update({'available_stock': material.tot_stock_received})

    @api.multi
    def action_used_qty(self):
        return {
                'name': _('Used Quantity'),
                'type': 'ir.actions.act_window',
                'res_model': 'project.used.quantity',
                'view_type': 'form',
                'view_mode': 'form',
                'view_id': self.env.ref('construction_boq_and_material_management.project_used_quantity_form').ids,
                'target': 'new',
                'context': {
                    'default_product_id': self.product_id.id,
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
                'view_id': self.env.ref('construction_boq_and_material_management.project_waste_process_form').ids,
                'target': 'new',
                'context': {
                    'default_product_id': self.product_id.id,
                    'default_material_id': self.id,
                    'default_uom_id': self.uom_id.id,
                    'task_id': self.task_id.id,
                    'uom_id': self.uom_id.id,
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
                'view_id': self.env.ref('construction_boq_and_material_management.project_scrap_move_form').ids,
                'target': 'new',
                'context': {
                    'default_product_id': self.product_id.id,
                    'default_material_id': self.id,
                    'default_uom_id': self.uom_id.id,
                    'task_id': self.task_id.id,
                }
            }


class ProjectWasteManagement(models.Model):
    _name = 'project.waste.management'
    _description = "Waste Management"

    product_id = fields.Many2one('product.product', string="Product")
    uom_id = fields.Many2one('product.uom', string="Unit of Measure")
    qty = fields.Float(string='Quantity')
    wastage_percent = fields.Float(string='Wastage Percentage')
    date_recorded = fields.Date(string='Date Recorded')
    task_id = fields.Many2one('project.task', 'Task')
    is_cutted = fields.Boolean(string="Is Cutted", default=False)


class ProjectScrapProducts(models.Model):
    _name = 'project.scrap.products'
    _description = "Scrap Products"

    product_id = fields.Many2one('product.product', string="Product")
    uom_id = fields.Many2one('product.uom', string="Unit of Measure")
    qty = fields.Float(string='Quantity')
    scrap_percent = fields.Float(string='Scrap Percentage')
    scrap_reason = fields.Text(string='Scrap Reason')
    date_recorded = fields.Date(string='Date Recorded',
                                default=fields.Date.context_today)
    task_id = fields.Many2one('project.task', 'Task')
