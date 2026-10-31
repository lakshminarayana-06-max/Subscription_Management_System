# -*- coding: utf-8 -*-
import re
from odoo import models, fields, api, _
from odoo.exceptions import ValidationError, AccessError


class ResUsers(models.Model):
    _inherit = 'res.users'

    brightloop_role = fields.Selection([
        ('admin', 'Admin'),
        ('staff', 'Internal Staff'),
        ('customer', 'Customer'),
    ], string='Brightloop Role', compute='_compute_brightloop_role', store=False)

    @api.depends('groups_id')
    def _compute_brightloop_role(self):
        for user in self:
            if user.has_group('brightloop_subscription.group_brightloop_admin'):
                user.brightloop_role = 'admin'
            elif user.has_group('brightloop_subscription.group_brightloop_staff'):
                user.brightloop_role = 'staff'
            else:
                user.brightloop_role = 'customer'

    @api.constrains('login')
    def _check_unique_email_login(self):
        for user in self:
            if user.login:
                matching = self.search([
                    ('id', '!=', user.id),
                    ('login', '=ilike', user.login.strip()),
                ])
                if matching:
                    raise ValidationError(_("A user account with email '%s' already exists.", user.login))

    @api.model
    def validate_password_complexity(self, password):
        """
        Enforces Brightloop password complexity:
        - Longer than 8 characters
        - At least 1 uppercase letter
        - At least 1 lowercase letter
        - At least 1 special character
        """
        if not password or len(password) <= 8:
            raise ValidationError(_("Password must be strictly longer than 8 characters."))
        if not re.search(r'[A-Z]', password):
            raise ValidationError(_("Password must contain at least one uppercase letter (A-Z)."))
        if not re.search(r'[a-z]', password):
            raise ValidationError(_("Password must contain at least one lowercase letter (a-z)."))
        if not re.search(r'[^A-Za-z0-9]', password):
            raise ValidationError(_("Password must contain at least one special character (e.g., !@#$%^&*)."))
        return True

    def write(self, vals):
        if 'password' in vals and vals['password']:
            self.validate_password_complexity(vals['password'])
            
        # Role creation enforcement: only Admin can assign staff or admin groups
        if 'groups_id' in vals:
            admin_group = self.env.ref('brightloop_subscription.group_brightloop_admin', raise_if_not_found=False)
            staff_group = self.env.ref('brightloop_subscription.group_brightloop_staff', raise_if_not_found=False)
            if admin_group or staff_group:
                current_is_admin = self.env.user.has_group('brightloop_subscription.group_brightloop_admin') or self.env.is_superuser()
                if not current_is_admin:
                    # Check if vals tries to add staff or admin group
                    for cmd in vals['groups_id']:
                        if len(cmd) >= 2 and cmd[0] in [4, 6]:
                            added_ids = cmd[2] if cmd[0] == 6 else [cmd[1]]
                            target_restricted_ids = [g.id for g in [admin_group, staff_group] if g]
                            if any(gid in target_restricted_ids for gid in added_ids):
                                raise AccessError(_("Only administrators can assign or modify Staff and Admin account permissions."))
                                
        return super().write(vals)

    @api.model_create_multi
    def create(self, vals_list):
        admin_group = self.env.ref('brightloop_subscription.group_brightloop_admin', raise_if_not_found=False)
        staff_group = self.env.ref('brightloop_subscription.group_brightloop_staff', raise_if_not_found=False)
        current_is_admin = self.env.user.has_group('brightloop_subscription.group_brightloop_admin') or self.env.is_superuser()

        for vals in vals_list:
            if vals.get('password'):
                self.validate_password_complexity(vals['password'])
            if 'groups_id' in vals and not current_is_admin:
                for cmd in vals['groups_id']:
                    if len(cmd) >= 2 and cmd[0] in [4, 6]:
                        added_ids = cmd[2] if cmd[0] == 6 else [cmd[1]]
                        target_restricted_ids = [g.id for g in [admin_group, staff_group] if g]
                        if any(gid in target_restricted_ids for gid in added_ids):
                            raise AccessError(_("Only administrators can create internal staff or admin accounts."))
        return super().create(vals_list)
