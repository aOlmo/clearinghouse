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

from django.http import HttpResponse
from django.http import HttpResponseRedirect
from django.contrib.auth.forms import AuthenticationForm
from django.contrib.auth.decorators import login_required
from django.core.urlresolvers import reverse
from django.views.generic.simple import direct_to_template
import django.contrib.auth as djangoauth

# Make available all of our own standard exceptions.
from seattlegeni.common.exceptions import *

# This is the logging decorator use use.
from seattlegeni.common.util.decorators import log_function_call
from seattlegeni.common.util.decorators import log_function_call_without_return

# For user registration input validation
from seattlegeni.common.util import validations

# All of the work that needs to be done is passed through the controller interface.
from seattlegeni.website.control import interface

from seattlegeni.website.html import forms


@log_function_call_without_return
@login_required()
def profile(request, info=""):
  """
  <Purpose>
    Display information about the user account.
    This method requires the request to represent a valid logged
    in user. See the top-level comment about the @login_required()
    decorator to achieve this property.
  <Arguments>
    request:
      An HTTP request object.  
    info:
      Additional message to display at the top of the page.
  <Exceptions>
    TODO
  <Side Effects>
    None.
  <Returns>
    An HTTP response object that represents the user info
    page on success. A redirect to a login page on error.
  """
  
  # If the user's session has expired, show them an appropriate page.
  # Note that if @login_required is being used, this might not be
  # possible, but we should at least check it and raise an exception
  # if we dont' think it's possible.
  
  try:
    user = interface.get_logged_in_user(request)
  except DoesNotExistError:
    return _show_login(request, 'accounts/login.html', {})
  return direct_to_template(request, 'control/profile.html',
                            {'geni_user' : user,
                             'info' : info})


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
    form = forms.GeniUserCreationForm(request.POST, request.FILES)
    
    # Calling the form's is_valid() function causes all form "clean_..." methods to be checked.
    # If this succeeds, then the form input data is validated per field-specific cleaning checks. (see forms.py)
    # However, we still need to do some checks which aren't doable from inside the form class.
    if form.is_valid():
      username = form.cleaned_data['username']
      password = form.cleaned_data['password1']
      passwordconfirm = form.cleaned_data['password2']
      affiliation = form.cleaned_data['affiliation']
      email = form.cleaned_data['email']
      pubkey = form.cleaned_data['pubkey']
      
      try:
        validations.validate_username_and_password_different(form.cleaned_data['username'], form.cleaned_data['password1'])
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
          geniuser = interface.register_user(username, password, email, affiliation, pubkey)
        except ValidationError, err:
          page_top_errors.append(str(err))
        else:
          return _show_login(request, 'accounts/login.html',
                             {'msg' : "Username %s has been successfully registered." % (geniuser)})
  else:
    form = forms.GeniUserCreationForm()
  return direct_to_template(request, 'accounts/register.html', {'form' : form, 'page_top_errors' : page_top_errors })
  



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
    return direct_to_template(request, ltemplate, template_dict)
  
  

def login(request):
  
  ltemplate = 'accounts/login.html'
  if request.method == 'POST':
    form = AuthenticationForm(request.POST)
    
    if not request.session.test_cookie_worked():
      request.session.set_test_cookie()
      return _show_login(request, ltemplate, {'err' : "Please enable your cookies and try again."}, form)

    if request.POST.has_key('jsenabled') and request.POST['jsenabled'] == 'false':
      return _show_login(request, ltemplate, {'err' : "Please enable javascript and try again."}, form)

    user = djangoauth.authenticate(username=request.POST['username'], password=request.POST['password'])
    if user is not None:
      if user.is_active:
        # logs the user in via django's auth platform. (this associates the user with the current session) 
        djangoauth.login(request, user)
        try:
          # only clear out the cookie if we actually authenticate and login ok
          request.session.delete_test_cookie()
        except:
          pass
        # Login successful, redirect to the user's profile.
        # JTC: MIGHT NOT BE NEEDED. Should be able to just use request.user
        interface.login_user(request)
        
        return HttpResponseRedirect(reverse("profile"))
      else:
        # Return a 'disabled account' error message
        return _show_login(request, ltemplate, {'err' : "This account has been disabled."}, form)
      
    # Return an 'invalid login' error message.
    return _show_login(request, ltemplate, {'err' : "Wrong username or password."}, form)

  # request type is GET, show a fresh login page
  return _show_login(request, ltemplate, {})


def logout(request):
  interface.logout_user(request)
  return HttpResponseRedirect(reverse("profile"))


@login_required()
def help(request):
  user = _validate_and_get_geniuser(request)
  return direct_to_template(request,'control/help.html', {})


# HTML view for the 'My GENI' page
# TODO: Need interface call for total_vessel_credits
@login_required()
def mygeni(request):
  user = _validate_and_get_geniuser(request)
  
  total_vessel_credits = 10
  num_acquired_vessels = len(interface.get_acquired_vessels(user))
  avail_vessel_credits = total_vessel_credits - num_acquired_vessels
  percent_total_used = int((num_acquired_vessels * 1.0 / total_vessel_credits * 1.0) * 100.0)
  
  # total_vessel_credits, percent_total_used, avail_vessel_credits
  return direct_to_template(request,'control/mygeni.html', 
                            {'total_vessel_credits' : total_vessel_credits,
                             'percent_total_used' : percent_total_used,
                             'avail_vessel_credits' : avail_vessel_credits})

# TODO: This is just temporary to get the existing templates working.
@login_required()
def myvessels(request, get_form=False, action_explanation="", remove_explanation="", action_summary=""):
  user = _validate_and_get_geniuser(request)
  
  if get_form is False:
    get_form = forms.gen_get_form(user)

  # shared vessels that are used by others but which belong to this user (TODO)
  shvessels = []

  # this user's used vessels
  my_vessels_raw = interface.get_acquired_vessels(user)
  my_vessels = interface.get_vessel_infodict_list(my_vessels_raw)

  # return the used resources page constructed from a template
  return direct_to_template(request,'control/myvessels.html',
                            {'geni_user' : user,
                             'num_vessels' : len(my_vessels),
                             'my_vessels' : my_vessels,
                             'sh_vessels' : shvessels,
                             'get_form' : get_form,
                             'action_explanation' : action_explanation,
                             'remove_explanation' : remove_explanation,
                             "action_summary" : action_summary})

@login_required()
def getdonations(request):
  user = _validate_and_get_geniuser(request)
  return direct_to_template(request,'control/getdonations.html', {'username' : user.username})

# TODO: This is just temporary to get the existing templates working.
@login_required()
def get_resources(request):
  pass

# TODO: This is just temporary to get the existing templates working.
@login_required()
def del_resource(request):
  pass

# TODO: This is just temporary to get the existing templates working.
@login_required()
def del_all_resources(request):
  pass

# TODO: This is just temporary to get the existing templates working.
@login_required()
def gen_new_key(request):
  pass

@log_function_call
@login_required()
def del_priv(request):
  user = _validate_and_get_geniuser(request)
  if user.user_privkey == "":
    msg = "Private key has already been deleted."
  else:
    try:
      interface.delete_private_key(user)
    except DoesNotExistError:
      msg = "Private key couldn't be deleted. (Couldn't grab user for key delete)"
    else:
      msg = "Private key has been deleted."
  return direct_to_template(request, 'control/profile.html',
                            {'geni_user' : user,
                             'info' : msg})


@log_function_call
@login_required()
def priv_key(request):
  user = _validate_and_get_geniuser(request)
  response = HttpResponse(user.user_privkey, mimetype='text/plain')
  response['Content-Disposition'] = 'attachment; filename=' + str(user.username) + '.privatekey'
  return response


@log_function_call
@login_required()
def pub_key(request):
  user = _validate_and_get_geniuser(request)
  response = HttpResponse(user.user_pubkey, mimetype='text/plain')
  response['Content-Disposition'] = 'attachment; filename=' + str(user.username) + '.publickey'
  return response



def _validate_and_get_geniuser(request):
  try:
    user = interface.get_logged_in_user(request)
  except DoesNotExistError:
    # JTC: we shouldn't ever get here, since we're restricting view methods with
    # @login_required, which should kick the user back to the login page if they
    # aren't logged in. but.. just in case the user still can't be retrieved from the session.
    return _show_login(request, 'accounts/login.html', {})
  return user