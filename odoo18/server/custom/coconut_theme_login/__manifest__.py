{
    'name': 'Coconut Theme Login',
    'version': '18.0.1.0.0',
    'category': 'Themes',
    'depends': ['web', 'auth_signup'],
    'data': [
        'views/login_templates.xml',
    ],
    'assets': {
        'web.assets_frontend': [
            'coconut_theme_login/static/src/css/login_theme.css',
        ],
    },
    'installable': True,
    'author': 'Coconut Team',
    'license': 'LGPL-3',
    'description': 'Login page theme dengan tema kelapa - hijau dan coklat profesional',
}
