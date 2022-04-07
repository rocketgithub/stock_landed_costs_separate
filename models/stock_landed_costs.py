# -*- coding: utf-8 -*-

from odoo import api, fields, models, tools, _
from collections import defaultdict
import logging

class StockLandedCost(models.Model):
    _inherit = 'stock.landed.cost'
    
    individual_cost_line_ids = fields.One2many('stock.landed.cost.individual', 'cost_id', 'Gastos individuales', copy=True, states={'done': [('readonly', True)]})
    allowed_product_ids = fields.Many2many('product.product', compute='_compute_allowed_product_ids')
    total_ajustes = fields.Monetary('Total de ajustes', compute='_compute_total_ajustes', store=True, tracking=True)
    
    @api.depends('picking_ids')
    def _compute_allowed_product_ids(self):
        for cost in self:
            product_ids = []
            for l in cost.picking_ids.move_lines:
                product_ids.append(l.product_id.id)
            cost.allowed_product_ids = product_ids
            
    @api.depends('valuation_adjustment_lines.additional_landed_cost')
    def _compute_total_ajustes(self):
        for cost in self:
            cost.total_ajustes = sum(line.additional_landed_cost for line in cost.valuation_adjustment_lines)
            
    def compute_landed_cost(self):
        super().compute_landed_cost()
        AdjustementLines = self.env['stock.valuation.adjustment.lines']

        towrite_dict = {}
        for cost in self.filtered(lambda cost: cost._get_targeted_move_ids()):
            rounding = cost.currency_id.rounding
            total_cost_by_product = {}
            all_val_line_values = cost.get_valuation_lines()
            for val_line_values in all_val_line_values:
                if val_line_values['product_id'] not in total_cost_by_product:
                    total_cost_by_product[val_line_values['product_id']] = 0
                
                former_cost = val_line_values.get('former_cost', 0.0)
                # round this because former_cost on the valuation lines is also rounded
                total_cost_by_product[val_line_values['product_id']] += cost.currency_id.round(former_cost)

            for line in cost.individual_cost_line_ids:
                value_split = 0.0
                for valuation in cost.valuation_adjustment_lines:
                    value = 0.0
                    if valuation.product_id and valuation.product_id.id in [p.id for p in line.product_ids]:
                        total_cost = sum([total_cost_by_product[p.id] for p in line.product_ids])
                        per_unit = (line.price_unit / total_cost)
                        value = valuation.former_cost * per_unit

                        if rounding:
                            value = tools.float_round(value, precision_rounding=rounding, rounding_method='UP')
                            fnc = min if line.price_unit > 0 else max
                            value = fnc(value, line.price_unit - value_split)
                            value_split += value

                        if valuation.id not in towrite_dict:
                            towrite_dict[valuation.id] = { 'value': value, 'individual_cost_line_id': line.id }
                        else:
                            towrite_dict[valuation.id]['value'] += value
        for key, value in towrite_dict.items():
            al = AdjustementLines.browse(key)
            al.write({
                'additional_landed_cost': al.additional_landed_cost + value['value'],
                'name': al.name + ' + costos individuales',
                'additional_indivitual_landed_cost': value['value'],
            })
            
        return True
        
    def _check_sum(self):
        prec_digits = self.env.company.currency_id.decimal_places
        for landed_cost in self:
            total_amount = sum(landed_cost.valuation_adjustment_lines.mapped('additional_landed_cost'))
            total_amount_individual = sum(landed_cost.individual_cost_line_ids.mapped('price_unit'))
            if not tools.float_is_zero(total_amount - total_amount_individual - landed_cost.amount_total, precision_digits=prec_digits):
                return False

            val_to_cost_lines = defaultdict(lambda: 0.0)
            for val_line in landed_cost.valuation_adjustment_lines:
                logging.warn(val_line.additional_landed_cost)
                logging.warn(val_line.additional_indivitual_landed_cost)
                val_to_cost_lines[val_line.cost_line_id] += val_line.additional_landed_cost - val_line.additional_indivitual_landed_cost
            logging.warning(val_to_cost_lines)
            if any(not tools.float_is_zero(cost_line.price_unit - val_amount, precision_digits=prec_digits)
                  for cost_line, val_amount in val_to_cost_lines.items()):
                return False
        return True

class StockLandedCostindIvidual(models.Model):
    _name = 'stock.landed.cost.individual'
    _description = 'Stock Landed Cost Individual'
    
    name = fields.Char('Descripción')
    cost_id = fields.Many2one('stock.landed.cost', 'Costo extra', required=True, ondelete='cascade')
    product_id = fields.Many2one('product.product', 'Product', required=True)
    price_unit = fields.Monetary('Costo', required=True)
    account_id = fields.Many2one('account.account', 'Cuenta', domain=[('deprecated', '=', False)])
    currency_id = fields.Many2one('res.currency', related='cost_id.currency_id')
    product_ids = fields.Many2many('product.product', string='Productos', copy=False)
    
    @api.onchange('product_id')
    def onchange_product_id(self):
        self.name = self.product_id.name or ''
        self.price_unit = self.product_id.standard_price or 0.0
        accounts_data = self.product_id.product_tmpl_id.get_product_accounts()
        self.account_id = accounts_data['stock_input']
        
class AdjustmentLines(models.Model):
    _inherit = 'stock.valuation.adjustment.lines'

    additional_indivitual_landed_cost = fields.Monetary('Additional Individual Landed Cost')
    unit_final_cost = fields.Monetary('Nuevo Valor Unitario', compute='_compute_unit_final_cost', store=True)
    
    @api.depends('final_cost', 'quantity')
    def _compute_unit_final_cost(self):
        for line in self:
            line.unit_final_cost = line.final_cost / line.quantity if line.quantity != 0 else 0;
