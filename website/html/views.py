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
import traceback

from django.http import HttpResponse
from django.http import HttpResponseRedirect
from django.contrib.auth.forms import AuthenticationForm
from django.contrib.auth.decorators import login_required
from django.contrib.sites.models import Site
from django.core.urlresolvers import reverse
from django.views.generic.simple import direct_to_template
from django.views.generic.simple import redirect_to

# Make available all of our own standard exceptions.
from seattlegeni.common.exceptions import *

# This is the logging decorator use use.
from seattlegeni.common.util.decorators import log_function_call
from seattlegeni.common.util.decorators import log_function_call_without_return

# For user registration input validation
from seattlegeni.common.util import validations

from seattlegeni.common.util import log

from seattlegeni.website import settings

# All of the work that needs to be done is passed through the controller interface.
from seattlegeni.website.control import interface

from seattlegeni.website.html import forms

from seattle import repyhelper
from seattle import repyportability

repyhelper.translate_and_import('rsa.repy')

# Path to the customize_installers.py. In this case, it's in the same directory
# as this views.py file.
PATH_TO_CUSTOMIZE_INSTALLER_SCRIPT = os.path.join(os.path.dirname(__file__), 
                                                  "customize_installers.py")

SITE_DOMAIN = "http://" + Site.objects.get_current().domain



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
  fullpath = os.path.join(settings.STATE_KEYS_DIR, key_file_name)
  return rsa_publickey_to_string(rsa_file_to_publickey(fullpath))





# The key used as the state key for new donations.
ACCEPTDONATIONS_STATE_PUBKEY = _state_key_file_to_publickey_string("acceptdonation.publickey")

SEATTLE_OWNER_PUBKEY = "22599311712094481841033180665237806588790054310631222126405381271924089573908627143292516781530652411806621379822579071415593657088637116149593337977245852950266439908269276789889378874571884748852746045643368058107460021117918657542413076791486130091963112612854591789518690856746757312472362332259277422867 12178066700672820207562107598028055819349361776558374610887354870455226150556699526375464863913750313427968362621410763996856543211502978012978982095721782038963923296750730921093699612004441897097001474531375768746287550135361393961995082362503104883364653410631228896653666456463100850609343988203007196015297634940347643303507210312220744678194150286966282701307645064974676316167089003178325518359863344277814551559197474590483044733574329925947570794508677779986459413166439000241765225023677767754555282196241915500996842713511830954353475439209109249856644278745081047029879999022462230957427158692886317487753201883260626152112524674984510719269715422340038620826684431748131325669940064404757120601727362881317222699393408097596981355810257955915922792648825991943804005848347665699744316223963851263851853483335699321871483966176480839293125413057603561724598227617736944260269994111610286827287926594015501020767105358832476708899657514473423153377514660641699383445065369199724043380072146246537039577390659243640710339329506620575034175016766639538091937167987100329247642670588246573895990251211721839517713790413170646177246216366029853604031421932123167115444834908424556992662935981166395451031277981021820123445253"





@log_function_call_without_return
@login_required
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
  
  username = user.username
  affiliation = user.affiliation
  port = user.usable_vessel_port
  has_privkey = user.user_privkey != None
  info = ""
  
  return direct_to_template(request, 'control/profile.html',
                            {'username' : username, 
                             'affiliation' : affiliation,
                             'port' : port, 
                             'has_privkey' : has_privkey,
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
  
  return direct_to_template(request,'control/help.html', {'username': user.username})





def accounts_help(request):
  return direct_to_template(request, 'accounts/help.html', {})



@login_required
def mygeni(request):
  try:
    user = _validate_and_get_geniuser(request)
  except LoggedInButFailedGetGeniUserError:
    return _show_failed_get_geniuser_page(request)
  
  total_vessel_credits = interface.get_total_vessel_credits(user)
  num_acquired_vessels = len(interface.get_acquired_vessels(user))
  avail_vessel_credits = total_vessel_credits - num_acquired_vessels
  percent_total_used = int((num_acquired_vessels * 1.0 / total_vessel_credits * 1.0) * 100.0)
  
  # total_vessel_credits, percent_total_used, avail_vessel_credits
  return direct_to_template(request,'control/mygeni.html', 
                            {'username' : user.username,
                             'total_vessel_credits' : total_vessel_credits,
                             'percent_total_used' : percent_total_used,
                             'avail_vessel_credits' : avail_vessel_credits})





@login_required
def myvessels(request, get_form=False, action_summary="", action_detail="", remove_summary=""):
  try:
    user = _validate_and_get_geniuser(request)
  except LoggedInButFailedGetGeniUserError:
    return _show_failed_get_geniuser_page(request)
  
  if get_form is False:
    get_form = forms.gen_get_form(user)

  # shared vessels that are used by others but which belong to this user (TODO)
  shvessels = []

  # this user's used vessels
  my_vessels_raw = interface.get_acquired_vessels(user)
  my_vessels = interface.get_vessel_infodict_list(my_vessels_raw)

  # return the used resources page constructed from a template
  return direct_to_template(request,'control/myvessels.html',
                            {'username' : user.username,
                             'num_vessels' : len(my_vessels),
                             'my_vessels' : my_vessels,
                             'sh_vessels' : shvessels,
                             'get_form' : get_form,
                             'action_summary' : action_summary,
                             'action_detail' : action_detail,
                             'remove_summary' : remove_summary})





@login_required
def getdonations(request):
  try:
    user = _validate_and_get_geniuser(request)
  except LoggedInButFailedGetGeniUserError:
    return _show_failed_get_geniuser_page(request)
  
  return direct_to_template(request,'control/getdonations.html', 
                            {'username' : user.username,
                             'domain' : SITE_DOMAIN})





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
  #if get_form is None:
  #  return myvessels(request)
  
  action_summary = ""
  action_detail = ""
  keep_get_form = False
  
  if get_form.is_valid():
    vessel_num = get_form.cleaned_data['num']
    vessel_type = get_form.cleaned_data['env']
    
    try:
      acquired_vessels = interface.acquire_vessels(user, vessel_num, vessel_type)
    except UnableToAcquireResourcesError, err:
      action_summary = "Couldn't acquire resources at this time."
      action_detail += str(err)
      keep_get_form = True
    except InsufficientUserResourcesError:
      action_summary = "You do not have enough vessel credits to fufill this request."
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
    remove_summary = "Internal GENI Error. The vessel you are trying to delete does not exist."
  except InvalidRequestError, err:
    remove_summary = "Internal GENI Error. Please contact us! Details: " + str(err)
  else:
    try:
      interface.release_vessels(user, vessel_to_release)
    except InvalidRequestError, err:
      remove_summary = "Internal GENI Error. Please contact us! Details: " + str(err)
  
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
  interface.release_all_vessels(user)
  
  return myvessels(request, remove_summary=remove_summary)





# TODO: This is just temporary to get the existing templates working.
@login_required
def gen_new_key(request):
  pass





@log_function_call
@login_required
def del_priv(request):
  try:
    user = _validate_and_get_geniuser(request)
  except LoggedInButFailedGetGeniUserError:
    return _show_failed_get_geniuser_page(request)
  
  if user.user_privkey == "":
    msg = "Private key has already been deleted."
  else:
    interface.delete_private_key(user)
    msg = "Private key has been deleted."
  return direct_to_template(request, 'control/profile.html',
                            {'geni_user' : user,
                             'info' : msg})





@log_function_call
@login_required
def priv_key(request):
  try:
    user = _validate_and_get_geniuser(request)
  except LoggedInButFailedGetGeniUserError:
    return _show_failed_get_geniuser_page(request)
  
  response = HttpResponse(user.user_privkey, mimetype='text/plain')
  response['Content-Disposition'] = 'attachment; filename=' + str(user.username) + '.privatekey'
  return response





@log_function_call
@login_required
def pub_key(request):
  try:
    user = _validate_and_get_geniuser(request)
  except LoggedInButFailedGetGeniUserError:
    return _show_failed_get_geniuser_page(request)
  
  response = HttpResponse(user.user_pubkey, mimetype='text/plain')
  response['Content-Disposition'] = 'attachment; filename=' + str(user.username) + '.publickey'
  return response





def download(request, username):
  validuser = True
  try:
    # validate that this username actually exists
    user = interface.get_user_for_installers(username)
  except DoesNotExistError:
    validuser = False
  return direct_to_template(request,'download/installers.html', {'username' : username, 
                                                                 'validuser' : validuser})





def build_win_installer(request, username):
  """
  <Purpose>
    Allows the user to download a Windows distribution of Seattle
    that will donate resources to user with 'username'.
  
  <Arguments>
    request:
       HTTP Request object
    username (string):
       A string representing the GENI user's username into the GENI portal
  
  <Exceptions>
    None?
  
  <Side Effects>
    None
  
  <Returns>
    On failure of username lookup returns an HTTP response with
    description of the error. On success, returns the seattle windows
    distribution file for the user to donate to as username.
  """
  success,ret = _build_installer(username, 'w')
  if not success:
      return HttpResponse("Installer build failed.")
  redir_url = ret + "seattle_win.zip"
  #return redirect_to(request, redir_url)
  return HttpResponseRedirect(redir_url)





def build_linux_installer(request, username):
  """
 <Purpose>
    Allows the user to download a Linux distribution of Seattle
    that will donate resources to user with 'username'.

 <Arguments>
    request:
       HTTP Request object
    username (string):
       A string representing the GENI user's username into the GENI portal

 <Exceptions>
    None?
 
 <Side Effects>
    None

 <Returns>
    On failure of username lookup returns an HTTP response with
    description of the error. On success, returns the seattle linux
    distribution file for the user to donate to as username.
  """
  success,ret = _build_installer(username, 'l')
  if not success:
      return HttpResponse("Installer build failed.")
  redir_url = ret + "seattle_linux.tgz"
  #return redirect_to(request, redir_url)
  return HttpResponseRedirect(redir_url)





def build_mac_installer(request, username):
  """
 <Purpose>
    Allows the user to download a Mac/OSX distribution of Seattle
    that will donate resources to user with 'username'.

 <Arguments>
    request:
       HTTP Request object
    username (string):
       A string representing the GENI user's username into the GENI portal

 <Exceptions>
    None?
 
 <Side Effects>
    None

 <Returns>
    On failure of username lookup returns an HTTP response with
    description of the error. On success, returns the seattle mac
    distribution file for the user to donate to as username.
  """
  success,ret = _build_installer(username, 'm')
  if not success:
      return HttpResponse("Installer build failed.")
  redir_url = ret + "seattle_mac.tgz"
  return HttpResponseRedirect(redir_url)





def _build_installer(username, dist_char):
  """
  <Purpose>
     Builds an installer with distrubution char 'dist_char' that
     describes the platform of the desired installer, that will
     donate resources to user with username.
  
  <Arguments>
     username (string):
        A string representing the GENI user's username into the GENI portal
     dist_char (string):
        Containing 'm' or 'l' or 'w' for each major distribution
        (Mac/Linux/Windows) that this function will build/compose.
  
  <Exceptions>
     None?
  
  <Side Effects>
     Creates a new installer file in a temporary directory that is
     world readable via Apache. It also creates a variety of files in
     this temporary directory that are relevant to the installer
     build process.
  
  <Returns>
     On success, returns (True, URL) where URL is the redirection url
     to the request installer. On failure returns (False,
     HttpResponse) where HttpResponse is an HTTP Response that
     specifies what went wrong in attemptign to look up the user with
     username.
  """
  try:
    user = interface.get_user_for_installers(username)
    username = user.username
  except DoesNotExistError:
    # TODO: what happens if the username is invalid? render a "build failed, bad user" page?
    ret = HttpResponse("Couldn't get user.")
    return False, ret
   
  prefix = os.path.join(settings.USER_INSTALLERS_DIR, "%s_dist"%(username))
  temp_installinfo_dir = os.path.join(prefix, "install_info")

  user_pubkey = user.donor_pubkey

  # remove and recreate the prefix dir
  shutil.rmtree(prefix, True)
  
#  try:
#    shutil.rmtree(prefix)
#  except OSError, err:
#    # directory didn't previously exist
#    pass

  os.mkdir(prefix)
 
  # create the install_info dir, a temporary directory where the vesselinfo
  # will reside right before it gets added into the install package by customize_installer
  os.mkdir(temp_installinfo_dir)

  # prepare & write out the vesselinfo file 
  vesselinfo = "Percent 80\n"
  vesselinfo += "Owner " + user_pubkey + "\n"
  vesselinfo += "User " + ACCEPTDONATIONS_STATE_PUBKEY + "\n"
  vesselinfo += "Percent 20\n"
  vesselinfo += "Owner " + SEATTLE_OWNER_PUBKEY + "\n"

  f = open((temp_installinfo_dir + "/vesselinfo"), 'w')
  f.write(vesselinfo)
  f.close()

  log.info("file preparation done. calling customize installer.")
  #os.system("python %s %s %s %s"%(customize_installer_script, "l", temp_installinfo_dir, prefix))
  try:
    subprocess.check_call([sys.executable, PATH_TO_CUSTOMIZE_INSTALLER_SCRIPT, dist_char, 
                           settings.BASE_INSTALLERS_DIR, temp_installinfo_dir, prefix])
  except subprocess.CalledProcessError:
    raise 
    
  redir_url = settings.USER_INSTALLERS_URL + "/%s_dist/"%(username)
  return True, redir_url





def donations_help(request, username):
  return direct_to_template(request,'download/help.html', {'username' : username})





def _validate_and_get_geniuser(request):
  try:
    user = interface.get_logged_in_user(request)
  except DoesNotExistError:
    # Failed to get GeniUser record, but user is logged in
    raise LoggedInButFailedGetGeniUserError
  return user


def _show_failed_get_geniuser_page(request):
  err = "Sorry, we can't display the page you requested. "
  err += "If you are logged in as an administrator, you'll need to logout, and login with a SeattleGENI account. "
  err += "If you aren't logged in as an administrator, then this is a bug. Please contact us!"
  return _show_login(request, 'accounts/login.html', {'err' : err})