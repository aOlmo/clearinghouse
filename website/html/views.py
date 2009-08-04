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

from django.utils import simplejson

# Make available all of our own standard exceptions.
from seattlegeni.common.exceptions import *

# This is the logging decorator use use.
from seattlegeni.common.util.decorators import log_function_call
from seattlegeni.common.util.decorators import log_function_call_without_return

# All of the work that needs to be done is passed through the controller interface.
from seattlegeni.website.control import interface

from seattlegeni.website.html import forms


#TODO: @login_required decorator? I think we'll probably do this ourselves, instead.
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
    print "*** USER IS NONE."
    return _show_login(request, 'accounts/login.html', {})
  
  return direct_to_template(request, 'control/profile.html',
                            {'geni_user' : user,
                             'info' : info})
  

def register(request):
  # TODO: check if there is a logged in user with this session already.
  
  if request.method == 'POST':
    # TODO: Validate submitted data! Skipping validation just during development.
    
    # Need to check that the attributes exist, not just grab them.
    # JCS: This was just the start of getting the register page to work.
    #      It isn't anywhere near complete or correct.
    username = request.POST["username"]
    password = request.POST["password"]
    password2 = request.POST["password2"]
    email = request.POST["email"]
    affiliation = request.POST["affiliation"]
    pubkey = None
    
    # At a minimum, the username cannot be empty. This is because register_user expects at
    # least a non-emtpy username so that it can try to obtain a lock on that username.
    if len(username) == 0:
      # TODO: show user an error message
      return
    
    geniuser = interface.register_user(username, password, email, affiliation, pubkey)
    
    return _show_login(request, 'accounts/login.html',
                      {'msg' : "Username %s has been successfully registered." % (geniuser)})
    
#        form = forms.UserCreationForm(request.POST, request.FILES)
#        if form.is_valid():
#            txt_pubkey = ""
#            if 'pubkey' in request.FILES:
#                file = request.FILES['pubkey']
#                if file.size > 2048:
#                    return HttpResponse("Public key too large, file size limit is 2048 bytes")
#                txt_pubkey = file.read()
#                
#            print "TXT_PUBKEY IS:", txt_pubkey    
#            if form.cleaned_data['gen_upload_choice'] == 2 and txt_pubkey == "":
#                return HttpResponse("Enter a public key")
#            
#            # if they specified a public key we must check it
#            if txt_pubkey != "":
#              # JAC: Need to verify the public key is valid
#              try:
#                possiblepubkey = rsa_string_to_publickey(txt_pubkey)
#              except ValueError:
#                # This will occur when the key isn't even a key (i.e. they 
#                # uploaded junk
#                return HttpResponse("Cannot convert key.   Please generate your public key using Seash.")
#
#              # JAC: Need to verify the public key is valid
#              if not rsa_is_valid_publickey(possiblepubkey):
#                return HttpResponse("The public key you uploaded is not valid.   Please generate using Seash.")
#
#            # this saves the user's record to the database
#            new_user = form.save()
#
#            # this creates and saves the geni user in the database
#            geni_user = User(www_user = new_user, affiliation=form.cleaned_data['affiliation'], pubkey=txt_pubkey, privkey="")
#            geni_user.save_new_user()
#  
#            
#            return show_login(request, 'accounts/login.html',
#                              {'msg' : "Username %s has been successfully registered."%(new_user)})
  else:
    form = forms.GeniUserCreationForm()
    return direct_to_template(request, 'accounts/register.html', {'form' : form})
  



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


def _validate_and_get_geniuser(request):
  try:
    user = interface.get_logged_in_user(request)
  except DoesNotExistError:
    # JTC: we shouldn't ever get here, since we're restricting view methods with
    # @login_required, which should kick the user back to the login page if they
    # aren't logged in. but.. just in case the user still can't be retrieved from the session.
    return _show_login(request, 'accounts/login.html', {})
  return user
  
###################################################################
# Below here are functions that have not been reimplemented for the
# new version of seattlegeni but that need to be defined in order
# to avoid the need to modify the existing templates.
###################################################################

#TODO: Login form presents a 'next' field, if the user visits a page
#      but gets bounced back to the login page, we should redirect them
#      there after successful login.
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


@login_required()
def mygeni(request):
  user = _validate_and_get_geniuser(request)
  return direct_to_template(request,'control/mygeni.html', {})

# TODO: This is just temporary to get the existing templates working.
@login_required()
def myvessels(request):
  pass

# TODO: This is just temporary to get the existing templates working.
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

#def __validate_ajax(request):
#    ret, success = __validate_guser__(request)
#    if not success:
#        return __jsonify({"success" : False, "error" : "could not validate your identity"}), False
#    geni_user = ret
#
#    # validate that the request is a POST method
#    if not request.method == u'POST':
#        return __jsonify({"success" : False, "error" : "request must be a POST method"}), False
#    
#    return geni_user, True

def __jsonify(data):
    """
    <Purpose>
        Turns data into json representation (marshalls data), and
        generates and returns an HttpResponse object that will communicate
        the json representation of data to the client.
       
    <Arguments>
        data: data to marshall to the client as json. Typically this is a
        simple datatype, such as a dictionary, or an array, of strings/ints.

    <Exceptions>
        None?
    
    <Side Effects>
        None

    <Returns>
        An HTTP response object the has mimetype set to application/json
    """
    json = simplejson.dumps(data)
    return HttpResponse(json, mimetype='application/json')

def _validate_ajax_and_get_geniuser(request):
  try:
    user = interface.get_logged_in_user(request)
  except DoesNotExistError:
    return __jsonify({"success" : False, "error" : "could not validate your identity"}), False
  if not request.method == u'POST':
    return __jsonify({"success" : False, "error" : "request must be a POST method"}), False
  return user
  
def ajax_getcredits(request):
    """
    <Purpose>

    <Arguments>
        request:
            An HTTP request object, representing the ajax POST request.
            
    <Exceptions>

    <Side Effects>

    <Returns>
        An HTTP response object

    <Note>
    """
    print "ajax_getcredits called"
    geni_user = _validate_ajax_and_get_geniuser(request)
    
    # NOTE: total percentage of percent_credits must be 100%
    percent_credits, total_vessels = geni_user.get_user_credits()
    
    print "get_user_credits returned: "
    print percent_credits
    print total_vessels

    credits = []
    for guser, percent in percent_credits:
        if guser == geni_user:
            geni_user_record = [{'username' : "Me", 'percent' : percent}]
            continue

        credits.append({'username' : str(guser),
                        'percent' : percent})
    
    # sort the credits list according to their percent
    def credit_compare(a, b):
        return cmp(a['percent'], b['percent'])
    credits.sort(credit_compare)
    print "sorted credits: "
    print credits

    # sort credits into two lists: credits above threshold limit and
    # below threshold limit (for nice display on page)
    credit_thresh = 10
    credits_above_thresh = []
    credits_below_thresh = []
    for credit in credits:
        if credit['percent'] > credit_thresh:
            credits_above_thresh.append(credit)
        else:
            credits_below_thresh.append(credit)

    ret = [credits_above_thresh, credits_below_thresh, geni_user_record, int(total_vessels)]
    return __jsonify(ret)



