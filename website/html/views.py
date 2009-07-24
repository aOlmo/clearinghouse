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

from django.contrib.auth.forms import AuthenticationForm

from django.views.generic.simple import direct_to_template

# Make available all of our own standard exceptions.
from seattlegeni.common.exceptions import *

# This is the logging decorator use use.
from seattlegeni.common.util.decorators import log_function_call_without_return

# All of the work that needs to be done is passed through the controller interface.
from seattlegeni.website.control import interface

from seattlegeni.website.html import forms





#TODO: @login_required decorator? I think we'll probably do this ourselves, instead.
@log_function_call_without_return
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
  
  user = interface.get_logged_in_user(request)

  # If the user's session has expired, show them an appropriate page.
  # Note that if @login_required is being used, this might not be
  # possible, but we should at least check it and raise an exception
  # if we dont' think it's possible.
  if user is None:
    # TODO
    pass
  
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


  
###################################################################
# Below here are functions that have not been reimplemented for the
# new version of seattlegeni but that need to be defined in order
# to avoid the need to modify the existing templates.
###################################################################

# TODO: This is just temporary to get the existing templates working.
def login(request):
  pass

# TODO: This is just temporary to get the existing templates working.
def logout(request):
  pass

# TODO: This is just temporary to get the existing templates working.
def help(request):
  pass

# TODO: This is just temporary to get the existing templates working.
def mygeni(request):
  pass

# TODO: This is just temporary to get the existing templates working.
def myvessels(request):
  pass

# TODO: This is just temporary to get the existing templates working.
def getdonations(request):
  pass

# TODO: This is just temporary to get the existing templates working.
def get_resources(request):
  pass

# TODO: This is just temporary to get the existing templates working.
def del_resource(request):
  pass

# TODO: This is just temporary to get the existing templates working.
def del_all_resources(request):
  pass

# TODO: This is just temporary to get the existing templates working.
def gen_new_key(request):
  pass

# TODO: This is just temporary to get the existing templates working.
def del_priv(request):
  pass

# TODO: This is just temporary to get the existing templates working.
def priv_key(request):
  pass

# TODO: This is just temporary to get the existing templates working.
def pub_key(request):
  pass

