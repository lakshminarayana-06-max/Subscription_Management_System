# -*- coding: utf-8 -*-
from odoo import http, _
from odoo.http import request
from odoo.addons.portal.controllers.portal import CustomerPortal
from odoo.exceptions import AccessError, MissingError


class BrightloopCustomerPortal(CustomerPortal):

    def _prepare_home_portal_values(self, counters):
        values = super()._prepare_home_portal_values(counters)
        if 'subscription_count' in counters:
            partner = request.env.user.partner_id
            values['subscription_count'] = request.env['brightloop.subscription'].search_count([
                ('partner_id', '=', partner.id)
            ])
        return values

    @http.route(['/my/subscriptions', '/my/subscriptions/page/<int:page>'], type='http', auth='user', website=True)
    def portal_my_subscriptions(self, page=1, **kw):
        partner = request.env.user.partner_id
        subscription_obj = request.env['brightloop.subscription']
        
        # Security: strictly query current user's partner records
        domain = [('partner_id', '=', partner.id)]
        subscriptions = subscription_obj.search(domain, order='id desc')
        
        values = self._prepare_portal_layout_values()
        values.update({
            'subscriptions': subscriptions,
            'page_name': 'subscriptions',
            'default_url': '/my/subscriptions',
        })
        return request.render("brightloop_subscription.portal_my_subscriptions", values)

    @http.route(['/my/subscriptions/<int:sub_id>'], type='http', auth='user', website=True)
    def portal_my_subscription_detail(self, sub_id=None, **kw):
        partner = request.env.user.partner_id
        subscription = request.env['brightloop.subscription'].browse(sub_id)
        
        # Enforce strict multi-tenant customer isolation
        if not subscription.exists() or subscription.partner_id.id != partner.id:
            raise AccessError(_("Access Denied: You do not have permission to view this subscription record."))

        values = self._prepare_portal_layout_values()
        values.update({
            'subscription': subscription,
            'page_name': 'subscription',
        })
        return request.render("brightloop_subscription.portal_subscription_page", values)

    @http.route(['/my/subscriptions/<int:sub_id>/action'], type='http', auth='user', methods=['POST'], website=True)
    def portal_subscription_action(self, sub_id=None, action=None, **kw):
        partner = request.env.user.partner_id
        subscription = request.env['brightloop.subscription'].browse(sub_id)
        
        if not subscription.exists() or subscription.partner_id.id != partner.id:
            raise AccessError(_("Access Denied."))

        if action == 'pause' and subscription.plan_id.pause_allowed and subscription.state == 'active':
            subscription.action_pause(reason=_("Customer requested pause via portal"))
        elif action == 'resume' and subscription.state == 'paused':
            subscription.action_resume()
        elif action == 'renew' and subscription.plan_id.renewal_allowed:
            subscription.action_renew()
        elif action == 'cancel' and subscription.plan_id.early_closure_allowed:
            subscription.action_cancel(reason=_("Customer requested cancellation via portal"))

        return request.redirect(f'/my/subscriptions/{sub_id}')
