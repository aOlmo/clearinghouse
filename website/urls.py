from django.conf.urls.defaults import *

from django.conf import settings

# Uncomment the next two lines to enable the admin:
from django.contrib import admin
admin.autodiscover()

urlpatterns = patterns('',
    
    (r'^html/', include('website.html.urls')),
    (r'^xmlrpc', include('website.xmlrpc.urls')),

    # Serve media statically for development.
    # TODO: use a flag in settings.py to determine whether to do this.
    # TODO: use the settings.MEDIA_URL value rather than hard code 'site_media'
    (r'^site_media/(?P<path>.*)$', 'django.views.static.serve',
      {'document_root': settings.MEDIA_ROOT}),

    # Uncomment the admin/doc line below and add 'django.contrib.admindocs' 
    # to INSTALLED_APPS to enable admin documentation:
    # (r'^admin/doc/', include('django.contrib.admindocs.urls')),

    # Uncomment the next line to enable the admin:
    (r'^admin/(.*)', admin.site.root),
)
