from django.conf.urls import *

import clearinghouse.website.html.views as htmlviews

# Uncomment the next two lines to enable the admin:
# from django.contrib import admin
# admin.autodiscover()
# the format for urlpatterns is
# (regular exp, function, optional dictionary, optional name)
urlpatterns = patterns('clearinghouse.website.html.views',

                       # Previously defined in accounts/urls.py.                       
                       (r'^register$', htmlviews.register, {}, 'register'),
                       (r'^login$', htmlviews.login, {}, 'login'),
                       (r'^logout$', htmlviews.logout, {}, 'logout'),
                       (r'^accounts_help$', htmlviews.accounts_help,
                        {}, 'accounts_help'),
                       # (r'^simplelogin$', 'simplelogin',{},'simplelogin'),
                       # OpenID/OAuth error pages
                       (r'^error$', htmlviews.error, {}, 'error'),
                       (r'^associate_error$', htmlviews.associate_error, {},
                        'associate_error'),
                       # OpenID/OAuth auto register page
                       (r'^auto_register$', htmlviews.auto_register,
                        {}, 'auto_register'),
                       # Top level urls and functions:
                       # show the user info page for this user listing the
                       # public/private keys, and user information
                       (r'^profile$', htmlviews.profile, {}, 'profile'),  # was user_info
                       # show the expriment registration page for this user
                       (r'^registerexperiment$', htmlviews.registerexperiment, {}, 'registerexperiment'),
                       # OpenID/OAuth auto registered users get sent here after creation
                       # (r'^new_auto_register_user$', 'new_auto_register_user', {}, 'new_auto_register_user'), #currently not used
                       # show the used resources page (with all the currently acquired vessels)
                       (r'^myvessels$', htmlviews.myvessels, {}, 'myvessels'),  # was used_resources
                       # show the help page
                       (r'^help$', htmlviews.help, {}, 'help'),
                       # getdonations page (to download installers)
                       (r'^getdonations$', htmlviews.getdonations, {},
                        'getdonations'),

                       # 'My GENI' page functions:
                       # get new resources (from form)
                       (r'^get_resources$', htmlviews.get_resources, {},
                        'get_resources'),

                       # delete some specific resource for this user (from form)
                       (r'^del_resource$', htmlviews.del_resource, {},
                        'del_resource'),

                       # delete all resources for this user (from form)
                       (r'^del_all_resources$', htmlviews.del_all_resources,
                        {}, 'del_all_resources'),

                       # renew some specific resource for this user (from form)
                       (r'^renew_resource$', htmlviews.renew_resource, {},
                        'renew_resource'),

                       # renew all resource for this user (from form)
                       (r'^renew_all_resources$', htmlviews.renew_all_resources,
                        {}, 'renew_all_resources'),

                       # Display and allow changing the API key.
                       (r'^api_info$', htmlviews.api_info, {}, 'api_info'),

                       # Form to generate or upload a new key.
                       (r'^change_key$', htmlviews.change_key, {},
                        'change_key'),

                       # Profile page functions:
                       # delete the user's private key from the server (from form)
                       (r'^del_priv$', htmlviews.del_priv, {}, 'del_priv'),

                       # download the user's private key (from form)
                       (r'^priv_key$', htmlviews.priv_key, {}, 'priv_key'),

                       # download the user's public key (from form)
                       (r'^pub_key$', htmlviews.pub_key, {}, 'pub_key'),

                       # FIXME: what's this??????????????????????????????????????
                       #                       (r'^private/$', 'home.views.private'),
                       #                      # create a new share with another use (from form)
                       #                      (r'^new_share$', 'new_share', {}, 'new_share'),
                       #                      # delete an existing share with another user (from form)
                       #                      (r'^del_share$', 'del_share', {}, 'del_share'),

                       # AJAX functions, called by the 'My GENI' page
                       # (r'^ajax_getcredits$', 'ajax_getcredits', {}, 'ajax_getcredits'),
                       # (r'^ajax_getshares$', 'ajax_getshares', {}, 'ajax_getshares'),
                       # (r'^ajax_editshare$', 'ajax_editshare', {}, 'ajax_editshare'),
                       # (r'^ajax_createshare$', 'ajax_createshare', {}, 'ajax_createshare'),
                       # (r'^ajax_getvessels$', 'ajax_getvessels', {}, 'ajax_getvesseles'),
                       )