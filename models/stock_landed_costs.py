# -*- coding: utf-8 -*-

from odoo import models, fields, api

class StockLandedCost(models.Model):
    _inherit = 'stock.landed.cost'
    
    stock_move_ids = fields.Many2many(
        'stock.move', string='Lineas',
        copy=False, states={'done': [('readonly', True)]})
    allowed_stock_move_ids = fields.Many2many('stock.move', compute='_compute_allowed_stock_move_ids')
    
    @api.depends('picking_ids')
    def _compute_allowed_stock_move_ids(self):
        for cost in self:
            moves = []
            for l in cost.picking_ids.move_lines:
                moves.append(l.id)
            cost.allowed_stock_move_ids = moves
        
    @api.onchange('picking_ids')
    def onchange_picking_ids(self):
        for cost in self:
            moves = []
            for l in cost.picking_ids.move_lines:
                moves.append(l.id)
            cost.stock_move_ids = moves
            
    def _get_targeted_move_ids(self):
        return self.stock_move_ids