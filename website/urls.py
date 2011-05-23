from django.conf.urls.defaults import *

from django.conf import settings

# Uncomment the next two lines to enable the admin:
from django.contrib import admin
admin.autodiscover()

# We override the default error handler because we want to pass a RequestContext
# to the template so that it can know the MEDIA_URL and so look nice.
handler500 = 'seattlegeni.website.html.errorviews.internal_error'

urlpatterns = patterns('',
    
    (r'^html/', include('seattlegeni.website.html.urls')),
    (r'^download/', include('seattlegeni.website.html.downloadurls')),
    (r'^xmlrpc', include('seattlegeni.website.xmlrpc.urls')),
    (r'^reports/', include('seattlegeni.website.reports.urls')),

    # Uncomment the admin/doc line below and add 'django.contrib.admindocs' 
    # to INSTALLED_APPS to enable admin documentation:
    # (r'^admin/doc/', include('django.contrib.admindocs.urls')),

    # Uncomment the next line to enable the admin:
    (r'^admin/', include(admin.site.urls)),
)

# If DEBUG is True, then this is for development rather than production. So,
# have django serve static files so apache isn't needed for development.
if settings.DEBUG:
  urlpatterns += patterns('',
      (r'^' + settings.MEDIA_URL[1:] + '(?P<path>.*)$', 'django.views.static.serve',
        {'document_root': settings.MEDIA_ROOT}),
  )
