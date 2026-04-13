{
    'name': 'Attendance Multi-IP Validator (Pro)',
    'version': '1.1',
    'summary': 'Secure IP-based attendance validation with EOD Popup',
    'description': """
        IP validation on Check-in/Check-out + EOD Popup before checkout.
    """,
    'author': 'ByteScripterz',
    'depends': ['hr_attendance'],
    'data': [
        'security/security.xml',
        'views/hr_attendance_views.xml',
    ],
    'assets': {
        'web.assets_backend': [
            'custom_attendance_ip/static/src/scss/custom_attendance.scss',
            'custom_attendance_ip/static/src/js/my_attendances.js',
            'custom_attendance_ip/static/src/xml/eod_dialog.xml',
        ],
    },
    'installable': True,
    'application': False,
    'license': 'LGPL-3',
}