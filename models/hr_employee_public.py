# -*- coding: utf-8 -*-

from odoo import fields, models


class HrEmployeePublic(models.Model):
    _inherit = 'hr.employee.public'

    allow_remote_checkin = fields.Boolean(
        compute='_compute_allow_remote_checkin',
        readonly=True,
    )

    def _compute_allow_remote_checkin(self):
        employee_model = self.env['hr.employee']
        has_flag = 'allow_remote_checkin' in employee_model._fields
        for employee in self:
            employee.allow_remote_checkin = (
                employee.employee_id.allow_remote_checkin if has_flag and employee.employee_id else False
            )
