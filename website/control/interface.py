"""
<Program Name>
  interface.py

<Started>
  June 17, 2009

<Author>
  Justin Samuel

<Purpose>
  This module presents the only methods that a frontend action will call. These
  methods do the work of ensuring that an action requested through a frontend
  are performed. The resulting data that the frontend needs is returned from
  these methods.
  
  This module should be the only point of entry from a frontend to the rest of
  the code base.

  Functions in this module will make calls to the following APIs:
    * backend
    * keygen
    * lockserver
    * maindb
  
<Notes>
  * All references to user here are to our GeniUser model, not to the django user.
  
  * The functions that modify the seattlegeni database or perform actions on
    nodes all do an extra check to ensure the user is valid after obtaining a
    user lock. This is to ensure that user has not been deleted and to see other
    changes to the user that were made between the time that the request was
    made and when the lock was obtained.
    
  * When using this module from the frontend views, you do not need to catch
    InternalError, ProgrammerError, or otherwise uncaught exceptions. Those
    are allowed to trickle all the way up and get handled based on how we've
    configured django.
"""

import traceback
import datetime

from seattlegeni.common.exceptions import *

from seattlegeni.common.api import backend
from seattlegeni.common.api import keygen
from seattlegeni.common.api import lockserver
from seattlegeni.common.api import maindb

from seattlegeni.common.util import validations

from seattlegeni.common.util.assertions import *

from seattlegeni.common.util.decorators import log_function_call
from seattlegeni.common.util.decorators import log_function_call_and_only_first_argument

from seattlegeni.website.control import vessels





@log_function_call_and_only_first_argument
def register_user(username, password, email, affiliation, pubkey=None):
  """
  <Purpose>
    Creates a user record with the specified information and sets any additional
    information necessary for the user record to be complete.
  <Arguments>
    username
    password
    email
    affiliation
    pubkey
      Optional. A string. If not provided, a key pair will be generated for this user.
  <Exceptions>
    UsernameAlreadyExistsError
      If there is already a user with the specified username.
    ValidationError
      If any of the arguments contains invalid values or if the username is the
      same as the password.
  <Side Effects>
    The user record in the django db is created as well as a user record in the
    corresponding user profile table that stores our custom information. A port
    will be assigned to the user and the user's donation keys will be set.
  <Returns>
    GeniUser instance (our GeniUser model, not the django User) corresponding to the
    newly registered user.
  """
  # If the frontend code that called this function wants to know which field
  # is invalid, it must call the validation functions itself before making the
  # call to register_user().
  # These will raise a ValidationError if any of the fields are invalid.
  # These ensure that the data is of the correct type (e.g. a string) as well as
  # that we like the content of the variable.
  validations.validate_username(username)
  validations.validate_password(password)
  validations.validate_username_and_password_different(username, password)
  validations.validate_email(email)
  validations.validate_affiliation(affiliation)
  if pubkey is not None:
    validations.validate_pubkey_string(pubkey)
  
  # Lock the user.
  lockserver_handle = lockserver.create_lockserver_handle()
  lockserver.lock_user(lockserver_handle, username)
  try:
    # Ensure there is not already a user with this username.
    try:
      # Raises a DoesNotExistError if the user doesn't exist.
      maindb.get_user(username)
      raise UsernameAlreadyExistsError
    except DoesNotExistError:
      # This is what we wanted: the username isn't already taken.
      pass
    
    # Get a key pair from the keygen api if the user didn't supply their own pubkey.
    if pubkey is None:
      (pubkey, privkey) = keygen.generate_keypair()
    else:
      privkey = None
    
    # Generate a donor key for this user. This is done through the backend
    # as the private key must be stored in the keydb, which the website cannot
    # directly access.
    keydescription = "donor:" + username
    donor_pubkey = backend.generate_key(keydescription)
    
    # Create the user record.
    geniuser = maindb.create_user(username, password, email, affiliation, pubkey, privkey, donor_pubkey)
    
  finally:
    # Unlock the user.
    lockserver.unlock_user(lockserver_handle, username)
    lockserver.destroy_lockserver_handle(lockserver_handle)
    
  return geniuser
  




#def change_user_pubkey(geniuser, user_pubkey):
#  """
#  <Purpose>
#    Assigns a new key pair to this user.
#  <Arguments>
#    geniuser
#    user_pubkey
#  <Exceptions>
#    ProgrammerError
#      If the user is not a valid GeniUser object or if user_pubkey is not a
#      valid pubkey.
#  <Side Effects>
#    The user's public key is replaced with the provided one. If they had a
#    private key still stored in our database, that private key is deleted.
#  <Returns>
#    None
#  """
#  raise NotImplementedError




# JTC: Added for installers.
@log_function_call
def get_user_for_installers(username):
  """
  <Purpose>
    Gets the user record corresponding to the given username.
    IMPORTANT: Used ONLY FOR getting the user object for downloading/building installers.
               Do NOT use for any other purpose, as this function does not validate passwords.
  <Arguments>
    username
      The username (must be a string).
  <Exceptions>
    DoesNotExistError
      If there is no user with the specified username and password.
  <Side Effects>
    None
  <Returns>
    The GeniUser instance if the username is valid.
  """
  assert_str(username)
  
  return maindb.get_user(username)





@log_function_call_and_only_first_argument
def get_user_with_password(username, password):
  """
  <Purpose>
    Gets the user record corresponding to the username and password.
  <Arguments>
    username
      The username (must be a string).
    password
      The password (must be a string).
  <Exceptions>
    DoesNotExistError
      If there is no user with the specified username and password.
  <Side Effects>
    None
  <Returns>
    The GeniUser instance if the username/password are valid.
  """
  assert_str(username)
  assert_str(password)
  
  return maindb.get_user_with_password(username, password)





@log_function_call_and_only_first_argument
def get_user_with_apikey(username, apikey):
  """
  <Purpose>
    Gets the user record corresponding to the username and apikey.
  <Arguments>
    username
      The username (must be a string).
    apikey
      The apikey (must be a string).
  <Exceptions>
    DoesNotExistError
      If there is no user with the specified username and apikey.
  <Side Effects>
    None
  <Returns>
    The GeniUser instance if the username/apikey are valid.
  """
  assert_str(username)
  assert_str(apikey)
  
  return maindb.get_user_with_apikey(username, apikey)  
  


# JTC: Why do we store the username in the request session dict, when
# the username is already available as request.user?
def login_user(request):
  request.session["username"] = request.user.username

#@log_function_call
#def login_user(request, geniuser):
#  """
#  <Purpose>
#    Log in a user to a session. This allows future requests that are part of
#    same session to obtain the user object through calls to get_logged_in_user().
#    This function should not be used through the xmlrpc frontend as there is
#    no concept of the session there.
#  <Arguments>
#    request
#      The HttpRequest object of the user's request through the frontend.
#    geniuser
#      The GeniUser object of the user to be logged in.
#  <Exceptions>
#    None
#  <Side Effects>
#    Associates the user with a session corresponding to the request.
#  <Returns>
#    None
#  """
#  assert_geniuser(geniuser)
#  
#  # JCS: I haven't tested this. It may not work as intended.
#  request.session["username"] = geniuser.username





@log_function_call
def get_logged_in_user(request):
  """
  <Purpose>
    Determine the user logged in to the current session.
    This function should not be used through the xmlrpc frontend as there is
    no concept of the session there.
  <Arguments>
    request
      The HttpRequest object of the user's request through the frontend.
  <Exceptions>
    DoesNotExistError
      If there is no user logged in to the current session.
  <Side Effects>
    None
  <Returns>
    The GeniUser object of the logged in user, or None if there is no logged in
    user (including if the session has expired).
  """
  username = request.session.get("username", None)
  if username is None:
    raise DoesNotExistError
  return maindb.get_user(username)





@log_function_call
def logout_user(request):
  """
  <Purpose>
    Logs out the user logged in to the current session, if any.
  <Arguments>
    request
      The HttpRequest object of the user's request through the frontend.
  <Exceptions>
    None
  <Side Effects>
    Any user logged in to the current session is no longer logged in.
  <Returns>
    None
  """
  # JCS: I haven't tested this. It may not work as intended.
  request.session.flush()
  
  
  
  

@log_function_call
def delete_private_key(geniuser):
  """
  <Purpose>
    Deletes the private key of the specified user.
  <Arguments>
    geniuser
      A GeniUser object of the user whose private key is to be deleted.
  <Exceptions>
    None
  <Side Effects>
    The private key belonging to the user is deleted if it exists, otherwise
    the user account is not modified.
  <Returns>
    None
  """
  assert_geniuser(geniuser)
  
  # Lock the user.
  lockserver_handle = lockserver.create_lockserver_handle()
  lockserver.lock_user(lockserver_handle, geniuser.username)
  try:
    # Make sure the user still exists now that we hold the lock. Also makes
    # sure that we see any changes made to the user before we obtained the lock.
    # We don't use the user object we retrieve because we want the
    # object passed in to the function to reflect the deletion of the key.
    # That is, we want the object passed in to have the user_privkey be None
    # when this function returns.
    try:
      maindb.get_user(geniuser.username)
    except DoesNotExistError:
      raise InternalError(traceback.format_exc())
    
    maindb.delete_user_private_key(geniuser)
    
  finally:
    # Unlock the user.
    lockserver.unlock_user(lockserver_handle, geniuser.username)
    lockserver.destroy_lockserver_handle(lockserver_handle)





@log_function_call
def get_private_key(geniuser):
  """
  <Purpose>
    Gets the private key of the specified user.
  <Arguments>
    geniuser
      A GeniUser object of the user whose private key is to be retrieved.
  <Exceptions>
    None
  <Side Effects>
    None
  <Returns>
    The string containing the user's private key or None if the user's private
    key is not stored by us (e.g. that is, either we never had it or the user
    deleted it).
  """
  assert_geniuser(geniuser)
  
  return geniuser.user_privkey





@log_function_call
def get_donations(geniuser):
  """
  <Purpose>
    Gets a list of donations made by a specific user.
  <Arguments>
    geniuser
      The GeniUser object who is the donor of the donations.
  <Exceptions>
    None
  <Side Effects>
    None
  <Returns>
    A list of the donations made by geniuser.
  """
  assert_geniuser(geniuser)
  
  # This is read-only, so not locking the user.
  return maindb.get_donations_by_user(geniuser)





@log_function_call
def get_acquired_vessels(geniuser):
  """
  <Purpose>
    Gets a list of vessels that have been acquired by the user.
  <Arguments>
    user
      A GeniUser object of the user who is assigned to the vessels.
  <Exceptions>
    None
  <Side Effects>
    None
  <Returns>
    A list of Vessel objects for the vessels that have been acquired by the
    user.
  """
  assert_geniuser(geniuser)
  
  # This is read-only, so not locking the user.
  return maindb.get_acquired_vessels(geniuser)





@log_function_call
def acquire_vessels(geniuser, vesselcount, vesseltype):
  """
  <Purpose>
    Acquire unused vessels of a given type for a user. For information on how
    the specified vesseltype affects which vessels will be considered
    to satisfy the request, see the type-specific functions that are called
    by this function.
  <Arguments>
    geniuser
      The GeniUser which will be assigned the vessels.
    vesselcount
      The number of vessels to acquire (a positive integer).
    vesseltype
      The type of vessels to acquire. One of either 'lan', 'wan', 'nat', or 'rand'.
  <Exceptions>
    UnableToAcquireResourcesError
      If not able to acquire the requested vessels (in this case, no vessels
      will be acquired).
    InsufficientUserResourcesError
      The user does not have enough vessel credits to acquire the number of
      vessels requested.
  <Side Effects>
    A total of 'vesselcount' previously-unassigned vessels of the specified
    vesseltype have been acquired by the user.
  <Returns>
    A list of the vessels as a result of this function call.
  """
  assert_geniuser(geniuser)
  assert_positive_int(vesselcount)
  assert_str(vesseltype)

  # Lock the user.
  lockserver_handle = lockserver.create_lockserver_handle()
  lockserver.lock_user(lockserver_handle, geniuser.username)
  
  try:
    # Make sure the user still exists now that we hold the lock. Also makes
    # sure that we see any changes made to the user before we obtained the lock.
    try:
      geniuser = maindb.get_user(geniuser.username)
    except DoesNotExistError:
      raise InternalError(traceback.format_exc())
    
    # Ensure the user is allowed to acquire these resources. This call will
    # raise an InsufficientUserResourcesError if the additional vessels would
    # cause the user to be over their limit.
    maindb.require_user_can_acquire_resources(geniuser, vesselcount)
    
    if vesseltype == 'wan':
      acquired_list = vessels.acquire_wan_vessels(lockserver_handle, geniuser, vesselcount)
    elif vesseltype == 'lan':
      acquired_list = vessels.acquire_lan_vessels(lockserver_handle, geniuser, vesselcount)
    elif vesseltype == 'nat':
      acquired_list = vessels.acquire_nat_vessels(lockserver_handle, geniuser, vesselcount)
    elif vesseltype == 'rand':
      acquired_list = vessels.acquire_rand_vessels(lockserver_handle, geniuser, vesselcount)
    else:
      raise ProgrammerError("Vessel type '%s' is not a valid type" % vesseltype)
    
    return acquired_list
    
  finally:
    # Unlock the user.
    lockserver.unlock_user(lockserver_handle, geniuser.username)
    lockserver.destroy_lockserver_handle(lockserver_handle)
    




@log_function_call
def release_vessels(geniuser, vessel_list):
  """
  <Purpose>
    Remove a user from a vessel that is assigned to the user.
  <Arguments>
    geniuser
      The GeniUser who is to be removed from the vessel.
    vessel_list
      A list of vessels the user is to be removed from.
  <Exceptions>
    InvalidRequestError
      If any of the vessels in the vessel_list are not currently acquired by
      geniuser.
  <Side Effects>
    The vessel is no longer assigned to the user. If this was the last user
    assigned to the vessel, the vessel is freed.
  <Returns>
    None
  """
  assert_geniuser(geniuser)
  assert_list(vessel_list)
  for vessel in vessel_list:
    assert_vessel(vessel)

  # Lock the user.
  lockserver_handle = lockserver.create_lockserver_handle()
  lockserver.lock_user(lockserver_handle, geniuser.username)
  
  try:
    # Make sure the user still exists now that we hold the lock. Also makes
    # sure that we see any changes made to the user before we obtained the lock.
    try:
      geniuser = maindb.get_user(geniuser.username)
    except DoesNotExistError:
      raise InternalError(traceback.format_exc())
    
    for vessel in vessel_list:
      if vessel.acquired_by_user != geniuser:
        raise InvalidRequestError("Only vessels acquired by this user can be released [offending vessel: " + str(vessel) + "]")
      
    vessels.release_vessels(lockserver_handle, vessel_list)

  finally:
    # Unlock the user.
    lockserver.unlock_user(lockserver_handle, geniuser.username)
    lockserver.destroy_lockserver_handle(lockserver_handle)





@log_function_call
def release_all_vessels(geniuser):
  """
  <Purpose>
    Release all vessels that have been acquired by the user.
  <Arguments>
    geniuser
      The GeniUser who is to have their vessels released.
  <Exceptions>
    None
  <Side Effects>
    All of the user's acquired vessels have been released.
  <Returns>
    None
  """
  assert_geniuser(geniuser)
  
  # Lock the user.
  lockserver_handle = lockserver.create_lockserver_handle()
  lockserver.lock_user(lockserver_handle, geniuser.username)
  try:
    # Make sure the user still exists now that we hold the lock. Also makes
    # sure that we see any changes made to the user before we obtained the lock.
    try:
      geniuser = maindb.get_user(geniuser.username)
    except DoesNotExistError:
      raise InternalError(traceback.format_exc())
    
    # Get a list of all vessels acquired by the user.
    vessel_list = maindb.get_acquired_vessels(geniuser)
    
    vessels.release_vessels(lockserver_handle, vessel_list)
    
  finally:
    # Unlock the user.
    lockserver.unlock_user(lockserver_handle, geniuser.username)
    lockserver.destroy_lockserver_handle(lockserver_handle)





# Not logging the function call for now.
def get_vessel_list(vesselhandle_list):
  """
  <Purpose>
    Convert a list of vesselhandles into a list of Vessel objects.
  <Arguments>
    vesselhandle_list
      A list of strings where each string is a vesselhandle of the format
      "nodeid:vesselname"
  <Exceptions>
    DoesNotExistError
      If a specified vessel does not exist.
    InvalidRequestError
      If any vesselhandle in the list is not in the correct format.
  <Side Effects>
    None
  <Returns>
    A list of Vessel objects.
  """
  assert_list_of_str(vesselhandle_list)
  
  vessel_list = []
  
  for vesselhandle in vesselhandle_list:
    if len((vesselhandle.split(":"))) != 2:
      raise InvalidRequestError("Invalid vesselhandle: " + vesselhandle)
    
    (nodeid, vesselname) = vesselhandle.split(":")
    # Raises DoesNotExistError if there is no such node/vessel.
    vessel = maindb.get_vessel(nodeid, vesselname)
    vessel_list.append(vessel)
    
  return vessel_list


  


# Not logging the function call for now.
def get_vessel_infodict_list(vessel_list):
  """
  <Purpose>
    Convert a list of Vessel objects into a list of vessel infodicts.
    An "infodict" is a dictionary of vessel information that contains data
    which is safe for public display.
  <Arguments>
    vessel_list
      A list of Vessel objects.
  <Exceptions>
    None
  <Side Effects>
    None
  <Returns>
    A list of vessel infodicts.
  """
  infodict_list = []
  
  for vessel in vessel_list:
    vessel_info = {}
    
    vessel_info["node_id"] = maindb.get_node_identifier_from_vessel(vessel)
    node = maindb.get_node(vessel_info["node_id"])
    
    vessel_info["node_ip"] = node.last_known_ip
    vessel_info["node_port"] = node.last_known_port
    vessel_info["vessel_id"] = vessel.name
    
    vessel_info["handle"] = vessel_info["node_id"] + ":" + vessel.name
    
    date_expires = vessel.date_expires
    if date_expires is None:
      # something has gone wrong in the DB, date_expires should never be NULL for an active vessel.
      vessel_info["expires_in"] = "Unknown"
    else:
      expires_in_timedelta = (vessel.date_expires - datetime.datetime.now()).seconds
      expires_in_hours = expires_in_timedelta / (60 * 60)
      expires_in_minutes = (expires_in_timedelta / (60)) - (expires_in_hours * 60)
      #expires_in_seconds = expires_in_timedelta - (expires_in_minutes * 60) - (expires_in_hours * 60 * 60)
      
      print "*" * 60
      print "date_expires: ", date_expires
      print "expires_in_timedelta: ", expires_in_timedelta
      print "expires_in_hours: ", expires_in_hours
      print "expires_in_minutes: ", expires_in_minutes
      print "formatted string: " + str(expires_in_hours) + "h " + str(expires_in_minutes) + "m"
      
      if expires_in_hours < 0 or expires_in_minutes < 0:
        # we shouldn't ever print this message, as no expired 
        # vessels should be returned from the interface 
        vessel_info["expires_in"] = "Expired"
      elif expires_in_hours == 0:
        vessel_info["expires_in"] = str(expires_in_minutes) + "m "
      else:
        vessel_info["expires_in"] = str(expires_in_hours) + "h " + str(expires_in_minutes) + "m"
      
    infodict_list.append(vessel_info)
    
  return infodict_list





def get_total_vessel_credits(geniuser):
  """
  <Purpose>
    Determine the total number of vessels the user is allowed to acquire,
    regardless of how many they have already acquired.
  <Arguments>
    geniuser
      The GeniUser whose total vessel credit count is wanted.
  <Exceptions>
    None
  <Side Effects>
    None
  <Returns>
    The maximum number of vessels the user is allowed to acquire.
  """
  return maindb.get_user_total_vessel_credits(geniuser)

