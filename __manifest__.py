{
    'name': 'Attendance Intelligence & IP Validator',
    'version': '1.1.0',
    'category': 'Human Resources/Attendances',
    'summary': 'Next-Gen IP Security, Daily Check-in Limits, and EOD Reporting System',
    'description': """
Attendance Intelligence Pro
===========================
A high-security attendance extension for Odoo 18.

Key Features:
-------------
* **IP-Based Validation**: Restrict check-in/out to authorized office networks.
* **Daily Attendance Guard**: Prevents multiple check-ins per day (Timezone Aware).
* **EOD Insights**: Mandatory "End of Day" summary popups for better employee accountability.
* **Premium UX**: Smooth animations, glassmorphism dialogs, and interactive dashboards.
* **HR Audit Tools**: Advanced filters to track missing eod reports.

Designed for security-conscious organizations.
    """,
    'author': 'ByteScripterz',
    'website': 'https://www.bytescripterz.com',
    'depends': ['hr_attendance', 'hr'],
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
    'images': ['static/description/banner.png'],
    'installable': True,
    'application': False,
    'license': 'LGPL-3',
}