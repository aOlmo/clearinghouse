from django.conf.urls.defaults import *

# Uncomment the next two lines to enable the admin:
# from django.contrib import admin
# admin.autodiscover()

urlpatterns = patterns('seattlegeni.website.html.views',

                       # Previously defined in accounts/urls.py.                       
                       (r'^register$', 'register',{},'register'),
                       (r'^login$', 'login',{},'login'), 
                       (r'^logout$', 'logout',{},'logout'),
                       (r'^accounts_help$', 'accounts_help',{},'accounts_help'),
                       #(r'^simplelogin$', 'simplelogin',{},'simplelogin'), 
                       
                       # Top level urls and functions:
                       # show the user info page for this user listing the public/private keys, and user information
                       (r'^profile$', 'profile', {}, 'profile'), # was user_info
                       # show the current donation for this user
                       (r'^mygeni$', 'mygeni', {}, 'mygeni'), # was donations
                       # show the used resources page (with all the currently acquired vessels)
                       (r'^myvessels$', 'myvessels', {}, 'myvessels'), # was used_resources
                       # show the help page
                       (r'^help$', 'help', {}, 'help'),
                       # getdonations page (to download installers)
                       (r'^getdonations$', 'getdonations', {}, 'getdonations'),
#                       
#                      # 'My GENI' page functions:
                       # get new resources (from form)
                       (r'^get_resources$', 'get_resources', {}, 'get_resources'),
                       # delete some specific resource for this user (from form)
                       (r'^del_resource$', 'del_resource', {}, 'del_resource'),
                       # delete all resources for this user (from form)
                       (r'^del_all_resource$', 'del_all_resources', {}, 'del_all_resources'),
#                       
                       # Profile page functions:
                       # generate a new public/private key pair for the user (from form)
                       (r'^gen_new_key$', 'gen_new_key', {}, 'gen_new_key'),
                       # delete the user's private key from the server (from form)
                       (r'^del_priv$', 'del_priv', {}, 'del_priv'),
                       # download the user's private key (from form)
                       (r'^priv_key$', 'priv_key', {}, 'priv_key'),
                       # download the user's public key (from form)
                       (r'^pub_key$', 'pub_key', {}, 'pub_key'),
                       
                       # 'Get Donations' functions:
                       # show the main download page for downloading installers
                       (r'^(?P<username>\w{3,32})/$', 'download', {}, 'installers'),
                       # build and download the windows installer
                       (r'^(?P<username>\w{3,32})/seattle_win.zip$', 'build_win_installer', {}, 'win_installer'),
                       # build and download the linux installer
                       (r'^(?P<username>\w{3,32})/seattle_linux.tgz$', 'build_linux_installer', {}, 'linux_installer'),
                       # build and download the mac installer
                       (r'^(?P<username>\w{3,32})/seattle_mac.tgz$', 'build_mac_installer', {}, 'mac_installer'),
                       # help page
                       (r'^(?P<username>\w{3,32})/help$', 'donations_help', {}, 'donations_help'),
#                      # create a new share with another use (from form)
#                      (r'^new_share$', 'new_share', {}, 'new_share'),
#                      # delete an existing share with another user (from form)
#                      (r'^del_share$', 'del_share', {}, 'del_share'),

                       # AJAX functions, called by the 'My GENI' page
                       #(r'^ajax_getcredits$', 'ajax_getcredits', {}, 'ajax_getcredits'),
                       #(r'^ajax_getshares$', 'ajax_getshares', {}, 'ajax_getshares'),
                       #(r'^ajax_editshare$', 'ajax_editshare', {}, 'ajax_editshare'),
                       #(r'^ajax_createshare$', 'ajax_createshare', {}, 'ajax_createshare'),
                       #(r'^ajax_getvessels$', 'ajax_getvessels', {}, 'ajax_getvesseles'),
                      )
