# -*- coding: utf-8 -*-
# Part of BrowseInfo. See LICENSE file for full copyright and licensing details.

from odoo import api, fields, models, _
from odoo.addons.payment.models.payment_acquirer import ValidationError
from odoo.tools.float_utils import float_compare

class CreditPaymentAcquirer(models.Model):
    _inherit = 'payment.acquirer'

    cod_config = fields.Many2one('cod.config', 'Cash on Delivery Configuraton')
    delivery_fees = fields.Float('Add Delivery Fees')
    
    @api.onchange('cod_config')
    def min_max_amt_calculation(self):
        cod_product_ids = self.env['product.template'].search([])
        for p in cod_product_ids:
            if p not in self.cod_config.excl_product:
                if p.list_price < self.cod_config.min_amt or p.list_price > self.cod_config.max_amt:
                    p.write({'cod_available': False}) 
                else:
                    p.write({'cod_available': True}) 


class CODPaymentTransaction(models.Model):
    _name = 'cod.config'

    name = fields.Char('Name', required=True)
    min_amt = fields.Float('Minimum Order Amount', required=True)
    max_amt = fields.Float('Maximum Order Amount', required=True)
    excl_product = fields.Many2many('product.template', string="COD Unavailable for the Products")
    cod_msg = fields.Char("COD Availability Alert")
    delivery_date = fields.Boolean('Display Expected Delivery Date')
    exp_delivery_interval = fields.Integer('Expected Delivery Interval')
    cod_unavailable_msg = fields.Char('COD Unavailable Message')
    cod_unavailable_msg_payment = fields.Char('COD Unavailable Message Payment')
    cod_poilicy = fields.Text("COD Policy")
    cod_state = fields.Many2many("res.country.state", string="Allow States")
    cod_zip = fields.One2many('res.zip', 'cod_id','Allow Zip')
    
    @api.model
    def create(self, value):
        cod = super(CODPaymentTransaction, self).create(value)
        for products in cod.excl_product:
            products.update({'cod_available': False})
        return cod

    def write(self,value):
        cod = super(CODPaymentTransaction, self).write(value)
        for products in self.excl_product:
            products.update({'cod_available': False})
        return cod

class CODZip(models.Model):
    
    _name = 'res.zip'
    
    zip_code = fields.Char('ZIP')
    cod_id = fields.Many2one('cod.config','COD Configuration')

class CODPaymentCollection(models.Model):
    
    _name = 'cod.payment.collection'
    _rec_name = 'sale_order_id'
    
    sale_order_id = fields.Many2one('sale.order','Sale Order')
    transaction_id = fields.Many2one('payment.transaction', 'Transaction')
    partner_id = fields.Many2one('res.partner','Customer')
    delivery_person_id = fields.Many2one('res.partner','Delivery Company/Person')
    order_amt = fields.Float("Order Amount")
    collection_amt = fields.Float("Collection Amount", required=True)
    company_id = fields.Many2one('res.company','Company')
    state = fields.Selection([('draft','Draft'),('confirm','Confirmed'),('done','Done'),('cancel','Cancel')], default='draft', string='State')
    notes = fields.Text('Notes')
    
    def confirm_collection(self):
        if self.order_amt == self.collection_amt:
            self.update({'state': 'confirm'})
        else:
            raise ValidationError(_('Please Enter Valid Collection Amount.'))


    def done_collection(self):
        self.update({'state': 'done'})
        self.transaction_id.update({
            'state' : 'done'
            })

    def cancel_collection(self):
        self.update({'state': 'cancel'})
        self.transaction_id.update({
            'state' : 'cancel'
            })

    @api.onchange('sale_order_id')
    def cod_collection_data_update(self):
        if self.sale_order_id:
            self.update({
                'transaction_id': self.sale_order_id.get_portal_last_transaction(),
                'partner_id': self.sale_order_id.partner_id,
                'order_amt': self.sale_order_id.amount_total,
                'company_id': self.sale_order_id.partner_id.company_id,
            })

class SaleOrdercollection(models.Model):
    _inherit = 'sale.order'
    
    def action_view_collections(self):
        action = self.env.ref('bi_website_cash_on_delivery.action_cod_collection_tree').read()[0]
        action['domain'] = [('sale_order_id', '=', self.id)]
        return action

    # def action_quotation_send(self):
    #     res = super(SaleOrdercollection, self).action_quotation_send()
    #     print(res,'=================== res')
    #     return res
    
class website(models.Model):
    _inherit = 'website'
    
    def get_cod_conf(self):
        cod_conf_obj = self.env['ir.model.data'].xmlid_to_object('bi_website_cash_on_delivery.payment_acquirer_cod')
        payment_obj = self.env['payment.acquirer'].search([])
        for curr_pay_method in payment_obj:
            if curr_pay_method.cod_config:
                cod_conf_obj = curr_pay_method
        return cod_conf_obj

    def get_all_zip(self):
        count = 0

        curr_pay_method = self.get_cod_conf()
        order = self.sale_get_order()
        user = order.partner_id

        if curr_pay_method.cod_config:
            if (not curr_pay_method.country_ids) or (user.country_id in curr_pay_method.country_ids):
                if curr_pay_method.cod_config.cod_zip or curr_pay_method.cod_config.cod_state:  
                    if curr_pay_method.cod_config.cod_zip:
                        if user.zip in [i.zip_code for i in curr_pay_method.cod_config.cod_zip]:
                            count = 1               
                    if curr_pay_method.cod_config.cod_state:
                        if user.state_id in curr_pay_method.cod_config.cod_state :
                            count = 1
                else:
                    count=1

        if count > 0 :
            return "Yes"
        else :
            return "No"


# vim:expandtab:smartindent:tabstop=4:softtabstop=4:shiftwidth=4:           
