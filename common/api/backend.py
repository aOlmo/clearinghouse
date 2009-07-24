"""
<Program>
  backend.py

<Started>
  29 June 2009

<Author>
  Justin Samuel

<Purpose>
  This is the API that should be used to interact with the backend XML-RPC
  server. Functions in this module are the only way that other code should
  interact with the backend.
   
  All components of seattlegeni use the backend to perform any nodemanager
  communication that changes the state of a node. ("State" here means
  modifying the node in any way, not "state" as in the "canonical state".)
  If the node only needs to be queried, not modified, then that can be
  done directly using the nodemanager api. This prevents the backend from
  needing to be called for regular querying done by polling daemons yet
  keeps the backend as the sole place where node changing operations
  are performed.
   
  The website uses only four functions in this module:
    acquire_vessel()
    release_vessel()
    generate_key()
    set_vessel_users()
     
  The other functions are used by polling daemons. In order to use the other
  functions, set_backend_authcode() must be called by the script first.
"""


from seattlegeni.common.exceptions import *

from seattlegeni.common.util.decorators import log_function_call



BACKEND_URL = "http://localhost:8000"

backend_authcode = None





# Not using log_function_call so we don't log the authcode.
def set_backend_authcode(authcode):
  """
  Sets the value of the authcode sent to the backend with privileged requests.
  This is needed for the backend to ensure that calls to the privileged
  operations (set_vessel_owner, split_vessel, join_vessel) are allowed.
  """
  global backend_authcode
  backend_authcode = authcode





@log_function_call
def acquire_vessel(geniuser, vessel):
  # TODO: implement
  raise UnableToAcquireResourcesError





@log_function_call
def release_vessel(vessel):
  # TODO: implement
  pass





@log_function_call
def generate_key(keydecription):
  """
  <Purpose>
    Generate a new key pair through the backend. The backend will store the
    private key in the keydb. As of the time of writing this, this method
    is mainly to be used by the website to obtain a donor_pubkey without
    ever having to see the corresponding private key.
  <Arguments>
    keydecription
      A description of what this key is for. This should be specific enough
      to locate where the returned public key is stored in the maindb.
  <Returns>
    The public key part of the key pair.
  """
  # TODO: implement
  return "generate_key() Not implemented"





@log_function_call
def set_vessel_users(vessel):
  # TODO: implement
  pass





@log_function_call
def set_vessel_owner(vessel, pubkey):
  """
  pubkey must be a valid key stored in the keydb.
  """
  # Having this method available to the website means that if the website is
  # compromised, then the attacker can try to change the vessel owner for
  # all vessels. One option would be to require passing to the backend a
  # some form of authorization info to indicate that the client code is
  # authorized to call this function. Instead, let's just make sure we
  # can find the pubkey in the keydb. By doing that check, we'll need to
  # use the keydb api, which is something the website won't be able to do
  # successfully. By doing this, we'll avoid complicating the backend api.

  # TODO: implement





@log_function_call
def split_vessel(vessel, desiredresourcedata):
  """
  <Exceptions>
    Raises ??? if unable to split the vessel because there aren't enough
    resources available to do the split.
  <Returns>
    Returns a tuple of (newvesselname1, newvesselname2) where newvesselname1
    has the leftovers and newvesselname2 is of the size requested.
  """
  # TODO: implement





@log_function_call
def join_vessels(firstvessel, secondvessel):
  """
  The first vessel will retain the user keys and  therefore the state.
  <Returns>
    A string that is the name of the combined vessel (which will turn out to
    be firstvessel).
  """
  # TODO: implement

