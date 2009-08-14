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

from django.http import HttpResponse
from django.http import HttpResponseRedirect
from django.contrib.auth.forms import AuthenticationForm
from django.contrib.auth.decorators import login_required
from django.core.urlresolvers import reverse
from django.views.generic.simple import direct_to_template
from django.views.generic.simple import redirect_to
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



@login_required()
def myvessels(request, get_form=False, action_summary="", action_detail="", remove_detail=""):
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
                             'action_summary' : action_summary,
                             'action_detail' : action_detail,
                             'remove_detail' : remove_detail})



@login_required()
def getdonations(request):
  user = _validate_and_get_geniuser(request)
  return direct_to_template(request,'control/getdonations.html', {'username' : user.username})



@login_required()
def get_resources(request):
  user = _validate_and_get_geniuser(request)
  
  # the request must be via POST. if not, bounce user back to My Vessels page
  if not request.method == 'POST':
    return myvessels(request)
  
  # try and grab form from POST. if it can't, bounce user back to My Vessels page
  get_form = forms.gen_get_form(user, request.POST)
  if get_form is None:
    return myvessels(request)
  
  action_summary = ""
  action_detail = ""
  
  if get_form.is_valid():
    vessel_num = get_form.cleaned_data['num']
    vessel_type = get_form.cleaned_data['env']
    
    try:
      acquired_vessels = interface.acquire_vessels(user, vessel_num, vessel_type)
    except UnableToAcquireResourcesError, err:
      action_summary = "Couldn't acquire resources at this time. Details follow:"
      action_detail = str(err)
    except InsufficientUserResourcesError:
      action_summary = "You do not have enough vessel credits to fufill this request."
  
  # return a My Vessels page with the updated vessels/vessel acquire details/errors
  return myvessels(request, get_form, action_summary=action_summary, action_detail=action_detail)
  

@login_required()
def del_resource(request):
  user = _validate_and_get_geniuser(request)
  
  # the request must be via POST. if not, bounce user back to My Vessels page
  if not request.method == 'POST':
    return myvessels(request)

  if not request.POST['handle']:
    print ("*** REQUEST.POST HANDLE WAS EMPTY")
    return myvessels(request)
  
  # vessel_handle needs to be a list (even though we only add one handle), 
  # since get_vessel_list expects a list.
  vessel_handle = []
  vessel_handle.append(request.POST['handle'])
  remove_detail = ""
  
  print "*** ABOUT TO CONVERT HANDLE TO VESSEL, handle: ", request.POST['handle']
  try:
    # convert handle to vessel
    vessel_to_release = interface.get_vessel_list(vessel_handle)
  except DoesNotExistError:
    remove_detail = "Internal GENI Error. The vessel you are trying to delete does not exist."
  except InvalidRequestError, err:
    remove_detail = "Internal GENI Error. Please contact us! Details: " + str(err)
  else:
    try:
      interface.release_vessels(user, vessel_to_release)
    except InvalidRequestError, err:
      remove_detail = "Internal GENI Error. Please contact us! Details: " + str(err)
  
  return myvessels(request, remove_detail=remove_detail)



@login_required()
def del_all_resources(request):
  user = _validate_and_get_geniuser(request)
  
  # the request must be via POST. if not, bounce user back to My Vessels page
  if not request.method == 'POST':
    return myvessels(request)
  
  remove_detail = ""
  
  try:
    interface.release_all_vessels(user)
  except DoesNotExistError:
    remove_detail = "Internal GENI Error. The vessel you are trying to delete does not exist."
  
  return myvessels(request, remove_detail=remove_detail)
  
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
    interface.delete_private_key(user)
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



def download(request, username):
  validuser = True
  try:
    # validate that this username actually exists
    user = interface.get_user_for_installers(username)
  except DoesNotExistError:
    validuser = False
  return direct_to_template(request,'download/installers.html', {'username' : username, 'validuser' : validuser})



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
  success,ret = build_installer(username, 'w')
  if not success:
      return ret
  redir_url = ret + "seattle_win.zip"
  return redirect_to(request, redir_url)



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
  success,ret = build_installer(username, 'l')
  if not success:
      return ret
  redir_url = ret + "seattle_linux.tgz"
  return redirect_to(request, redir_url)



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
  success,ret = build_installer(username, 'm')
  if not success:
      return ret
  redir_url = ret + "seattle_mac.tgz"
  return redirect_to(request, redir_url)



def build_installer(username, dist_char):
    """
   <Purpose>
      Builds an installer with distrubution char 'dist_char' that
      describes the platform of the desired installer, that will
      donate resources to uesr with username.

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
      #TODO: what happens if the username is invalid? render a "build failed, bad user" page?
      ret = HttpResponse("Couldn't get user.")
      return False, ret

    # prefix dir is specific to this user
    prefix = "/var/www/dist/geni/%s_dist"%(username)
    # paths to custominstallerinfo and customize_installers script
    vesselinfopy = "/home/geni/trunk_do_not_update/test/writecustominstallerinfo.py"
    customize_installer_script = "/home/geni/trunk_do_not_update/dist/customize_installers.py"
    
    genilookuppubkey = "129774128041544992483840782113037451944879157105918667490875002217516699749307491907386666192386877354906201798442050236403095676275904600258748306841717805688118184641552438954898004036758248379889058675795451813045872492421308274734660011578944922609099087277851338277313994200761054957165602579454496913499 5009584846657937317736495348478482159442951678179796433038862287646668582746026338819112599540128338043099378054889507774906339128900995851308672478258731140180190140468013856238094738039659798409337089186188793214102866350638939419805677190812074478208301019935069545923355193838949699496492397781457581193908714041831854374243557949384786876738266983181127249134779897575097946022340850779201939355412918841366370355327173665360672716628991450762121558255087503128279166537142360507802367604402756069070736597174937086480718583392482692614171062272186494071564184129689431325498982800811856338274118203718702345272278560446589165471494375651361750852019147810160148921625729542290638336334809398971313397822221564079037502214439643276240764600598988028102968157487817931720659847520822457976835172247118797446828110946660365132205322939204586763411439281848784213195825380220677820416073940040666481776343542973130000147584659760068373009458649543362607042577145752915876989793197702723812196638625607032478537457723974278728977851718860740932725872670723883052328375429048891803294991318092625440596678842926089139554432813900387338150959410412520854154851406242710420276841944243411402577440698771918699717808708127522759621651"
    
    # remove and recreate the prefix dir
    os.system("rm -Rf %s/"%(prefix))
    os.system("mkdir %s/"%(prefix))

    # write out to file the user's donor key
    f = open('%s/%s'%(prefix, username),'w');
    f.write("%s"%(user.user_pubkey))
    f.close()

    # write out to file the geni lookup key
    f = open('%s/%s_geni'%(prefix, username),'w');
    f.write("%s"%(genilookuppubkey))
    f.close()
    
    # write out to file the vesselinfo to customize the installer
    vesselinfo = '''Percent 8\nOwner %s/%s\nUser %s/%s_geni\n'''%(prefix,username,prefix,username);
    f = open('%s/vesselinfo'%(prefix),'w');
    f.write("%s"%(vesselinfo))
    f.close()

    # create the dir where vesselinfo will be created
    os.system("mkdir %s/vesselinfodir/"%(prefix))
    # create the vessel info
    cmd = "cd /var/www/dist/geni && python %s %s/vesselinfo %s/vesselinfodir 2> /tmp/customize.err > /tmp/customize.out"%(vesselinfopy, prefix, prefix)
    #f = open("/tmp/out", "w")
    #f.write(cmd)
    os.system(cmd)
    # run carter's script to create the installer of the particular type ((w)in, (l)inux, or (m)ac)
    os.system("python %s %s %s/vesselinfodir/ %s/ > /tmp/carter.out 2> /tmp/carter.err"%(customize_installer_script, dist_char, prefix,prefix))
    #os.system("python %s %s %s/vesselinfodir/ %s/ &> /tmp/out"%(carter_script, dist_char, prefix,prefix))
    # compose and return the url to which the user needs to be redirected
    redir_url = "http://seattlegeni.cs.washington.edu/dist/geni/%s_dist/"%(username)
    return True, redir_url



def donations_help(request, username):
  return direct_to_template(request,'download/help.html', {'username' : username})



def _validate_and_get_geniuser(request):
  try:
    user = interface.get_logged_in_user(request)
  except DoesNotExistError:
    # JTC: we shouldn't ever get here, since we're restricting view methods with
    # @login_required, which should kick the user back to the login page if they
    # aren't logged in. but.. just in case the user still can't be retrieved from the session.
    return _show_login(request, 'accounts/login.html', {})
  return user