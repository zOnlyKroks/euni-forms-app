import os

# Every setting in base.py can be overloaded by redefining it here.
from .base import *

# This is your website's URL, set it accordingly
SITE_URL = os.getenv("AA_SITE_URL", "http://localhost:8000")

# Django security
CSRF_TRUSTED_ORIGINS = [SITE_URL]

# These are required for Django to function properly. Don't touch.
ROOT_URLCONF = "myauth.urls"
WSGI_APPLICATION = "myauth.wsgi.application"
SECRET_KEY = os.getenv("AA_SECRET_KEY")

# This is where css/images will be placed for your webserver to read
STATIC_ROOT = "/app/myauth/static/"

# Change this to change the name of the auth site displayed
# in page titles and the site header.
SITE_NAME = os.getenv("AA_SITE_NAME")

# Change this to enable/disable debug mode, which displays
# useful error messages but can leak sensitive data.
DEBUG = os.getenv("AA_DEBUG", "True").lower() in [
    "true",
    "1",
    "t",
    "on",
    "yes",
]

# Add any additional apps to this list.
INSTALLED_APPS += [
    "eunicore",
    "euniforms",
]

# To change the logging level for extensions, uncomment the following line.
# LOGGING['handlers']['extension_file']['level'] = 'DEBUG'


# Enter credentials to use MySQL/MariaDB. Comment out to use sqlite3
DATABASES["default"] = {
    "ENGINE": "django.db.backends.mysql",
    "NAME": os.getenv("AA_DB_NAME"),
    "USER": os.getenv("AA_DB_USER"),
    "PASSWORD": os.getenv("AA_DB_PASSWORD"),
    "HOST": os.getenv("AA_DB_HOST", "localhost"),
    "PORT": os.getenv("AA_DB_PORT", "3306"),
    "OPTIONS": {"charset": os.getenv("AA_DB_CHARSET", "utf8mb4")},
}

# Register an application at https://developers.eveonline.com for Authentication
# & API Access and fill out these settings. Be sure to set the callback URL
# to https://example.com/sso/callback substituting your domain for example.com
# Logging in to auth requires the publicData scope (can be overridden through the
# LOGIN_TOKEN_SCOPES setting). Other apps may require more (see their docs).
ESI_SSO_CLIENT_ID = os.getenv("ESI_SSO_CLIENT_ID")
ESI_SSO_CLIENT_SECRET = os.getenv("ESI_SSO_CLIENT_SECRET")
ESI_SSO_CALLBACK_URL = f"{SITE_URL}/sso/callback"
# A server maintainer that CCP can contact in case of issues.
ESI_USER_CONTACT_EMAIL = os.getenv("ESI_USER_CONTACT_EMAIL")

# By default emails are validated before new users can log in.
# It's recommended to use a free service like SparkPost or Elastic Email to send email.
# https://www.sparkpost.com/docs/integrations/django/
# https://elasticemail.com/resources/settings/smtp-api/
# Set the default from email to something like 'noreply@example.com'
# Email validation can be turned off by uncommenting the line below. This can break some services.
REGISTRATION_VERIFY_EMAIL = False
EMAIL_HOST = os.getenv("AA_EMAIL_HOST", "")
EMAIL_PORT = int(os.getenv("AA_EMAIL_PORT", 587))
EMAIL_HOST_USER = os.getenv("AA_EMAIL_HOST_USER", "")
EMAIL_HOST_PASSWORD = os.getenv("AA_EMAIL_HOST_PASSWORD", "")
EMAIL_USE_TLS = os.getenv("AA_EMAIL_USE_TLS", "True").lower() in [
    "true",
    "1",
    "t",
    "on",
    "yes",
]
DEFAULT_FROM_EMAIL = os.getenv("AA_EMAIL_DEFAULT_FROM", "")

#######################################
# Add any custom settings below here. #
#######################################
# EVE University is English-speaking. By default Alliance Auth follows the
# browser's Accept-Language header (e.g. de-DE) and serves its translated
# (German) UI strings. Disabling i18n forces every string to its English
# source, regardless of browser language. To re-enable translations, set
# USE_I18N = True and choose a per-user language in the Auth profile instead.
LANGUAGE_CODE = "en"
USE_I18N = False

BROKER_URL = "redis://redis:6379/0"
CELERY_RESULT_BACKEND = "redis://redis:6379/0"
CACHES = {
    "default": {
        "BACKEND": "django_redis.cache.RedisCache",
        "LOCATION": "redis://redis:6379/1",
    }
}

AUTHENTICATION_BACKENDS = [
    "eunicore.auth.backends.EUniBackend",
    "django.contrib.auth.backends.ModelBackend",
]

TEMPLATES[0]["BACKEND"] = "eunicore.template.backends.EUniDjangoTemplates"
