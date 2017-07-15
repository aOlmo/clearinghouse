"""
<Program>
  views.py

<Started>
  October, 2008

<Author>
  Ivan Beschastnikh
  Jason Chen
  Justin Samuel

<Purpose>
  This module defines the functions that correspond to each possible request
  made through the html frontend. The urls.py file in this same directory
  lists the url paths which can be requested and the corresponding function name
  in this file which will be invoked.
"""

import os
import sys
import shutil
import subprocess
import xmlrpclib

# Needed to escape characters for the Android referrer...
import urllib

from django.http import HttpResponse
from django.http import HttpResponseRedirect
from django.contrib.auth.forms import AuthenticationForm
from django.contrib.auth.decorators import login_required
from django.core.urlresolvers import reverse

#Used to display meaningful OpenID/OAuth error messages to the user
from django.contrib.messages.api import get_messages
from django.shortcuts import render_to_response, redirect
from social_auth.utils import setting
from django.template import RequestContext
# Any requests that change state on the server side (e.g. result in database
# modifications) need to be POST requests. This is for protecting against
# CSRF attacks (part, but not all, of that is our use of the CSRF middleware
# which only checks POST requests). Sometimes we use this decorator, sometimes
# we check the request type inside the view function.
from django.views.decorators.http import require_POST

# Make available all of our own standard exceptions.
from clearinghouse.common.exceptions import *

# This is the logging decorator use use.
from clearinghouse.common.util.decorators import log_function_call
from clearinghouse.common.util.decorators import log_function_call_without_return

# For user registration input validation
from clearinghouse.common.util import validations

from clearinghouse.common.util import log

from clearinghouse.website import settings
# FIXME: this patches the portability safe_type declaration, there might be a 
# cleaner way of doing this. We rely in the backup made by the safe module to
# reload type here.
import safe
__builtins__['type'] = safe._type

from clearinghouse.website import settings

# All of the work that needs to be done is passed through the controller interface.
from clearinghouse.website.control import interface

from clearinghouse.website.html import forms

from django.shortcuts import render

# import the logging library
import logging

# Get an instance of a logger
logger = logging.getLogger(__name__)

from seattle.repyportability import *
add_dy_support(locals())

rsa = dy_import_module("rsa.r2py")



from clearinghouse.website.control.models import Experiment
from clearinghouse.website.control.models import Sensor
from clearinghouse.website.control.models import Battery
from clearinghouse.website.control.models import Bluetooth
from clearinghouse.website.control.models import Cellular
from clearinghouse.website.control.models import Location
from clearinghouse.website.control.models import Settings
from clearinghouse.website.control.models import ConcretSensor
from clearinghouse.website.control.models import Signal_strengths
from clearinghouse.website.control.models import Wifi

#for user get donations
from clearinghouse.common.util.build_manager import BuildManager

# TODO: THIS IS USED FOR TESTING PURPOSES, DELETE LATER
# ------------------------------------------------------
import pdb
# ------------------------------------------------------

class LoggedInButFailedGetGeniUserError(Exception):
  """
  <Purpose>
  Indicates that a function tried to get a GeniUser record, and failed;
  while having passed the @login_required decorator. This means that a
  DjangoUser is logged in, but there is no corresponding GeniUser record.

  This exception should only be thrown from _validate_and_get_geniuser,
  and caught by methods with @login_required decorators.
  """





def _state_key_file_to_publickey_string(key_file_name):
  """
  Read a public key file from the the state keys directory and return it in
  a key string format.
  """
  fullpath = os.path.join(settings.SEATTLECLEARINGHOUSE_STATE_KEYS_DIR, key_file_name)
  return rsa.rsa_publickey_to_string(rsa.rsa_file_to_publickey(fullpath))





# The key used as the state key for new donations.
ACCEPTDONATIONS_STATE_PUBKEY = _state_key_file_to_publickey_string("acceptdonation.publickey")





def error(request):
  """
  <Purpose>
    If a OpenID/OAuth backend itself has an error(not a user or Seattle Clearinghouse's fault)
    a user will get redirected here.  This can happen if the backend rejects the user or from
    user cancelation.

  <Arguments>
    request:
      An HTTP request object.

  <Exceptions>
    None

  <Side Effects>
    None

  <Returns>
    An HTTP response object that represents the error page.
  """
  #Retrieve information which caused an error
  messages = get_messages(request)
  info =''
  try:
    user = _validate_and_get_geniuser(request)
    return profile(request, info, info, messages)
  except:
    return _show_login(request, 'accounts/login.html', {'messages' : messages})





@login_required
def associate_error(request):
  """
  <Purpose>
    If an error occured during the OpenId/OAuth association process a user will get
    redirected here.
  <Arguments>
    request:
      An HTTP request object.
    backend:
      An OpenID/OAuth backend ex google,facebook etc.
  <Exceptions>
    None
  <Side Effects>
    None
  <Returns>
    An HTTP response object that represents the associate_error page.
  """
  info=''
  error_msg = "Whoops, this account is already linked to another Seattle Clearninghouse user."
  return profile(request, info, error_msg)





def auto_register(request,backend=None,error_msgs=''):
  """
  <Purpose>
  Part of the SOCIAL_AUTH_PIPELINE whose order is mapped in settings.py.  If
  a user logs in with a OpenID/OAuth account and that account is not yet linked
  with a Clearinghouse account, he gets redirected here.
  If a valid username is entered then a new Seattle Clearinghouse user is created.

  <Arguments>
    request:
      An HTTP request object.
    backend:
      An OpenID/OAuth backend ex google,facebook etc.
  <Exceptions>

  <Side Effects>
    A new Seattle Clearinghouse user is created.
  <Returns>
    If a user passes in a valid username he continues the pipeline and moves
    forward in the auto register process.
  """
  # Check if a username is provided
  username_form = forms.AutoRegisterForm()
  if request.method == 'POST' and request.POST.get('username'):
    name = setting('SOCIAL_AUTH_PARTIAL_PIPELINE_KEY', 'partial_pipeline')
    username_form = forms.AutoRegisterForm(request.POST)
    if username_form.is_valid():
      username = username_form.cleaned_data['username']
      try:
        interface.get_user_without_password(username)
        error_msgs ='That username is already in use.'
      except DoesNotExistError:
        request.session['saved_username'] = request.POST['username']
        backend = request.session[name]['backend']
        return redirect('socialauth_complete', backend=backend)
  name = setting('SOCIAL_AUTH_PARTIAL_PIPELINE_KEY', 'partial_pipeline')
  backend=request.session[name]['backend']
  return render_to_response('accounts/auto_register.html', {'backend' : backend, 'error_msgs' : error_msgs, 'username_form' : username_form}, RequestContext(request))





@log_function_call_without_return
@login_required
def profile(request, info="", error_msg="", messages=""):
  """
  <Purpose>
    Display information about the user account.
    This method requires the request to represent a valid logged
    in user. See the top-level comment about the @login_required()
    decorator to achieve this property.  User account is editable through this
    method.
  <Arguments>
    request:
      An HTTP request object.
    info:
      Additional message to display at the top of the page in a green box.
    error_msg:
      Additional message to display at top of the page in a red box.
    messages
      Django social auth error message
  <Exceptions>
    None
  <Side Effects>
    None
  <Returns>
    An HTTP response object that represents the profile page.
  """
  try:
    user = _validate_and_get_geniuser(request)
  except LoggedInButFailedGetGeniUserError:
    return _show_failed_get_geniuser_page(request)

  email_form = forms.gen_edit_user_form(instance=user)
  affiliation_form = forms.gen_edit_user_form(instance=user)
  password_form = forms.EditUserPasswordForm()

  if request.method == 'POST':
    if 'affiliation' in request.POST:
       affiliation_form = forms.gen_edit_user_form(('affiliation',), request.POST, instance=user)
       if affiliation_form.is_valid():
         new_affiliation = affiliation_form.cleaned_data['affiliation']
         interface.change_user_affiliation(user, new_affiliation)
         info ="Affiliation has been successfully changed to %s." % (user.affiliation)
    elif 'email' in request.POST:
       email_form = forms.gen_edit_user_form(('email',), request.POST, instance=user)
       if email_form.is_valid():
         new_email = email_form.cleaned_data['email']
         interface.change_user_email(user, new_email)
         info ="Email has been successfully changed to %s." % (user.email)
    elif 'password1' in request.POST:
       password_form = forms.EditUserPasswordForm( request.POST, instance=user)
       if password_form.is_valid():
         new_password = password_form.cleaned_data['password1']
         interface.change_user_password(user, new_password)
         info ="Password has been successfully changed"

  username = user.username
  affiliation = user.affiliation
  email = user.email
  port = user.usable_vessel_port
  has_privkey = user.user_privkey != None
  #currently not used, needed if editing user port is allowed
  #port_range = interface.get_useable_ports()
  #port_range_min = port_range[0]
  #port_range_max = port_range[-1]

  return render_to_response('control/profile.html',
                            {'email_form' : email_form,
                             'affiliation_form' : affiliation_form,
                             'password_form' : password_form,
                             'username' : username,
                             'affiliation' : affiliation,
                             'email' : email,
                             'port' : port,
                             'api_key' : user.api_key,
                             'has_privkey' : has_privkey,
                             #'port_range_min' : port_range_min,
                             #'port_range_max' : port_range_max,
                             'info' : info,
                             'error_msg' : error_msg,
                             'messages' : messages},
                            context_instance=RequestContext(request))


def register(request):
  try:
    # check to see if a user is already logged in. if so, redirect them to profile.
    user = interface.get_logged_in_user(request)
  except DoesNotExistError:
    pass
  else:
    return HttpResponseRedirect(reverse("profile"))

  page_top_errors = []
  if request.method == 'POST':

    #TODO: what if the form data isn't in the POST request? we need to check for this.
    form = forms.GeniUserCreationForm(request.POST, request.FILES)
    # Calling the form's is_valid() function causes all form "clean_..." methods to be checked.
    # If this succeeds, then the form input data is validated per field-specific cleaning checks. (see forms.py)
    # However, we still need to do some checks which aren't doable from inside the form class.
    if form.is_valid():
      username = form.cleaned_data['username']
      password = form.cleaned_data['password1']
      affiliation = form.cleaned_data['affiliation']
      email = form.cleaned_data['email']
      pubkey = form.cleaned_data['pubkey']

      try:
        validations.validate_username_and_password_different(username, password)
      except ValidationError, err:
        page_top_errors.append(str(err))

      # NOTE: gen_upload_choice turns out to be a *string* when retrieved, hence '2'
      if form.cleaned_data['gen_upload_choice'] == '2' and pubkey == None:
        page_top_errors.append("Please select a public key to upload.")

      # only proceed with registration if there are no validation errors
      if page_top_errors == []:
        try:
          # we should never error here, since we've already finished validation at this point.
          # but, just to be safe...
          user = interface.register_user(username, password, email, affiliation, pubkey)
        except ValidationError, err:
          page_top_errors.append(str(err))
        else:
          return _show_login(request, 'accounts/login.html',
                             {'msg' : "Username %s has been successfully registered." % (user.username)})
  else:
    form = forms.GeniUserCreationForm()
  return render_to_response('accounts/register.html',
          {'form' : form, 'page_top_errors' : page_top_errors},
          context_instance=RequestContext(request))





def _show_login(request, ltemplate, template_dict, form=None):
    """
    <Purpose>
        Show the GENI login form

    <Arguments>
        request:
            An HTTP request object to use to populate the form

        ltemplate:
           The login template name to use for the login form. Right now
           this can be one of 'accounts/simplelogin.html' and
           'accounts/login.html'. They provide different ways of visualizing
           the login page.

        template_dict:
           The dictionary of arguments to pass to the template

        form:
           Either None or the AuthenticationForm to use as a 'form' argument
           to ltemplate. If form is None, a fresh AuthenticationForm() will be
           created and used.

    <Exceptions>
        None.

    <Side Effects>
        None.

    <Returns>
        An HTTP response object that represents the login page on
        success.
    """
    if form == None:
        # initial page load
        form = AuthenticationForm()
        # set test cookie, but only once -- remove it on login
        #if not request.session.test_cookie_worked():
        request.session.set_test_cookie()
    template_dict['form'] = form
    return render_to_response(ltemplate, template_dict,
            context_instance=RequestContext(request))





def login(request):
  try:
    # check to see if a user is already logged in. if so, redirect them to profile.
    user = interface.get_logged_in_user(request)
  except DoesNotExistError:
    pass
  else:
    return HttpResponseRedirect(reverse("profile"))

  ltemplate = 'accounts/login.html'
  if request.method == 'POST':
    form = AuthenticationForm(request.POST)

    if not request.session.test_cookie_worked():
      request.session.set_test_cookie()
      return _show_login(request, ltemplate, {'err' : "Please enable your cookies and try again."}, form)

    if request.POST.has_key('jsenabled') and request.POST['jsenabled'] == 'false':
      return _show_login(request, ltemplate, {'err' : "Please enable javascript and try again."}, form)

    try:
      interface.login_user(request, request.POST['username'], request.POST['password'])
    except DoesNotExistError:
      return _show_login(request, ltemplate, {'err' : "Wrong username or password."}, form)

    # only clear out the cookie if we actually authenticate and login ok
    request.session.delete_test_cookie()

    return HttpResponseRedirect(reverse("profile"))

  # request type is GET, show a fresh login page
  return _show_login(request, ltemplate, {})





def logout(request):
  interface.logout_user(request)
  # TODO: We should redirect straight to login page
  return HttpResponseRedirect(reverse("profile"))





@login_required
def help(request):
  try:
    user = _validate_and_get_geniuser(request)
  except LoggedInButFailedGetGeniUserError:
    return _show_failed_get_geniuser_page(request)

  return render_to_response('control/help.html', {'username': user.username},
          context_instance=RequestContext(request))





def accounts_help(request):
  return render_to_response('accounts/help.html', {},
          context_instance=RequestContext(request))





@login_required
def mygeni(request):
  try:
    user = _validate_and_get_geniuser(request)
  except LoggedInButFailedGetGeniUserError:
    return _show_failed_get_geniuser_page(request)

  total_vessel_credits = interface.get_total_vessel_credits(user)
  num_acquired_vessels = len(interface.get_acquired_vessels(user))
  avail_vessel_credits = interface.get_available_vessel_credits(user)

  if num_acquired_vessels > total_vessel_credits:
    percent_total_used = 100
    over_vessel_credits = num_acquired_vessels - total_vessel_credits
  else:
    percent_total_used = int((num_acquired_vessels * 1.0 / total_vessel_credits * 1.0) * 100.0)
    over_vessel_credits = 0

  # total_vessel_credits, percent_total_used, avail_vessel_credits
  return request_ro_response('control/mygeni.html',
                            {'username' : user.username,
                             'total_vessel_credits' : total_vessel_credits,
                             'used_vessel_credits' : num_acquired_vessels,
                             'percent_total_used' : percent_total_used,
                             'avail_vessel_credits' : avail_vessel_credits,
                             'over_vessel_credits' : over_vessel_credits},
                            context_instance=RequestContext(request))





@login_required
def myvessels(request, get_form=False, action_summary="", action_detail="", remove_summary=""):
  try:
    user = _validate_and_get_geniuser(request)
  except LoggedInButFailedGetGeniUserError:
    return _show_failed_get_geniuser_page(request)

  # get_form of None means don't show the form to acquire vessels.
  if interface.get_available_vessel_credits(user) == 0:
    get_form = None
  elif get_form is False:
    get_form = forms.gen_get_form(user)

  # shared vessels that are used by others but which belong to this user (TODO)
  shvessels = []

  # this user's used vessels
  my_vessels_raw = interface.get_acquired_vessels(user)
  my_vessels = interface.get_vessel_infodict_list(my_vessels_raw)

  # this user's number of donations, max vessels, total vessels and free credits
  my_donations = interface.get_donations(user)
  my_max_vessels = interface.get_available_vessel_credits(user)
  my_free_vessel_credits = interface.get_free_vessel_credits_amount(user)
  my_total_vessel_credits = interface.get_total_vessel_credits(user)

  for vessel in my_vessels:
    if vessel["expires_in_seconds"] <= 0:
      # We shouldn't ever get here, but just in case, let's handle it.
      vessel["expires_in"] = "Expired"
    else:
      days = vessel["expires_in_seconds"] / (3600 * 24)
      hours = vessel["expires_in_seconds"] / 3600 % 24
      minutes = vessel["expires_in_seconds"] / 60 % 60
      vessel["expires_in"] = "%dd %dh %dm" % (days, hours, minutes)

  # return the used resources page constructed from a template
  return render_to_response('control/myvessels.html',
                            {'username' : user.username,
                             'num_vessels' : len(my_vessels),
                             'my_vessels' : my_vessels,
                             'sh_vessels' : shvessels,
                             'get_form' : get_form,
                             'action_summary' : action_summary,
                             'action_detail' : action_detail,
                             'my_donations' : len(my_donations),
                             'my_max_vessels' : my_max_vessels,
                             'free_vessel_credits' : my_free_vessel_credits,
                             'total_vessel_credits' : my_total_vessel_credits,
                             'remove_summary' : remove_summary},
                        context_instance=RequestContext(request))





@login_required
def getdonations(request):
  try:
    user = _validate_and_get_geniuser(request)
  except LoggedInButFailedGetGeniUserError:
    return _show_failed_get_geniuser_page(request)

  domain = "https://" + request.get_host()
  username = user.username

  try:
    android = build_android_installer(request, username)
  except:
    android = "Failed to build installer."

  try:
    mac = build_mac_installer(request, username)
  except:
    mac = "Failed to build installer."

  try:
    linux = build_linux_installer(request, username)
  except:
    linux = "Failed to build installer."

  return render_to_response('control/getdonations.html',
                            {'username' : user.username,
                             'domain' : domain, 'android' : android, 'mac' : mac, 'linux' : linux},
                            context_instance=RequestContext(request))


def installers(request):

  try:
    user = _validate_and_get_geniuser(request)
  except LoggedInButFailedGetGeniUserError:
    return _show_failed_get_geniuser_page(request)

  username = user.username

  try:
    android = build_android_installer(request, username)
  except:
    android = "Failed to build installer."

  return render('common/installers.html', {'username' : username,
                                 'android' : android})


@login_required
def get_resources(request):
  try:
    user = _validate_and_get_geniuser(request)
  except LoggedInButFailedGetGeniUserError:
    return _show_failed_get_geniuser_page(request)

  # the request must be via POST. if not, bounce user back to My Vessels page
  if not request.method == 'POST':
    return myvessels(request)

  # try and grab form from POST. if it can't, bounce user back to My Vessels page
  get_form = forms.gen_get_form(user, request.POST)

  action_summary = ""
  action_detail = ""
  keep_get_form = False

  if get_form.is_valid():
    vessel_num = get_form.cleaned_data['num']
    vessel_type = get_form.cleaned_data['env']

    try:
      acquired_vessels = interface.acquire_vessels(user, vessel_num, vessel_type)
    except UnableToAcquireResourcesError, err:
      action_summary = "Unable to acquire vessels at this time."
      if str(err) == 'Acquiring NAT vessels is currently disabled. ':
        link = """<a href="{{ TESTBED_URL }}}blog">blog</a>"""
        action_detail += str(err) + 'Please check our '+ link  +' to see when we have re-enabled NAT vessels.'
      else:
        action_detail += str(err)
      keep_get_form = True
    except InsufficientUserResourcesError:
      action_summary = "Unable to acquire vessels: you do not have enough vessel credits to fulfill this request."
      keep_get_form = True
  else:
    keep_get_form = True

  if keep_get_form == True:
    # return the original get_form, since the form wasn't valid (or there were errors)
    return myvessels(request, get_form, action_summary=action_summary, action_detail=action_detail)
  else:
    # return a My Vessels page with the updated vessels/vessel acquire details/errors
    return myvessels(request, False, action_summary=action_summary, action_detail=action_detail)





@login_required
def del_resource(request):
  try:
    user = _validate_and_get_geniuser(request)
  except LoggedInButFailedGetGeniUserError:
    return _show_failed_get_geniuser_page(request)

  # the request must be via POST. if not, bounce user back to My Vessels page
  if not request.method == 'POST':
    return myvessels(request)

  if not request.POST['handle']:
    return myvessels(request)

  # vessel_handle needs to be a list (even though we only add one handle),
  # since get_vessel_list expects a list.
  vessel_handle = []
  vessel_handle.append(request.POST['handle'])
  remove_summary = ""

  try:
    # convert handle to vessel
    vessel_to_release = interface.get_vessel_list(vessel_handle)
  except DoesNotExistError:
    remove_summary = "Unable to remove vessel. The vessel you are trying to remove does not exist."
  except InvalidRequestError, err:
    remove_summary = "Unable to remove vessel. " + str(err)
  else:
    try:
      interface.release_vessels(user, vessel_to_release)
    except InvalidRequestError, err:
      remove_summary = "Unable to remove vessel. The vessel does not belong"
      remove_summary += " to you any more (maybe it expired?). " + str(err)

  return myvessels(request, remove_summary=remove_summary)






@login_required
def del_all_resources(request):
  try:
    user = _validate_and_get_geniuser(request)
  except LoggedInButFailedGetGeniUserError:
    return _show_failed_get_geniuser_page(request)

  # the request must be via POST. if not, bounce user back to My Vessels page
  if not request.method == 'POST':
    return myvessels(request)

  remove_summary = ""

  try:
    interface.release_all_vessels(user)
  except InvalidRequestError, err:
    remove_summary = "Unable to release all vessels: " + str(err)

  return myvessels(request, remove_summary=remove_summary)






@login_required
def renew_resource(request):
  try:
    user = _validate_and_get_geniuser(request)
  except LoggedInButFailedGetGeniUserError:
    return _show_failed_get_geniuser_page(request)

  # The request must be via POST. If not, bounce user back to My Vessels page.
  if not request.method == 'POST':
    return myvessels(request)

  if not request.POST.get('handle', ''):
    return myvessels(request)

  action_summary = ""
  action_detail = ""

  try:
    # Convert handle to vessel object.
    # Raises a DoesNotExistError if the vessel does not exist. This is more
    # likely to be an error than an expected case, so we let it bubble up.
    vessel_handle_list = [request.POST['handle']]
    vessel_to_renew = interface.get_vessel_list(vessel_handle_list)
  except DoesNotExistError:
    action_summary = "Unable to renew vessel: The vessel you are trying to delete does not exist."
  except InvalidRequestError, err:
    action_summary = "Unable to renew vessel."
    action_detail += str(err)
  else:
    try:
      interface.renew_vessels(user, vessel_to_renew)
    except InvalidRequestError, err:
      action_summary = "Unable to renew vessel: " + str(err)
    except InsufficientUserResourcesError, err:
      action_summary = "Unable to renew vessel: you are currently over your"
      action_summary += " vessel credit limit."
      action_detail += str(err)

  return myvessels(request, False, action_summary=action_summary, action_detail=action_detail)





@login_required
def renew_all_resources(request):
  try:
    user = _validate_and_get_geniuser(request)
  except LoggedInButFailedGetGeniUserError:
    return _show_failed_get_geniuser_page(request)

  # The request must be via POST. If not, bounce user back to My Vessels page.
  if not request.method == 'POST':
    return myvessels(request)

  action_summary = ""
  action_detail = ""

  try:
    interface.renew_all_vessels(user)
  except InvalidRequestError, err:
    action_summary = "Unable to renew vessels: " + str(err)
  except InsufficientUserResourcesError, err:
    action_summary = "Unable to renew vessels: you are currently over your"
    action_summary += " vessel credit limit."
    action_detail += str(err)

  return myvessels(request, False, action_summary=action_summary, action_detail=action_detail)





@login_required
def change_key(request):
  try:
    user = _validate_and_get_geniuser(request)
  except LoggedInButFailedGetGeniUserError:
    return _show_failed_get_geniuser_page(request)
  info = ""
  if request.method == 'GET':
    return render_to_response('control/change_key.html',
                              {'username' : user.username,
                               'error_msg' : ""},
                              context_instance=RequestContext(request))

  # This is a POST, so figure out if a file was uploaded or if we are supposed
  # to generate a new key for the user.
  if request.POST.get('generate', False):
    interface.change_user_keys(user, pubkey=None)
    msg = "Your new keys have been generated. You should download them now."
    return profile(request, msg)

  else:
    file = request.FILES.get('pubkey', None)
    if file is None:
      msg = "You didn't select a public key file to upload."
      return profile(request, info, msg)


    if file.size == 0 or file.size > forms.MAX_PUBKEY_UPLOAD_SIZE:
      msg = "Invalid file uploaded. The file size limit is "
      msg += str(forms.MAX_PUBKEY_UPLOAD_SIZE) + " bytes."
      return profile(request, info, msg)

    pubkey = file.read()

    try:
      validations.validate_pubkey_string(pubkey)
    except ValidationError:
      msg = "Invalid public key uploaded."
      return profile(request, info, msg)

    # If we made it here, the uploaded key is good.
    interface.change_user_keys(user, pubkey=pubkey)
    msg = "Your public key has been successfully changed."
    return profile(request, msg)





@login_required
def api_info(request):
  try:
    user = _validate_and_get_geniuser(request)
  except LoggedInButFailedGetGeniUserError:
    return _show_failed_get_geniuser_page(request)

  if request.method == 'GET':
    return render_to_response('control/api_info.html',
                              {'username' : user.username,
                               'api_key' : user.api_key,
                               'msg' : ""},
                              context_instance=RequestContext(request))

  # This is a POST, so it should be generation of an API key.
  if not request.POST.get('generate_api_key', False):
    msg = "Sorry, we didn't understand your request."
    return profile(request, info, msg)

  interface.regenerate_api_key(user)
  msg = "Your API key has been regenerated. Your old one will no longer work."
  msg += " You should update any places you are using the API key"
  msg += " (e.g. in programs using the XML-RPC client)."
  return profile(request,msg)





@log_function_call
@require_POST
@login_required
def del_priv(request):
  try:
    user = _validate_and_get_geniuser(request)
  except LoggedInButFailedGetGeniUserError:
    return _show_failed_get_geniuser_page(request)

  if user.user_privkey == "":
    msg = "Your private key has already been deleted."
  else:
    interface.delete_private_key(user)
    msg = "Your private key has been deleted."
  return profile(request, msg)





@log_function_call
@login_required
def priv_key(request):
  try:
    user = _validate_and_get_geniuser(request)
  except LoggedInButFailedGetGeniUserError:
    return _show_failed_get_geniuser_page(request)

  response = HttpResponse(user.user_privkey, content_type='text/plain')
  response['Content-Disposition'] = 'attachment; filename=' + \
          str(user.username) + '.privatekey'
  return response





@log_function_call
@login_required
def pub_key(request):
  try:
    user = _validate_and_get_geniuser(request)
  except LoggedInButFailedGetGeniUserError:
    return _show_failed_get_geniuser_page(request)

  response = HttpResponse(user.user_pubkey, content_type='text/plain')
  response['Content-Disposition'] = 'attachment; filename=' + \
            str(user.username) + '.publickey'
  return response





def download(request, username):
  validuser = True
  try:
    # validate that this username actually exists
    user = interface.get_user_for_installers(username)
  except DoesNotExistError:
    validuser = False

  templatedict = {}
  templatedict['username'] = username
  templatedict['validuser'] = validuser
  templatedict['domain'] = "https://" + request.get_host()
  # I need to build a URL for android to download the installer from.   (The
  # same installer is downloaded from the Google Play store for all users.)
  # The URL is escaped twice (ask Akos why) and inserted in the referrer
  # information in the URL.
  #templatedict['android_installer_link'] = urllib.quote(urllib.quote(domain,safe=''),safe='')

  return render_to_response('download/installers.html', templatedict,
          context_instance=RequestContext(request))





def build_android_installer(request, username):
  """
  <Purpose>
    Allows the user to download a Android distribution of Seattle that will
    donate resources to user with 'username'.

  <Arguments>
    request:
      Django HttpRequest object

    username:
      A string representing the GENI user to which the installer will donate
      resources.

  <Exceptions>
    None

  <Side Effects>
    None

  <Returns>
    On failure, returns an HTTP response with a description of the error. On
    success, redirects the user to download the installer.
  """

  success, return_value = _build_installer(username, "android")

  if not success:
    error_response = return_value
    return error_response

  installer_url = return_value
  return installer_url





def build_win_installer(request, username):
  """
  <Purpose>
    Allows the user to download a Windows distribution of Seattle that will
    donate resources to user with 'username'.

  <Arguments>
    request:
      Django HttpRequest object

    username:
      A string representing the GENI user to which the installer will donate
      resources.

  <Exceptions>
    None

  <Side Effects>
    None

  <Returns>
    On failure, returns an HTTP response with a description of the error. On
    success, redirects the user to download the installer.
  """

  success, return_value = _build_installer(username, "windows")

  if not success:
    error_response = return_value
    return error_response

  installer_url = return_value
  return HttpResponseRedirect(installer_url)





def build_linux_installer(request, username):
  """
  <Purpose>
    Allows the user to download a Linux distribution of Seattle that will
    donate resources to user with 'username'.

  <Arguments>
    request:
      Django HttpRequest object

    username:
      A string representing the GENI user to which the installer will donate
      resources.

  <Exceptions>
    None

  <Side Effects>
    None

  <Returns>
    On failure, returns an HTTP response with a description of the error. On
    success, redirects the user to download the installer.
  """

  success, return_value = _build_installer(username, "linux")

  if not success:
    error_response = return_value
    return error_response

  installer_url = return_value
  return HttpResponseRedirect(installer_url)





def build_mac_installer(request, username):
  """
  <Purpose>
    Allows the user to download a Mac distribution of Seattle that will
    donate resources to user with 'username'.

  <Arguments>
    request:
      Django HttpRequest object

    username:
      A string representing the GENI user to which the installer will donate
      resources.

  <Exceptions>
    None

  <Side Effects>
    None

  <Returns>
    On failure, returns an HTTP response with a description of the error. On
    success, redirects the user to download the installer.
  """

  success, return_value = _build_installer(username, "mac")

  if not success:
    error_response = return_value
    return error_response

  installer_url = return_value
  return HttpResponseRedirect(installer_url)




@login_required
def registerexperiment(request):
  """
  <Purpose>
      Show the Experiment Registration Form
  <Returns>
      An HTTP response object that represents the experiment registration page on
      success.
  """
  # Obtain the context from the HTTP request.

  context_instance = RequestContext(request)

  # Since several Classes (battery, bluetooth, location, settings etc.)
  # inherit from the abstract class Sensor, in order to print with a loop
  # first the vars from each class and then those from the Sensor one, we
  # will need to store the name of all Sensor vars to later compare them
  # with the others and print them in the order we want
  sensor_instance = Sensor()
  sensor_var_names = vars(sensor_instance)

  # One of the Sensor's vars is "experiment_id" but apparently, there appears
  # another var called "experiment_id_id" instead, so we get rid of this and
  # insert the name of the other one manually.
  if "experiment_id_id" in sensor_var_names:
    del sensor_var_names["experiment_id_id"]
    sensor_var_names["experiment_id"] = None

  try:
    user = _validate_and_get_geniuser(request)
  except LoggedInButFailedGetGeniUserError:
    return _show_failed_get_geniuser_page(request)

  page_top_errors = []
  username = user.username
  ret =['testA'] #test list

  if request.method == 'POST':
    # create a form instance and populate it with data from the request:
    r_form = forms.RegisterExperimentForm(request.POST) #global data form
    details_form = forms.DetailsForm(request.POST, prefix = 'details')
    battery_form = forms.BatteryForm(request.POST, prefix = 'battery')
    bluetooth_form = forms.BluetoothForm(request.POST, prefix = 'bluetooth')
    cellular_form = forms.CellularForm(request.POST, prefix = 'cellular')
    location_form = forms.LocationForm(request.POST, prefix = 'location')
    settings_form = forms.SettingsForm(request.POST, prefix = 'settings')
    sensor_form = forms.SensorForm(request.POST, prefix = 'sensor')
    signalstrength_form = forms.SignalStrengthForm(request.POST, prefix = 'signalstrength')
    wifi_form = forms.WifiForm(request.POST, prefix = 'wifi')

    if r_form.is_valid(): #if r_form is valid save the data
      ret.append("valid1")
      geni_user = user #foreign key of the experiment
      experiment_name = r_form.cleaned_data['expe_name']
      researcher_name = r_form.cleaned_data['researcher_name']
      researcher_address = r_form.cleaned_data['researcher_address']
      researcher_email = r_form.cleaned_data['researcher_email']
      irb = r_form.cleaned_data['researcher_institution_name']
      irb_email = r_form.cleaned_data['irb_officer_email']
      goal = r_form.cleaned_data['goal']
      if r_form.is_required('terms_of_use') == False:
        page_top_errors.append("Please accept the terms of use")

      try:
        # we should never error here, since we've already finished validation at this point.
        # but, just to be safe...
        experiment = interface.register_experiment(geni_user,experiment_name,
                                          researcher_name,researcher_address,
                                          researcher_email,irb, irb_email, goal)
      except ValidationError, err:
        page_top_errors.append(str(err))

      else:
        #Evreything went good so far and
        #now we have to check every sensor form.
        if battery_form.is_valid():
          if battery_form.is_required('battery'):#check if the researcher wants to use this sensor
            #check sensor checkboxes
            if_battery_present = battery_form.is_required('if_battery_present')
            battery_health = battery_form.is_required('battery_health')
            battery_level = battery_form.is_required('battery_level')
            battery_plug_type = battery_form.is_required('battery_plug_type')
            battery_status = battery_form.is_required('battery_status')
            battery_technology = battery_form.is_required('battery_technology')
            #check general sensor atributes
            battery_frequency = battery_form.cleaned_data['frequency']
            battery_frequency_unit = battery_form.cleaned_data['frequency_unit']
            battery_frequency_other = battery_form.cleaned_data['frequency_other']
            battery_precision = battery_form.cleaned_data['precision']
            battery_truncation = battery_form.cleaned_data['truncation']
            battery_precision_other = battery_form.cleaned_data['precision_other']
            battery_goal = battery_form.cleaned_data['goal']
        
            if battery_frequency == None: #if the user doesnt set frequency
              battery_frequency = 0 #we set it to 0
              if battery_frequency_other == '':#if he doesnt provide any other informatio either
                page_top_errors.append("Please select the frequency in the battery sensor")#We set an error

            if battery_truncation == None:
              if  battery_precision == 'truncate':
                page_top_errors.append("Please select the truncation decimals in the battery sensor")
              else:
                battery_truncation = 0

            if battery_goal == '':
              page_top_errors.append("Please explain the goal of using the battery sensor")

            if if_battery_present == False and battery_health == False and \
                battery_level == False and battery_plug_type == False and \
                battery_status == False and battery_technology == False:
              page_top_errors.append("Please select any battery attribute")

            if page_top_errors == []:
              try:
                battery = interface.register_sensor('battery',experiment,battery_frequency,
                                            battery_frequency_unit,battery_frequency_other,
                                            battery_precision,battery_truncation, battery_precision_other,
                                            battery_goal,[if_battery_present,battery_health,battery_level,
                                            battery_plug_type,battery_status,battery_technology])
              except ValidationError, err:
                page_top_errors.append(str(err))

        else:#when battery form is not valid
          page_top_errors.append("Battery form is not valid")

        if bluetooth_form.is_valid():#save data into bluetooth model
          if bluetooth_form.is_required('bluetooth'):#check if the researcher wants to use this sensor
            #check sensor checkboxes
            bluetooth_state = bluetooth_form.is_required('bluetooth_state')
            bluetooth_is_discovering = bluetooth_form.is_required('bluetooth_is_discovering')
            scan_mode = bluetooth_form.is_required('scan_mode')
            local_address = bluetooth_form.is_required('local_address')
            local_name = bluetooth_form.is_required('local_name')
            #check general sensor atributes
            bluetooth_frequency = bluetooth_form.cleaned_data['frequency']
            bluetooth_frequency_unit = bluetooth_form.cleaned_data['frequency_unit']
            bluetooth_frequency_other = bluetooth_form.cleaned_data['frequency_other']
            bluetooth_precision = bluetooth_form.cleaned_data['precision']
            bluetooth_truncation = bluetooth_form.cleaned_data['truncation']
            bluetooth_precision_other = bluetooth_form.cleaned_data['precision_other']
            bluetooth_goal = bluetooth_form.cleaned_data['goal']

            if bluetooth_frequency == None:
              bluetooth_frequency = 0
              if bluetooth_frequency_other == '':
                page_top_errors.append("Please select the frequency in the bluetooth sensor")

            if bluetooth_precision == 'truncate'and bluetooth_truncation == None:
              page_top_errors.append("Please select the truncation decimals in the bluetooth sensor")

            if bluetooth_goal == '':
              page_top_errors.append("Please explain the goal of using the bluetooth sensor")

            if bluetooth_state == False and bluetooth_is_discovering == False and \
                scan_mode == False and local_address == False and \
                local_name == False:
              page_top_errors.append("Please select any bluetooth attribute")

            if page_top_errors == []:
              try:
                bluetooth = interface.register_sensor('bluetooth',experiment,bluetooth_frequency,
                                            bluetooth_frequency_unit,bluetooth_frequency_other,
                                            bluetooth_precision,bluetooth_truncation, bluetooth_precision_other,
                                            bluetooth_goal,[bluetooth_state,bluetooth_is_discovering,scan_mode,
                                            local_address,local_name])
              except ValidationError, err:
                page_top_errors.append(str(err))

        else:#when bluetooth form is not valid
          page_top_errors.append("Bluetooth form is not valid")

        if cellular_form.is_valid():#save data into cellular model
          if cellular_form.is_required('cellular'):#check if the researcher wants to use this sensor
            #check sensor checkboxes
            network_roaming = cellular_form.is_required('network_roaming')
            cellID = cellular_form.is_required('cellID')
            location_area_code = cellular_form.is_required('location_area_code')
            mobile_country_code = cellular_form.is_required('mobile_country_code')
            mobile_network_code = cellular_form.is_required('mobile_network_code')
            network_operator = cellular_form.is_required('network_operator')
            network_operator_name = cellular_form.is_required('network_operator_name')
            network_type = cellular_form.is_required('network_type')
            service_state = cellular_form.is_required('service_state')
            signal_strengths = cellular_form.is_required('signal_strengths')
            #check general sensor atributes
            cellular_frequency = cellular_form.cleaned_data['frequency']
            cellular_frequency_unit = cellular_form.cleaned_data['frequency_unit']
            cellular_frequency_other = cellular_form.cleaned_data['frequency_other']
            cellular_precision = cellular_form.cleaned_data['precision']
            cellular_truncation = cellular_form.cleaned_data['truncation']
            cellular_precision_other = cellular_form.cleaned_data['precision_other']
            cellular_goal = cellular_form.cleaned_data['goal']

            if cellular_frequency == None:
              cellular_frequency = 0
              if cellular_frequency_other == '':
                page_top_errors.append("Please select the frequency in the cellular sensor")

            if cellular_precision == 'truncate'and cellular_truncation == None:
              page_top_errors.append("Please select the truncation decimals in the cellular sensor")

            if cellular_goal == '':
              page_top_errors.append("Please explain the goal of using the cellular sensor")

            if network_roaming == False and cellID == False and \
                location_area_code == False and mobile_country_code == False and \
                mobile_network_code == False and network_operator == False and \
                network_operator_name == False and network_type == False and \
                service_state == False and signal_strengths == False:
              page_top_errors.append("Please select any cellular attribute")

            if page_top_errors == []:
              try:
                cellular = interface.register_sensor('cellular',experiment,cellular_frequency,
                                            cellular_frequency_unit,cellular_frequency_other,
                                            cellular_precision,cellular_truncation, cellular_precision_other,
                                            cellular_goal,[network_roaming,cellID,location_area_code,
                                            mobile_country_code,mobile_network_code,network_operator,
                                            network_operator_name, network_type,service_state,signal_strengths])
              except ValidationError, err:
                page_top_errors.append(str(err))

        else:#when cellular form is not valid
          page_top_errors.append("Cellular form is not valid")

        if location_form.is_valid():#save data into location model
          if location_form.is_required('location'):#check if the researcher wants to use this sensor
            #check sensor checkboxes
            location_providers = location_form.is_required('location_providers')
            location_provider_enabled = location_form.is_required('location_provider_enabled')
            location_data = location_form.is_required('location_data')
            last_known_location = location_form.is_required('last_known_location')
            geocode = location_form.is_required('geocode')
            #check general sensor atributes
            location_frequency = location_form.cleaned_data['frequency']
            location_frequency_unit = location_form.cleaned_data['frequency_unit']
            location_frequency_other = location_form.cleaned_data['frequency_other']
            location_precision = location_form.cleaned_data['precision']
            location_truncation = location_form.cleaned_data['truncation']
            location_precision_other = location_form.cleaned_data['precision_other']
            location_goal = location_form.cleaned_data['goal']

            if location_frequency == None:
              location_frequency = 0
              if location_frequency_other == '':
                page_top_errors.append("Please select the frequency in the location sensor")

            if location_precision == 'truncate'and location_truncation == None:
              page_top_errors.append("Please select the truncation decimals in the location sensor")

            if location_goal == '':
              page_top_errors.append("Please explain the goal of using the location sensor")

            if location_providers == False and location_provider_enabled == False and \
                location_data == False and last_known_location == False and \
                geocode == False:
              page_top_errors.append("Please select any location attribute")

            if page_top_errors == []:
              try:
                location = interface.register_sensor('location',experiment,location_frequency,
                                            location_frequency_unit,location_frequency_other,
                                            location_precision,location_truncation, location_precision_other,
                                            location_goal,[location_providers,location_provider_enabled,
                                            location_data,last_known_location,geocode])
              except ValidationError, err:
                page_top_errors.append(str(err))

        else:#when location form is not valid
          page_top_errors.append("Location form is not valid")

        if settings_form.is_valid():#save data into settings model
          if settings_form.is_required('settings'):#check if the researcher wants to use this sensor
            #check sensor checkboxes
            airplane_mode = settings_form.is_required('airplane_mode')
            ringer_silent_mode = settings_form.is_required('ringer_silent_mode')
            screen_on = settings_form.is_required('screen_on')
            max_media_volume = settings_form.is_required('max_media_volume')
            max_ringer_volume = settings_form.is_required('max_ringer_volume')
            media_volume = settings_form.is_required('media_volume')
            ringer_volume = settings_form.is_required('ringer_volume')
            screen_brightness = settings_form.is_required('screen_brightness')
            screen_timeout = settings_form.is_required('screen_timeout')
            #check general sensor atributes
            settings_frequency = settings_form.cleaned_data['frequency']
            settings_frequency_unit = settings_form.cleaned_data['frequency_unit']
            settings_frequency_other = settings_form.cleaned_data['frequency_other']
            settings_precision = settings_form.cleaned_data['precision']
            settings_truncation = settings_form.cleaned_data['truncation']
            settings_precision_other = settings_form.cleaned_data['precision_other']
            settings_goal = settings_form.cleaned_data['goal']

            if settings_frequency == None:
              settings_frequency = 0
              if settings_frequency_other == '':
                page_top_errors.append("Please select the frequency in the settings sensor")

            if settings_precision == 'truncate'and settings_truncation == None:
              page_top_errors.append("Please select the truncation decimals in the settings sensor")

            if settings_goal == '':
              page_top_errors.append("Please explain the goal of using the settings sensor")

            if airplane_mode == False and ringer_silent_mode == False and \
                screen_on == False and max_media_volume == False and \
                max_ringer_volume == False and media_volume == False and \
                ringer_volume == False and screen_brightness == False and \
                screen_timeout == False:
              page_top_errors.append("Please select any settings attribute")

            if page_top_errors == []:
              try:
                settings = interface.register_sensor('settings',experiment,settings_frequency,
                                            settings_frequency_unit,settings_frequency_other,
                                            settings_precision,settings_truncation, settings_precision_other,
                                            settings_goal,[airplane_mode,ringer_silent_mode,screen_on,
                                            max_media_volume,max_ringer_volume,media_volume,ringer_volume,
                                            screen_brightness,screen_timeout])
              except ValidationError, err:
                page_top_errors.append(str(err))

        else:#when settings form is not valid
          page_top_errors.append("Settings form is not valid")

        if sensor_form.is_valid():#save data into sensor model
          if sensor_form.is_required('sensor'):#check if the researcher wants to use this sensor
            #check sensor checkboxes
            sensor_data = sensor_form.is_required('sensor_data')
            sensors_accuracy = sensor_form.is_required('sensors_accuracy')
            light = sensor_form.is_required('light')
            accelerometer = sensor_form.is_required('accelerometer')
            magnetometer = sensor_form.is_required('magnetometer')
            orientation = sensor_form.is_required('orientation') 
            #check general sensor atributes
            sensor_frequency = sensor_form.cleaned_data['frequency']
            sensor_frequency_unit = sensor_form.cleaned_data['frequency_unit']
            sensor_frequency_other = sensor_form.cleaned_data['frequency_other']
            sensor_precision = sensor_form.cleaned_data['precision']
            sensor_truncation = sensor_form.cleaned_data['truncation']
            sensor_precision_other = sensor_form.cleaned_data['precision_other']
            sensor_goal = sensor_form.cleaned_data['goal']

            if sensor_frequency == None:
              sensor_frequency = 0
              if sensor_frequency_other == '':
                page_top_errors.append("Please select the frequency in the sensor sensor")

            if sensor_precision == 'truncate'and sensor_truncation == None:
              page_top_errors.append("Please select the truncation decimals in the sensor sensor")

            if sensor_goal == '':
              page_top_errors.append("Please explain the goal of using the sensor sensor")

            if sensor_data == False and sensors_accuracy == False and \
                light == False and accelerometer == False and \
                magnetometer == False and orientation == False:
              page_top_errors.append("Please select any sensor attribute")

            if page_top_errors == []:
              try:
                sensor = interface.register_sensor('sensor',experiment,sensor_frequency,
                                            sensor_frequency_unit, sensor_frequency_other,
                                            sensor_precision,sensor_truncation, sensor_precision_other,
                                            sensor_goal,[sensor_data,sensors_accuracy,light,
                                            accelerometer,magnetometer,orientation])
              except ValidationError, err:
                page_top_errors.append(str(err))

        else:#when concret sensor form is not valid
          page_top_errors.append("Sensor form is not valid")

        if signalstrength_form.is_valid():#save data into signalstrenght model
          if signalstrength_form.is_required('signalstrength'):#check if the researcher wants to use this sensor
            #check sensor checkboxes
            signal_strengths = signalstrength_form.is_required('signal_strengths')
            #check general sensor atributes
            signalstrength_frequency = signalstrength_form.cleaned_data['frequency']
            signalstrength_frequency_unit = signalstrength_form.cleaned_data['frequency_unit']
            signalstrength_frequency_other = signalstrength_form.cleaned_data['frequency_other']
            signalstrength_precision = signalstrength_form.cleaned_data['precision']
            signalstrength_truncation = signalstrength_form.cleaned_data['truncation']
            signalstrength_precision_other = signalstrength_form.cleaned_data['precision_other']
            signalstrength_goal = signalstrength_form.cleaned_data['goal']

            if signalstrength_frequency == None:
              signalstrength_frequency = 0
              if signalstrength_frequency_other == '':
                page_top_errors.append("Please select the frequency in the signalstrength sensor")

            if signalstrength_precision == 'truncate'and signalstrength_truncation == None:
              page_top_errors.append("Please select the truncation decimals in the signalstrength sensor")

            if signalstrength_goal == '':
              page_top_errors.append("Please explain the goal of using the signalstrength sensor")

            if signal_strengths == False:
              page_top_errors.append("Please select any signalstrength attribute")

            if page_top_errors == []:
              try:
                signalstrength = interface.register_sensor('signalstrength',experiment,signalstrength_frequency,
                                            signalstrength_frequency_unit,signalstrength_frequency_other,
                                            signalstrength_precision,signalstrength_truncation, signalstrength_precision_other,
                                            signalstrength_goal,[signal_strengths])
              except ValidationError, err:
                page_top_errors.append(str(err))

        else:#when signalstrength form is not valid
          page_top_errors.append("Signalstrength form is not valid")

        if wifi_form.is_valid():#save data into wifi model
          if wifi_form.is_required('wifi'):#check if the researcher wants to use this sensor
            #check sensor checkboxes
            wifi_state = wifi_form.is_required('wifi_state')
            ip_address = wifi_form.is_required('ip_address')
            link_speed = wifi_form.is_required('link_speed')
            supplicant_state = wifi_form.is_required('supplicant_state')
            ssid = wifi_form.is_required('ssid')
            rssi = wifi_form.is_required('rssi')
            scan_results = wifi_form.is_required('scan_results')
            #check general sensor atributes
            wifi_frequency = wifi_form.cleaned_data['frequency']
            wifi_frequency_unit = wifi_form.cleaned_data['frequency_unit']
            wifi_frequency_other = wifi_form.cleaned_data['frequency_other']
            wifi_precision = wifi_form.cleaned_data['precision']
            wifi_truncation = wifi_form.cleaned_data['truncation']
            wifi_precision_other = wifi_form.cleaned_data['precision_other']
            wifi_goal = wifi_form.cleaned_data['goal']

            if wifi_frequency == None:
              wifi_frequency = 0
              if wifi_frequency_other == '':
                page_top_errors.append("Please select the frequency in the wifi sensor")

            if wifi_precision == 'truncate'and wifi_truncation == None:
              page_top_errors.append("Please select the truncation decimals in the wifi sensor")

            if wifi_goal == '':
              page_top_errors.append("Please explain the goal of using the wifi sensor")

            if wifi_state == False and ip_address == False and \
                link_speed == False and supplicant_state == False and \
                ssid == False and rssi == False:
              page_top_errors.append("Please select any wifi attribute")

            if page_top_errors == []:
              try:
                wifi = interface.register_sensor('wifi',experiment,wifi_frequency,
                                            wifi_frequency_unit,wifi_frequency_other,
                                            wifi_precision,wifi_truncation, wifi_precision_other,
                                            wifi_goal,[wifi_state,ip_address,link_speed,
                                            supplicant_state,ssid,rssi,scan_results])
              except ValidationError, err:
                page_top_errors.append(str(err))

        else:#when bluetooth wifi is not valid
          page_top_errors.append("Wifi form is not valid")

        if page_top_errors == []: #all data have been saved succesfully
          #redirect to the help page just as a test
          return HttpResponseRedirect(reverse("viewexperiments")) 
              
    else: #if r_form is not valid
      page_top_errors.append("Basic information of the experiment is not valid")
   
  # if a GET (or any other method) we'll create a blank form
  else:
      r_form = forms.RegisterExperimentForm()
      details_form = forms.DetailsForm(prefix='details')
      battery_form = forms.BatteryForm(prefix = 'battery') #form for each sensor
      bluetooth_form = forms.BluetoothForm(prefix = 'bluetooth') #form for each sensor
      cellular_form = forms.CellularForm(prefix = 'cellular') #form for each sensor
      location_form = forms.LocationForm(prefix = 'location') #form for each sensor
      settings_form = forms.SettingsForm(prefix = 'settings') #form for each sensor
      sensor_form = forms.SensorForm(prefix = 'sensor') #form for each sensor
      signalstrength_form = forms.SignalStrengthForm(prefix = 'signalstrength') #form for each sensor
      wifi_form = forms.WifiForm(prefix = 'wifi') #form for each sensor

  values_to_render = {
    'username' : username,
    'battery_form': battery_form,
    'bluetooth_form': bluetooth_form,
    'cellular_form': cellular_form,
    'location_form': location_form,
    'settings_form': settings_form,
    'sensor_form': sensor_form,
    'signalstrength_form': signalstrength_form,
    'wifi_form': wifi_form,
    'r_form': r_form,
    'details_form': details_form,
    'ret': ret,
    'page_top_errors': page_top_errors,
    'sensor_var_names': sensor_var_names,
  }

  return render(request, 'control/registerexperiment.html', values_to_render)




@login_required
def viewexperiments(request):
  """
  <Purpose>
      Show the Experiments Registrated 
  <Returns>
     Experimenr objects
  """
  # Obtain the context from the HTTP request.

  context_instance = RequestContext(request)

  try:
    user = _validate_and_get_geniuser(request)
  except LoggedInButFailedGetGeniUserError:
    return _show_failed_get_geniuser_page(request)


  page_top_errors = []
  username = user.username
  ret = [] #returning list
  user_experiments = Experiment.objects.filter(geni_user=user)
  for experiment in reversed(user_experiments):
    #reversed so the oldest experiment is the last we show.
    experiment_sensors = []
    name_list = []
    experiment_sensors.extend(list(Battery.objects.filter(experiment_id=experiment)))
    experiment_sensors.extend(list(Bluetooth.objects.filter(experiment_id=experiment)))
    experiment_sensors.extend(list(Cellular.objects.filter(experiment_id=experiment)))
    experiment_sensors.extend(list(Settings.objects.filter(experiment_id=experiment)))
    experiment_sensors.extend(list(ConcretSensor.objects.filter(experiment_id=experiment)))
    experiment_sensors.extend(list(Location.objects.filter(experiment_id=experiment)))
    experiment_sensors.extend(list(Signal_strengths.objects.filter(experiment_id=experiment)))
    experiment_sensors.extend(list(Wifi.objects.filter(experiment_id=experiment)))

    for sensor in experiment_sensors:
      name_list.append(sensor.show_name())

    if name_list == []:
      name_list = "None"

    ret.append([experiment.expe_name,name_list,experiment.id])
    
    
  
  return render(request, 'control/viewexperiments.html', {'username' : username, 
            'page_top_errors' : page_top_errors, 'ret':ret})


def delete_experiment(request, exp_id):
  experiment_to_delete = Experiment.objects.filter(id=exp_id)
  experiment_to_delete.delete()
  return redirect("viewexperiments")


@login_required
def viewdonations(request):
  """
  <Purpose>
      Show the Experiments Registrated 
  <Returns>
     Experimenr objects
  """
  # Obtain the context from the HTTP request.

  context_instance = RequestContext(request)

  try:
    user = _validate_and_get_geniuser(request)
  except LoggedInButFailedGetGeniUserError:
    return _show_failed_get_geniuser_page(request)


  username = user.username
  my_donations = interface.get_donations(user)
  lent = "AA"

  return render(request, 'control/viewdonations.html', {'username' : username, 
            'my_donations' : my_donations, 'lent' : lent})




def _build_installer(username, platform):
  """
  <Purpose>
    Builds an installer for the given platform that will donate resources to
    the user with the given username.

  <Arguments>
    username:
      A string representing the GENI user to which the installer will donate
      resources.

    platform:
      A string representing the platform for which to build the installer.
      Options include 'windows', 'linux', or 'mac'.

  <Exceptions>
    None

  <Side Effects>
    None

  <Returns>
    On success, returns (True, installer_url) where installer_url is URL from
    which the installer may be downloaded.

    On failure, returns (False, error_response) where error_repsponse is an
    HttpResponse which specifies what went wrong.
  """
  try:
    user = interface.get_user_for_installers(username)
    username = user.username
  except DoesNotExistError:
    error_response = HttpResponse("Couldn't get user.")
    return False, error_response

  try:
    xmlrpc_proxy = xmlrpclib.ServerProxy(settings.SEATTLECLEARINGHOUSE_INSTALLER_BUILDER_XMLRPC)

    vessel_list = [{'percentage': 80, 'owner': 'owner', 'users': ['user']}]

    user_data = {
      'owner': {'public_key': user.donor_pubkey},
      'user': {'public_key': ACCEPTDONATIONS_STATE_PUBKEY},
    }

    build_results = xmlrpc_proxy.build_installers(vessel_list, user_data)
  except:
    error_response = HttpResponse("Failed to build installer.")
    return False, error_response

  installer_url = build_results['installers'][platform]
  return True, installer_url

def download_installers_page(request, build_id):
  """
  <Purpose>
    Renders the installer package download page.
  <Arguments>
    request:
      A Django request.
    build_id:
      The build ID of the results to display.
  <Exceptions>
    None.
  <Side Effects>
    None.
  <Returns>
    A Django response.
  """

  manager = BuildManager(build_id=build_id)

  # Invalid build IDs should results in an error.
  if not os.path.isdir(manager.get_build_directory()):
    raise Http404
    
  # Compile the list of links of where to find the installers and cryptographic
  # key archives.
  installer_links = manager.get_urls()
    
  # If there is a query string appended to the current URL, we don't want that
  # in the share-this-URL box.
  share_url = request.build_absolute_uri().split('?')[0]
  
  # Only show the progress bar if the user has built this installer himself.
  # Otherwise, we assume the user has shared this link with a friend.
  step = None
  user_built = False
  
  if 'build_results' in request.session:
    if build_id in request.session['build_results']:
      step = 'installers'
      user_built = True

      # If we serve a fast_lane_build we don't show the breadcrumbs
      if 'fast_lane_build' in request.session['build_results'][build_id]:
        step = False

  return render(request, 'get_donations.html',
      {
        'build_id': build_id,
        'installers': installer_links,
        'share_url': share_url,
        'step': step,
        'user_built': user_built,
      })





def donations_help(request, username):
  return render_to_response('download/help.html', {'username' : username},
          context_instance=RequestContext(request))





def _validate_and_get_geniuser(request):
  try:
    user = interface.get_logged_in_user(request)
  except DoesNotExistError:
    # Failed to get GeniUser record, but user is logged in
    raise LoggedInButFailedGetGeniUserError
  return user





@log_function_call_without_return
@login_required
def new_auto_register_user(request):
  msg = "Your account has been succesfully created. "
  msg += "If you would like to login without OpenID/OAuth please change your password now."
  return profile(request,msg)





def _show_failed_get_geniuser_page(request):
  err = "Sorry, we can't display the page you requested. "
  err += "If you are logged in as an administrator, you'll need to logout, and login with a Seattle Clearinghouse account. "
  err += "If you aren't logged in as an administrator, then this is a bug. Please contact us!"
  return _show_login(request, 'accounts/login.html', {'err' : err})