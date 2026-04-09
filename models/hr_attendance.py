import ipaddress
import logging
from odoo import models, api, _
from odoo.exceptions import ValidationError
from odoo.http import request

_logger = logging.getLogger(__name__)

class HrAttendance(models.Model):
    _inherit = 'hr.attendance'

    @api.model_create_multi
    def create(self, vals_list):
        # --- PRODUCTION CONFIGURATION-- ff
        # 1. Define list of allowed network addresses and individual IP addresses
        # '192.168.18.0/24' subnet includes all addresses from 192.168.18.1 to 192.168.18.254
        ALLOWED_NETWORKS = [
            ipaddress.ip_network('192.168.18.0/24'), # Office network subnet (configured by administrator)
            ipaddress.ip_address('127.0.0.1'),       # Localhost IPv4
            ipaddress.ip_address('::1'),             # Localhost IPv6
        ]

        # 2. Extract client IP address from HTTP request headers (optimized for proxy/Nginx environments)
        # Only perform IP validation if request context exists (allows cron jobs to bypass validation)
        if request:
            header_ip = request.httprequest.environ.get('HTTP_X_FORWARDED_FOR')
            client_ip_str = header_ip.split(',')[0].strip() if header_ip else request.httprequest.remote_addr
            
            # Log client IP for debugging and audit trails
            print(f"DEBUG: Attempting Attendance - Current User IP: {client_ip_str}")
            _logger.info("Attendance Validation: Client IP detected as %s", client_ip_str)

            try:
                client_ip = ipaddress.ip_address(client_ip_str)
                
                # Verify if the client IP is in the allowed networks or individual address list
                is_allowed = any(
                    client_ip in net if isinstance(net, ipaddress.IPv4Network) or isinstance(net, ipaddress.IPv6Network)
                    else client_ip == net 
                    for net in ALLOWED_NETWORKS
                )

                if not is_allowed:
                    _logger.warning("Access Denied for IP: %s", client_ip_str)
                    raise ValidationError(_(
                        "Access Denied: Your IP address (%s) is not authorized for attendance.\n"
                        "Please connect from the office network or contact your administrator."
                    ) % client_ip_str)

            except ValueError:
                _logger.error("Invalid IP format detected: %s", client_ip_str)
                raise ValidationError(_("System Error: Invalid IP address format (%s).") % client_ip_str)

        # 3. If validation passes or no request context is available, proceed with attendance record creation
        return super(HrAttendance, self).create(vals_list)