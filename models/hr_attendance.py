# -*- coding: utf-8 -*-
"""
Module: custom_attendance_ip.models.hr_attendance
Description: Extends the standard hr.attendance model to incorporate strict IP-based validation,
             timezone-aware daily attendance limits, and End of Day (EOD) reporting mechanisms.
"""

from datetime import datetime, time, timedelta
import pytz
import ipaddress
import logging
from odoo import models, api, fields, _
from odoo.exceptions import ValidationError
from odoo.http import request

_logger = logging.getLogger(__name__)


class HrAttendance(models.Model):
    """
    Inherits hr.attendance to apply security rules and validation logic.
    Ensures employees can only check in from trusted networks and enforces one check-in per day.
    """
    _inherit = 'hr.attendance'

    # ---------------------------------------------------------
    # DB FIELDS
    # ---------------------------------------------------------
    eod_report = fields.Text(
        string="End of Day Report",
        help="Summary provided by the employee detailing accomplishments before check-out."
    )

    # ---------------------------------------------------------
    # VALIDATION METHODS
    # ---------------------------------------------------------
    def _get_allowed_networks(self):
        """
        Fetches allowed IPs and Networks from Odoo System Parameters.
        Key: custom_attendance.allowed_ips
        Default: 192.168.18.0/24, 127.0.0.1, ::1
        """
        param = self.env['ir.config_parameter'].sudo().get_param(
            'custom_attendance.allowed_ips', 
            '192.168.18.0/24, 127.0.0.1, ::1'
        )
        networks = []
        for ip_str in param.split(','):
            ip_str = ip_str.strip()
            if not ip_str:
                continue
            try:
                if '/' in ip_str:
                    networks.append(ipaddress.ip_network(ip_str, strict=False))
                else:
                    networks.append(ipaddress.ip_address(ip_str))
            except ValueError:
                _logger.error("Invalid IP/Network config in System Parameters: %s", ip_str)
        return networks

    def _validate_client_ip(self):
        """
        Validates the incoming HTTP request's IP against a whitelist of authorized office networks.
        Prevents unauthorized remote check-ins/check-outs.
        """
        # Bypass validation for Internal CRON jobs or Server Actions (where request context is void)
        if not request:
            return True

        ALLOWED_NETWORKS = self._get_allowed_networks()

        # Extract client IP, respecting reverse proxies (Nginx, Traefik, HAProxy)
        header_ip = request.httprequest.environ.get('HTTP_X_FORWARDED_FOR')
        client_ip_str = header_ip.split(',')[0].strip() if header_ip else request.httprequest.remote_addr
        
        _logger.info("Attendance Tracker: Authenticating Client IP - %s", client_ip_str)

        try:
            client_ip = ipaddress.ip_address(client_ip_str)
            # Check if the extracted IP falls within any of the defined allowed networks
            is_allowed = any(
                client_ip in net if isinstance(net, (ipaddress.IPv4Network, ipaddress.IPv6Network))
                else client_ip == net 
                for net in ALLOWED_NETWORKS
            )

            if not is_allowed:
                _logger.warning("Security Policy Violation: Access Denied for IP %s", client_ip_str)
                raise ValidationError(_(
                    "Security Restricted: Your network IP (%s) is not whitelisted.\n"
                    "Attendance can only be logged from the registered office network."
                ) % client_ip_str)

        except ValueError:
            _logger.error("Data Integrity Error: Malformed IP Address format detected - %s", client_ip_str)
            raise ValidationError(_("System Error: Invalid IP address structure detected (%s).") % client_ip_str)

        return True

    def _check_daily_attendance(self, employee_id):
        """
        Validates if the employee has an existing check-in within the current localized calendar day.
        Utilizes `pytz` for precise UTC conversion, preventing midnight overlap anomalies.
        
        :param employee_id: ID of the hr.employee record
        """
        if not employee_id:
            return

        # Dynamically determine the active timezone (User Preference -> Context -> Fallback)
        tz_name = self.env.user.tz or self.env.context.get('tz') or 'UTC'
        user_tz = pytz.timezone(tz_name)
        
        # Calculate exactly what 'today' means in the user's localized timezone
        today_local = datetime.now(user_tz).date()
        
        # Create strict boundary markers for the local start and end of this specific day
        start_of_day_local = user_tz.localize(datetime.combine(today_local, time.min))
        end_of_day_local = user_tz.localize(datetime.combine(today_local, time.max))

        # Convert local boundaries safely back to raw UTC for accurate database querying
        start_of_day_utc = start_of_day_local.astimezone(pytz.UTC).replace(tzinfo=None)
        end_of_day_utc = end_of_day_local.astimezone(pytz.UTC).replace(tzinfo=None)

        # Query for any overlapping active attendance within today's 24-hr window
        existing_attendance = self.search([
            ('employee_id', '=', employee_id),
            ('check_in', '>=', start_of_day_utc),
            ('check_in', '<=', end_of_day_utc)
        ], limit=1)

        if existing_attendance:
            raise ValidationError(_(
                "Policy Enforcement: Duplicate Check-In detected.\n"
                "You have already initiated a session today (%s). Sessions reset at midnight locally."
            ) % today_local)

    # ---------------------------------------------------------
    # ORM OVERRIDES
    # ---------------------------------------------------------
    @api.model_create_multi
    def create(self, vals_list):
        """
        Intercepts creation sequence to enforce IP whitelisting and daily limitations on check-in.
        """
        self._validate_client_ip()
        for vals in vals_list:
            if 'employee_id' in vals:
                self._check_daily_attendance(vals['employee_id'])
        
        return super(HrAttendance, self).create(vals_list)

    def write(self, vals):
        """
        Intercepts write sequence specifically designed to enforce IP validations upon check-out action.
        """
        if 'check_out' in vals and vals.get('check_out'):
            self._validate_client_ip()
        return super(HrAttendance, self).write(vals)

    # ---------------------------------------------------------
    # PUBLIC EOD ENDPOINTS 
    # ---------------------------------------------------------
    @api.model
    def action_save_eod(self, attendance_id, eod_text):
        """
        RPC Endpoint consumed by the OWL frontend to secure End Of Day reports.
        Saved asynchronously before invoking Odoo's native checkout to preserve geolocation APIs.
        
        :param attendance_id: Int ID of active attendance record (if resolved client-side)
        :param eod_text: Content string provided by user.
        :return: Dictionary object dictating JSON-RPC success state
        """
        if not eod_text or len(eod_text) > 255:
            return {'success': False, 'error': 'EOD report is required (max 255 chars).'}
        
        try:
            if attendance_id:
                attendance = self.browse(attendance_id).exists()
            else:
                # Fallback: Identify the open session bound to the active context user
                employee_id = self.env.context.get('employee_id') or self.env.user.employee_id.id
                attendance = self.search([('employee_id', '=', employee_id), ('check_out', '=', False)], limit=1)

            if not attendance:
                return {'success': False, 'error': 'Cannot process EOD: No active attendance found.'}

            # Enforce access rights: Users cannot sign-out counterparts via RPC payload manipulation
            if not self.env.su and attendance.employee_id.user_id != self.env.user:
                return {'success': False, 'error': 'Unauthorized Action: You can only modify your own sessions.'}

            # Persist EOD content bypassing record-level normal constraint due to standard user groups
            attendance.sudo().write({
                'eod_report': eod_text
            })
            return {'success': True}
        
        except ValidationError as e:
            # Trap validation errors triggered in writes to broadcast cleanly to OWL UI
            return {'success': False, 'error': e.args[0] if e.args else str(e)}
        except Exception as e:
            _logger.error("Core Engine Fault in EOD Checkout Sequence: %s", str(e))
            return {'success': False, 'error': 'A systemic error occurred processing the EOD event.'}