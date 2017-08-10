from django.conf.urls import *

from django.conf import settings
from django.views.generic import RedirectView

from django.shortcuts import render_to_response, redirect
# Uncomment the next two lines to enable the admin:
from django.contrib import admin

admin.autodiscover()

# We override the default error handler because we want to pass a RequestContext
# to the template so that it can know the MEDIA_URL and so look nice.
handler500 = 'clearinghouse.website.html.errorviews.internal_error'
# the format for urlpatterns is
# (regular exp, function, optional dictionary, optional name)
urlpatterns = patterns('',

                       url(r'^html/', include('clearinghouse.website.html.urls')),
                       url(r'^download/', include('clearinghouse.website.html.downloadurls')),
                       url(r'^xmlrpc', include('clearinghouse.website.xmlrpc.urls')),
                       (r'^reports/', include('clearinghouse.website.reports.urls')),
                       # OPenID/OAuth pages, RedirectView.as_view cuts off the complete/backend/ in the url
                       url(r'^complete/(?P<backend>[^/]+)/error', RedirectView.as_view(url='/html/error')),
                       url(r'^complete/(?P<backend>[^/]+)/associate_error',
                           RedirectView.as_view(url='/html/associate_error')),
                       url(r'^complete/(?P<backend>[^/]+)/profile', RedirectView.as_view(url='/html/profile')),
                       # url(r'^complete/(?P<backend>[^/]+)/new_auto_register_user', RedirectView.as_view(url='/html/new_auto_register_user')),
                       # Currently unused, we've disabled disconnected social accounts
                       # url(r'^disconnect/(?P<backend>[^/]+)/profile', RedirectView.as_view(url='/html/profile')),
                       url(r'', include('social_auth.urls')),
                       # Uncomment the admin/doc line below and add 'django.contrib.admindocs'
                       # to INSTALLED_APPS to enable admin documentation:
                       # (r'^admin/doc/', include('django.contrib.admindocs.urls')),
                       # Uncomment the next line to enable the admin:
                       url(r'^admin/', include(admin.site.urls)),
                       )

# If DEBUG is True, then this is for development rather than production. So,
# have django serve static files so apache isn't needed for development.
if settings.DEBUG:
  urlpatterns += patterns('',
                          (r'^' + settings.MEDIA_URL[1:] + '(?P<path>.*)$', 'django.views.static.serve',
                           {'document_root': settings.MEDIA_ROOT}),
                          )
