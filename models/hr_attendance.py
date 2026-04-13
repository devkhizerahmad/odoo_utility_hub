from datetime import timedelta
import ipaddress
import logging
from odoo import models, api, fields, _
from odoo.exceptions import ValidationError
from odoo.http import request

_logger = logging.getLogger(__name__)

class HrAttendance(models.Model):
    _inherit = 'hr.attendance'

    # Field to store EOD report
    eod_report = fields.Text(string="End of Day Report")

    def _validate_client_ip(self):
        """
        Validates if the user's IP is within the allowed networks.
        Allowed: 192.168.18.0/24 subnet and localhost.
        """
        ALLOWED_NETWORKS = [
            ipaddress.ip_network('192.168.18.0/24'), 
            ipaddress.ip_address('127.0.0.1'),       
            ipaddress.ip_address('::1'),             
        ]

        if not request:
            return True # Cron jobs or server actions bypass

        # Support for reverse proxy (Nginx etc.)
        header_ip = request.httprequest.environ.get('HTTP_X_FORWARDED_FOR')
        client_ip_str = header_ip.split(',')[0].strip() if header_ip else request.httprequest.remote_addr
        
        _logger.info("Attendance IP Validation: Client IP detected as %s", client_ip_str)

        try:
            client_ip = ipaddress.ip_address(client_ip_str)
            is_allowed = any(
                client_ip in net if isinstance(net, (ipaddress.IPv4Network, ipaddress.IPv6Network))
                else client_ip == net 
                for net in ALLOWED_NETWORKS
            )

            if not is_allowed:
                _logger.warning("Access Denied for IP: %s", client_ip_str)
                raise ValidationError(_(
                    "Access Denied: Your IP address (%s) is not authorized for attendance.\n"
                    "Please connect from the office network."
                ) % client_ip_str)

        except ValueError:
            _logger.error("Invalid IP format detected: %s", client_ip_str)
            raise ValidationError(_("System Error: Invalid IP address format (%s).") % client_ip_str)

        return True

    def _check_daily_attendance(self, employee_id):
        """
        Check if the employee has already checked in today (Local Timezone).
        """
        if not employee_id:
            return

        # Get the current date in the user's/employee's timezone
        today = fields.Date.context_today(self)
        
        # Search for any attendance record for this employee where check_in falls on 'today'
        existing_attendance = self.search([
            ('employee_id', '=', employee_id),
            ('check_in', '>=', fields.Datetime.to_string(fields.Datetime.to_datetime(today))),
            ('check_in', '<', fields.Datetime.to_string(fields.Datetime.to_datetime(today) + timedelta(days=1)))
        ], limit=1)

        if existing_attendance:
            raise ValidationError(_(
                "Attendance Alert: You have already checked in for today (%s).\n"
                "You can only check in once per day. Access will reset at midnight."
            ) % today)

    @api.model_create_multi
    def create(self, vals_list):
        # Validate IP and Daily Limit on Check-in
        self._validate_client_ip()
        for vals in vals_list:
            if 'employee_id' in vals:
                self._check_daily_attendance(vals['employee_id'])
        
        return super(HrAttendance, self).create(vals_list)

    def write(self, vals):
        # Validate IP on Check-out (when write contains check_out field)
        if 'check_out' in vals and vals.get('check_out'):
            self._validate_client_ip()
        return super(HrAttendance, self).write(vals)

    @api.model
    def action_submit_eod_checkout(self, attendance_id, eod_text):
        """
        Public method called from JS to submit EOD and checkout at once.
        """
        if not eod_text or len(eod_text) > 255:
            return {'success': False, 'error': 'EOD report is required and must be under 255 characters.'}
        
        try:
            if attendance_id:
                attendance = self.browse(attendance_id).exists()
            else:
                # Look for open attendance of the current user's employee
                employee_id = self.env.context.get('employee_id')
                if not employee_id:
                    employee_id = self.env.user.employee_id.id
                
                attendance = self.search([
                    ('employee_id', '=', employee_id),
                    ('check_out', '=', False)
                ], limit=1)

            if not attendance:
                return {'success': False, 'error': 'No active attendance record found to check out.'}

            # Using sudo() to bypass ACL write restrictions for normal users
            attendance.sudo().write({
                'check_out': fields.Datetime.now(),
                'eod_report': eod_text
            })
            return {'success': True}
        
        except ValidationError as e:
            # ValidationError from _validate_client_ip will be caught here
            return {'success': False, 'error': e.args[0] if e.args else str(e)}
        except Exception as e:
            _logger.error("Error in EOD Checkout: %s", str(e))
            return {'success': False, 'error': 'An unexpected error occurred.'}