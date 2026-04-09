# {
#     'name': 'Utility Hub',
#     'version': '1.0',
#     'summary': 'Custom Utility Hub Module',
#     'description': 'My first custom Odoo custom module',
#     'author': 'WebDev',
#     'category': 'Custom',
#     'depends': ['base'],
#     'data': [],
#     'installable': True,
#     'application': True,
# }

{
    'name': 'Attendance Multi-IP Validator (Pro)',
    'version': '1.0',
    'summary': 'Secure IP-based attendance validation for multiple subnets',
    'description': """
        This module enhances the attendance system by allowing multiple IP addresses and subnets for validation.
        It ensures that employees can only mark attendance from authorized networks, improving security and flexibility.
    """,
    'author': 'ByteScripterz',
    'depends': ['hr_attendance'],
    'data': [],
    'installable': True,
    'application': False,
    'license': 'LGPL-3',
}