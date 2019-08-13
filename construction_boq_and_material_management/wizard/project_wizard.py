# -*- coding: utf-8 -*-
from odoo import fields, models, api, _


class ProjectUsedQuantity(models.Model):
    _name = 'project.used.quantity'
    _description = "Project Used Quantity"

    product_id = fields.Many2one('product.product', string="Product",
                                 readonly=True)
    quantity = fields.Float(string='Quantity')
    material_id = fields.Many2one('project.material.consumption',
                                  string="Material")

    @api.multi
    def update_used_qty(self):
        task = self.env.context['task_id']
        received_qty = self.env.context['received']
        product = self.product_id.id
        waste_management = self.env['project.waste.management'].search([
            ('task_id', '=', task), ('product_id', '=', product)])
        scrap_product = self.env['project.scrap.products'].search([
            ('task_id', '=', task), ('product_id', '=', product)])
        waste_qty = 0
        scrap = 0
        for waste in waste_management:
            waste_qty += waste.qty
        for scraps in scrap_product:
            scrap += scraps.qty
        available_qty = received_qty - (self.quantity + waste_qty + scrap)
        self.material_id.write({'used_qty': self.quantity,
                                'available_stock': available_qty,
                                'consumption_progress': self.quantity})
        from_loc = self.material_id.task_id.stock_location_id.id
        to_loc = self.material_id.task_id.picking_type_id.default_location_dest_id.id
        stock_picking = self.env['stock.picking'].search([
            ('material_id', '=', self.material_id.id)])
        stock_move = self.env['stock.move'].search([
            ('picking_id', '=', stock_picking.id)])
        if stock_picking:
            stock_picking.update({
                'picking_type_id': self.material_id.task_id.picking_type_id.id,
                'location_id': from_loc,
                'location_dest_id': to_loc,
                                            })
            if stock_move:
                stock_move.update({
                    'product_id': self.material_id.product_id.id,
                    'product_uom_qty': self.quantity,
                    'product_uom': self.material_id.product_id.uom_id.id,
                    'location_id': stock_picking.location_id.id,
                    'location_dest_id': stock_picking.location_dest_id.id,
                })
        else:
            picking = stock_picking.create({
                'picking_type_id': self.material_id.task_id.picking_type_id.id,
                'location_id': from_loc,
                'location_dest_id': to_loc,
                'material_id': self.material_id.id
                                            })
            stock_move.create({
                'name': _('New Move:') + self.material_id.product_id.display_name,
                'product_id': self.material_id.product_id.id,
                'product_uom_qty': self.quantity,
                'product_uom': self.material_id.product_id.uom_id.id,
                'picking_id': picking.id,
                'location_id': picking.location_id.id,
                'location_dest_id': picking.location_dest_id.id,
            })


class ProjectWasteProcess(models.Model):
    _name = 'wizard.waste.process'
    _description = "Waste Process Wizard"

    product_id = fields.Many2one('product.product', string="Product",
                                 readonly=True)
    new_product_id = fields.Many2one('product.product',
                                     string="New Product Name",
                                     required=True)
    material_waste = fields.Many2one('product.product',
                                     string="Material Waste",
                                     required=True)
    quantity = fields.Float(string='Quantity')
    waste_location = fields.Many2one('stock.location',
                                     string="Waste Location",
                                     required=True)
    description = fields.Text(string='Description',
                              required=True)
    material_id = fields.Many2one('project.material.consumption',
                                  string="Material")

    @api.multi
    def update_waste_process(self):
        uom = self.env.context['uom']
        waste_management = self.env['project.waste.management']
        waste_manage = self.env['project.waste.management'].search([
            ('task_id', '=', self.material_id.task_id.id)])
        if waste_manage:
            if self.material_id.product_id.id == self.product_id.id:
                waste_manage.update({'product_id': self.product_id.id,
                                     'qty': self.quantity,
                                     'task_id': self.material_id.task_id.id,
                                     'date_recorded': fields.Date.today(),
                                     'uom': uom
                                     })
            else:
                waste_management.create({'product_id': self.product_id.id,
                                         'qty': self.quantity,
                                        'task_id': self.material_id.task_id.id,
                                         'date_recorded': fields.Date.today(),
                                         'uom': uom})
        else:
            waste_management.create({'product_id': self.product_id.id,
                                     'qty': self.quantity,
                                     'task_id': self.material_id.task_id.id,
                                     'date_recorded': fields.Date.today(),
                                     'uom': uom})
        self.material_id.write({'wastage_percent': self.quantity,
                                })


class ProjectScrapMove(models.Model):
    _name = 'wizard.scrap.move'
    _description = "Scrap Move Wizard"

    product_id = fields.Many2one('product.product', string="Product",
                                 readonly=True)
    quantity = fields.Float(string='Quantity of Scrap Material')
    uom = fields.Many2one('product.uom', string="Unit of Measure",
                          readonly=True)
    scrap_percent = fields.Float(string='Scrap Percentage', readonly=True)
    scrap_location = fields.Many2one('stock.location',
                                     string="Scrap Location",
                                     required=True)
    description = fields.Text(string='Description',
                              required=True)
    material_id = fields.Many2one('project.material.consumption',
                                  string="Material")

    @api.multi
    def update_scrap_move(self):
        scrap_move = self.env['project.scrap.products']
        scraps = self.env['project.scrap.products'].search([
            ('task_id', '=', self.material_id.task_id.id)])
        if scraps:
            if self.material_id.product_id.id == self.product_id.id:
                scraps.update({
                            'product_id': self.product_id.id,
                            'uom': self.uom.id,
                            'qty': self.quantity,
                            'date_recorded': fields.Date.today(),
                            'scrap_reason': self.description,
                            'task_id': self.material_id.task_id.id,
                    })
            else:
                scrap_move.create({'product_id': self.product_id.id,
                                   'uom': self.uom.id,
                                   'qty': self.quantity,
                                   'date_recorded': fields.Date.today(),
                                   'scrap_reason': self.description,
                                   'task_id': self.material_id.task_id.id,
                                   })
        else:
            scrap_move.create({'product_id': self.product_id.id,
                               'uom': self.uom.id,
                               'qty': self.quantity,
                               'date_recorded': fields.Date.today(),
                               'scrap_reason': self.description,
                               'task_id': self.material_id.task_id.id,
                               })
        self.material_id.write({'scrap_percent': self.quantity,
                                })


class SkitStockPicking(models.Model):
    _inherit = 'stock.picking'

    material_id = fields.Many2one('project.material.consumption',
                                  "Material Requisition")
