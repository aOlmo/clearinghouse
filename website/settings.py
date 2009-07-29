# Django settings for www project.

# For development: We use the os module to determine the directory this settings.py file is in.
import os

DEBUG = True
TEMPLATE_DEBUG = DEBUG

# This is needed to allow xmlrpc requests to work when they don't have a slash
# on the end of the url.
APPEND_SLASH = False

# The directory the settings.py file is in is what we consider the root of the website. 
WEBSITE_ROOT = os.path.dirname(__file__)

ADMINS = (
    # ('Your Name', 'your_email@domain.com'),
)

MANAGERS = ADMINS

DATABASE_ENGINE = 'mysql'    # 'postgresql_psycopg2', 'postgresql', 'mysql', 'sqlite3' or 'oracle'.
DATABASE_NAME = 'seattlegeni'  # Or path to database file if using sqlite3.
DATABASE_USER = 'root'             # Not used with sqlite3.
DATABASE_PASSWORD = ''         # Not used with sqlite3.
DATABASE_HOST = ''             # Set to empty string for localhost. Not used with sqlite3.
DATABASE_PORT = ''             # Set to empty string for default. Not used with sqlite3.



# JCS: This code may or may not be kept. If we don't keep it (because we use
#      django 1.0 not 1.1), then we need to find another way of making sure
#      to call init_database() from within the website, not just polling daemons.
## This is called by code below on connection creation if the version of django
## supports it.
#def _set_schema(sender, **kwargs):
#  from seattlegeni.common.api import maindb
#  maindb.init_database()
#
#
## If this is a modern-enough version of django to support specifying a function
## to be called on database connection creation, then have it call init_database
## at that time. This is to help prevent init_database() from accidentally not
## being called when it should be.
## Maybe this code shouldn't go in settings.py. I was concerned that putting it
## in maindb, however, might cause the signal to be registered after the database
## connection was created. As far as I know, putting it in settings.py is the
## closest to a guarantee that it will be executed.
#import django
#if django.VERSION >= (1,1):
#  from django.db.backends.signals import connection_created
#  connection_created.connect(_set_schema)
  
  

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
ADMIN_MEDIA_PREFIX = '/media/'

# Make this unique, and don't share it with anybody.
SECRET_KEY = 'p_(z-58(^j0rxzin-f2)r$0!oy4%_$(g!39mv+79%k1+oehfz$'

# List of callables that know how to import templates from various sources.
TEMPLATE_LOADERS = (
    'django.template.loaders.filesystem.load_template_source',
    'django.template.loaders.app_directories.load_template_source',
#     'django.template.loaders.eggs.load_template_source',
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
    'django.contrib.auth',
    'django.contrib.contenttypes',
    'django.contrib.sessions',
    'django.contrib.sites',
    
    # We have our maindb model defined here, so it must be listed.
    'seattlegeni.website.control',
)
