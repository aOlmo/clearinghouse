"""
These are the django settings for the seattlegeni project. See the README.txt
file for details on what needs to be set in this file. At a minimum for
development, it will be the database connection info and the SECRET_KEY value.

For public deployment, see the README.txt file for information about which
additional changes you'll need to make to this file.
"""

import django
import os

from seattlegeni.common.util import log



# If DEBUG is True, then error details will be shown on the website and ADMINS
# will not receive an email when an error occurs. So, this should be False in
# production.
DEBUG = True
TEMPLATE_DEBUG = DEBUG

# The log level used by the seattlegeni log module. All messages at this level
# or more severe will be logged.
LOG_LEVEL = log.LOG_LEVEL_DEBUG

# Rather than make the log module have to import this settings file to set the
# log level, just set it right here.
log.set_log_level(LOG_LEVEL)

# This is needed to allow xmlrpc requests to work when they don't have a slash
# on the end of the url.
APPEND_SLASH = False

# The directory the settings.py file is in is what we consider the root of the website. 
WEBSITE_ROOT = os.path.dirname(__file__)

# Email addresses of people that should be emailed when a 500 error occurs on
# the site when DEBUG = False (that is, in production). Leave this to be empty
# if nobody should receive an email. 
ADMINS = (
    # ('Your Name', 'your_email@domain.com'),
)

# To be able to send mail to ADMINS when there is an error, django needs to
# know about an SMTP server it can use. That info is defined here.
#EMAIL_HOST = 'smtp.gmail.com'
#EMAIL_HOST_USER = 'an.error.sending.account@gmail.com'
#EMAIL_HOST_PASSWORD = 'PASSWORD_HERE'
#EMAIL_PORT = 587
#EMAIL_USE_TLS = True

# Email address that error notifications will be sent from.
#SERVER_EMAIL = "error@seattlegeni.server.hostname"

MANAGERS = ADMINS

DATABASE_ENGINE = 'mysql'      # 'postgresql_psycopg2', 'postgresql', 'mysql', 'sqlite3' or 'oracle'.
DATABASE_NAME = 'FILL_THIS_IN' # Or path to database file if using sqlite3.
DATABASE_USER = 'FILL_THIS_IN' # Not used with sqlite3.
DATABASE_PASSWORD = 'FILL_THIS_IN' # Not used with sqlite3.
DATABASE_HOST = ''             # Set to empty string for localhost. Not used with sqlite3.
DATABASE_PORT = ''             # Set to empty string for default. Not used with sqlite3.

# Make this unique, and don't share it with anybody.
# Fill this in!
SECRET_KEY = ''



# Called when new database connections are created (see below).
def _prepare_newly_created_db_connection(sender, **kwargs):
  from seattlegeni.common.api import maindb
  maindb.init_maindb()


# If this is a modern-enough version of django to support specifying a function
# to be called on database connection creation, then have it call init_maindb()
# at that time. This is to help prevent init_maindb() from accidentally not
# being called when it should be.
# Maybe this code shouldn't go in settings.py. I was concerned that putting it
# in maindb, however, might cause the signal to be registered after the database
# connection was created. As far as I know, putting it in settings.py is the
# closest to a guarantee that it will be executed.
if django.VERSION >= (1,1):
  # connection_created only exists with django >= 1.1
  from django.db.backends.signals import connection_created
  connection_created.connect(_prepare_newly_created_db_connection)
else:
  log.error("You must use django >= 1.1 in order to support automatically " +
            "perform custom database connection initialization. (See settings.py)")
  


# Local time zone for this installation. Choices can be found here:
# http://en.wikipedia.org/wiki/List_of_tz_zones_by_name
# although not all choices may be available on all operating systems.
# If running in a Windows environment this must be set to the same as your
# system time zone.
TIME_ZONE = 'America/Los_Angeles'

# Language code for this installation. All choices can be found here:
# http://www.i18nguy.com/unicode/language-identifiers.html
LANGUAGE_CODE = 'en-us'

SITE_ID = 1

# If you set this to False, Django will make some optimizations so as not
# to load the internationalization machinery.
USE_I18N = True

# Absolute path to the directory that holds media.
# Example: "/home/media/media.lawrence.com/"
MEDIA_ROOT = WEBSITE_ROOT + '/html/media/'

# URL that handles the media served from MEDIA_ROOT. Make sure to use a
# trailing slash if there is a path component (optional in other cases).
# Examples: "http://media.lawrence.com", "http://example.com/media/"
MEDIA_URL = '/site_media/'

# URL prefix for admin media -- CSS, JavaScript and images. Make sure to use a
# trailing slash.
# Examples: "http://foo.com/media/", "/media/".
ADMIN_MEDIA_PREFIX = '/admin_media/'

# List of callables that know how to import templates from various sources.
TEMPLATE_LOADERS = (
  'django.template.loaders.filesystem.load_template_source',
  'django.template.loaders.app_directories.load_template_source',
# 'django.template.loaders.eggs.load_template_source',
)

MIDDLEWARE_CLASSES = (
  'django.middleware.common.CommonMiddleware',
  'django.contrib.sessions.middleware.SessionMiddleware',
  'django.contrib.auth.middleware.AuthenticationMiddleware',
  # Our own middleware that logs when a request is initially received and
  # sets up the logger to log other messages with per-request unique ids.
  'seattlegeni.website.middleware.logrequest.LogRequestMiddleware',
)

ROOT_URLCONF = 'website.urls'

TEMPLATE_DIRS = (
  # Put strings here, like "/home/html/django_templates" or "C:/www/django/templates".
  # Always use forward slashes, even on Windows.
  # Don't forget to use absolute paths, not relative paths.
  WEBSITE_ROOT + '/html/templates'
)

INSTALLED_APPS = (
  'django.contrib.admin',
  'django.contrib.auth',
  'django.contrib.contenttypes',
  'django.contrib.sessions',
  'django.contrib.sites',
  
  # We have our maindb model defined here, so it must be listed.
  'seattlegeni.website.control',
)
