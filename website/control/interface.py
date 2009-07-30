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
"""

from seattlegeni.common.exceptions import *

from seattlegeni.common.api import backend
from seattlegeni.common.api import keygen
from seattlegeni.common.api import lockserver
from seattlegeni.common.api import maindb

from seattlegeni.common.util import crypto

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
      Can't be an empty string or will result in a ProgrammerError.
    password
    email
    affiliation
    pubkey
      Optional. If not provided, a key pair will be generated for this user.
  <Exceptions>
    UsernameAlreadyExistsError
      If there is already a user with the specified username.
    
    TODO: InvalidUsernameError
    TODO: InvalidPasswordError
    TODO: InvalidEmailError
    TODO: InvalidAffiliationError
  <Side Effects>
    The user record in the django db is created as well as a user record in the
    corresponding user profile table that stores our custom information. A port
    will be assigned to the user and the user's donation keys will be set.
  <Returns>
    GeniUser instance (our GeniUser model, not the django User) corresponding to the
    newly registered user.
  """
  assert_str(username)
  assert_str(password)
  assert_str(email)
  assert_str(affiliation)
  assert_str_or_none(pubkey)
  
  # TODO: check that we like the content of the fields (not just that they are
  #       of valid types) and raise specific exceptions such as 
  #       InvalidUsernameError if we don't like them.
  
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
      if not crypto.is_valid_pubkey_string(pubkey):
        raise InvalidPublicKeyError
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
  




@log_function_call
def login_user(request, geniuser):
  """
  <Purpose>
    Log in a user to a session. This allows future requests that are part of
    same session to obtain the user object through calls to get_logged_in_user().
    This function should not be used through the xmlrpc frontend as there is
    no concept of the session there.
  <Arguments>
    request
      The HttpRequest object of the user's request through the frontend.
    geniuser
      The GeniUser object of the user to be logged in.
  <Exceptions>
    None
  <Side Effects>
    Associates the user with a session corresponding to the request.
  <Returns>
    None
  """
  assert_geniuser(geniuser)
  
  # JCS: I haven't tested this. It may not work as intended.
  request.session["username"] = geniuser.username





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
  # JCS: I haven't tested this. It may not work as intended.
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
    DoesNotExistError
      If the user does not exist by the time we hold the user lock.
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
    # Raises a DoesNotExistError if the user doesn't exist anymore.
    # We don't use the user object we retrieve because we want the
    # object passed in to the function to reflect the deletion of the key.
    # That is, we want the object passed in to have the user_privkey be None
    # when this function returns.
    maindb.get_user(geniuser.username)
    
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
      The number of vessels to acquire (an integer).
    vesseltype
      The type of vessels to acquire. One of either 'lan', 'wan', or 'rand'.
  <Exceptions>
    DoesNotExistError
      If the user doesn't exist anymore after we have acquired the user lock.
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
  assert_int(vesselcount)
  assert_str(vesseltype)

  # Lock the user.
  lockserver_handle = lockserver.create_lockserver_handle()
  lockserver.lock_user(lockserver_handle, geniuser.username)
  
  try:
    # Make sure the user still exists now that we hold the lock. Also makes
    # sure that we see any changes made to the user before we obtained the lock.
    # Raises a DoesNotExistError if the user doesn't exist anymore.
    geniuser = maindb.get_user(geniuser.username)
    
    # Ensure the user is allowed to acquire these resources. This call will
    # raise an InsufficientUserResourcesError if the additional vessels would
    # cause the user to be over their limit.
    maindb.require_user_can_acquire_resources(geniuser, vesselcount)
    
    if vesseltype == 'wan':
      acquired_list = vessels.acquire_wan_vessels(lockserver_handle, geniuser, vesselcount)
    elif vesseltype == 'lan':
      acquired_list = vessels.acquire_lan_vessels(lockserver_handle, geniuser, vesselcount)
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
    DoesNotExistError
      If the user doesn't exist anymore after we have acquired the user lock.
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
    # Raises a DoesNotExistError if the user doesn't exist anymore.
    geniuser = maindb.get_user(geniuser.username)
    
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
    DoesNotExistError
      If the user doesn't exist anymore after we have acquired the user lock.
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
    # Raises a DoesNotExistError if the user doesn't exist anymore.
    geniuser = maindb.get_user(geniuser.username)
    
    # Get a list of all vessels acquired by the user.
    vessel_list = maindb.get_acquired_vessels(geniuser)
    
    vessels.release_vessels(lockserver_handle, vessel_list)
    
  finally:
    # Unlock the user.
    lockserver.unlock_user(lockserver_handle, geniuser.username)
    lockserver.destroy_lockserver_handle(lockserver_handle)





def get_vessel_list(vesselhandle_list):
  """
  <Exceptions>
    Raises DoesNotExistError
  """
  assert_list_of_str(vesselhandle_list)
  
  vessel_list = []
  
  for vesselhandle in vesselhandle_list:
    if len((vesselhandle.split(":"))) != 2:
      raise InvalidRequestError("Invalid vesselhandle: " + vesselhandle)
    
    (nodeid, vesselname) = vesselhandle.split(":")
    vessel = maindb.get_vessel(nodeid, vesselname)
    vessel_list.append(vessel)
    
  return vessel_list


  


def get_vessel_infodict_list(vessel_list):
  
  infodict_list = []
  
  for vessel in vessel_list:
    vessel_info = {}
    
    vessel_info["node_id"] = maindb.get_node_identifier_from_vessel(vessel)
    node = maindb.get_node(vessel_info["node_ip"])
    
    vessel_info["node_ip"] = node.last_known_ip
    vessel_info["node_port"] = node.last_known_port
    vessel_info["vessel_id"] = vessel.name
    
    vessel_info["handle"] = vessel_info["node_id"] + ":" + vessel.name
    
    infodict_list.append(vessel_info)
    
  return infodict_list

