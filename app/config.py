import os
basedir = os.path.abspath(os.path.dirname(__file__))

CSRF_ENABLED = True
SECRET_KEY = '12345'
SQLALCHEMY_DATABASE_URI = 'sqlite:///site.db'
SQLALCHEMY_MIGRATE_REPO = os.path.join(basedir, 'db_repository')
MAIL_SERVER = 'smtp.googlemail.com'
MAIL_PORT = 587
MAIL_USE_TLS = True
MAIL_USERNAME = os.environ.get('EMAIL_USER')
MAIL_PASSWORD = os.environ.get('EMAIL_PASS')
