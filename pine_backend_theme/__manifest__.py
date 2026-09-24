{
    'name': 'Pine Backend Theme Suite',
    'summary': 'A clean, modern backend theme with flexible customization.',
    'description': '''
        Pine Backend Theme is a polished, modern theme for Odoo that delivers
        a clean UI, responsive layout, and configurable styling. It provides
        ready-to-use assets, settings, and example views to speed up branding
        and customization work.
    ''',
    'version': '18.0.1.0.0',
    'category': 'Themes/Backend',
    'license': 'LGPL-3',
    'author': 'Daniel Geremew',
    'website': 'danielgeremew93@gmail.com',
    'depends': [
        'base_setup',
        'mail',
        'web',
        'web_editor',
        'auth_signup',
    ],
    'data': [
        'templates/web_layout.xml',
        'templates/webclient_colors.xml',
        'templates/webclient_appsbar.xml',
        'views/login.xml',
        'views/reset_pwd.xml',
        'views/home.xml',
        'views/res_config_settings.xml',
        'views/res_users_appsbar.xml',
        'views/res_users_chatter.xml',
        'views/res_users_dialog.xml',
    ],
    'assets': {
        'web._assets_primary_variables': [
            ('prepend', 'pine_backend_theme/static/src/scss/colors.scss'),
            (
                'before',
                'pine_backend_theme/static/src/scss/colors.scss',
                'pine_backend_theme/static/src/scss/colors_light.scss',
            ),
            'pine_backend_theme/static/src/scss/appsbar.variables.scss',
            (
                'after',
                'web/static/src/scss/primary_variables.scss',
                'pine_backend_theme/static/src/scss/variables.scss',
            ),
        ],
        'web._assets_backend_helpers': [
            'pine_backend_theme/static/src/scss/appsbar.mixins.scss',
        ],
        'web.assets_web_dark': [
            (
                'after',
                'pine_backend_theme/static/src/scss/appsbar.variables.scss',
                'pine_backend_theme/static/src/scss/appsbar.variables.dark.scss',
            ),
            (
                'after',
                'pine_backend_theme/static/src/scss/colors.scss',
                'pine_backend_theme/static/src/scss/colors_dark.scss',
            ),
        ],
        'web.assets_frontend': [
            'pine_backend_theme/static/src/webclient/login/login.scss',
            'pine_backend_theme/static/src/webclient/login/reset_pwd.scss',
        ],
        'web.assets_backend': [
            'pine_backend_theme/static/src/webclient/**/*.xml',
            'pine_backend_theme/static/src/webclient/**/*.scss',
            'pine_backend_theme/static/src/webclient/**/*.js',
            'pine_backend_theme/static/src/core/**/*.xml',
            'pine_backend_theme/static/src/core/**/*.scss',
            'pine_backend_theme/static/src/core/**/*.js',
            'pine_backend_theme/static/src/chatter/**/*.xml',
            'pine_backend_theme/static/src/chatter/**/*.scss',
            'pine_backend_theme/static/src/chatter/**/*.js',
            'pine_backend_theme/static/src/views/**/*.scss',
            'pine_backend_theme/static/src/views/**/*.js',
        ],
    },
    'images': [
        'static/description/icon.png',
        'static/description/banner.png',
    ],
    'post_init_hook': '_setup_module',
    'uninstall_hook': '_uninstall_cleanup',
}
