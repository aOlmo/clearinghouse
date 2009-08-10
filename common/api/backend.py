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

import socket
import traceback
import xmlrpclib

from seattlegeni.common.exceptions import *

from seattlegeni.common.util.decorators import log_function_call



BACKEND_URL = "http://127.0.0.1:8020"

# This is not a thread-local variable. There isn't any case where one thread
# in a process will have this authcode and another won't. So, we don't make
# the client code pass around a handle just for this.
backend_authcode = None





def _get_backend_proxy():
  return xmlrpclib.ServerProxy(BACKEND_URL)




def _do_backend_request(func, *args):
  try:
    return func(*args)
  except xmlrpclib.Fault:
    raise ProgrammerError("The backend rejected the request: " + traceback.format_exc())
  except xmlrpclib.ProtocolError:
    raise InternalError("Unable to communicate with the backend: " + traceback.format_exc())
  except socket.error:
    raise InternalError("Unable to communicate with the backend: " + traceback.format_exc())





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
  # Acquiring a vessel is just setting the userkeylist to include only this
  # user's key.
  func = _get_backend_proxy().SetVesselUsers
  args = (vessel.node.node_identifier, vessel.name, [geniuser.user_pubkey])
  
  _do_backend_request(func, *args)
    




@log_function_call
def release_vessel(vessel):
  # This is actually a noop. The reason for this is because the backend doesn't
  # perform immediate action because of a released vessel. Instead, the client
  # code will user maindb.record_released_vessel() and the database change
  # resulting from that will cause the cleanup thread in the backend to do
  # anything it needs to do.
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
  func = _get_backend_proxy().GenerateKey
  args = (keydecription,)
  
  return _do_backend_request(func, *args)





@log_function_call
def set_vessel_user_keylist(vessel, userkeylist):
  func = _get_backend_proxy().SetVesselUsers
  args = (vessel.node.node_identifier, vessel.name, userkeylist)
  
  _do_backend_request(func, *args)





@log_function_call
def set_vessel_owner_key(vessel, ownerkey):
  """
  pubkey must be a valid key stored in the keydb.
  """
  # Having this method available to the website means that if the website is
  # compromised, then the attacker can try to change the vessel owner for
  # all vessels. So, we need to authenticate with the backend by including
  # the backend_authcode in the request.

  if backend_authcode is None:
    raise ProgrammerError("You must call set_backend_authcode(authcode) before calling this function.")

  func = _get_backend_proxy().SetVesselOwner
  args = (backend_authcode, vessel.node.node_identifier, vessel.name, ownerkey)
  
  _do_backend_request(func, *args)

  # TODO: the client code needs to update the database to reflect the new owner
  #       key. Need to make this clear in the function docstring.

  



@log_function_call
def split_vessel(vessel, desiredresourcedata):
  """
  <Exceptions>
    Raises ??? if unable to split the vessel because there aren't enough
    resources available to do the split.
  <Returns>
    Returns a tuple of (newvessel1, newvessel2) where newvessel1
    has the leftovers and newvessel2 is of the size requested. These are both
    vessel objects.
  """
  # This seems like a privileged operation, so the backend_authcode must be
  # provided in the request.
  
  if backend_authcode is None:
    raise ProgrammerError("You must call set_backend_authcode(authcode) before calling this function.")
  
  func = _get_backend_proxy().SplitVessel
  args = (backend_authcode, vessel.node.node_identifier, vessel.name, desiredresourcedata)
  
  _do_backend_request(func, *args)
  
  # TODO: the client code needs to update the database to reflect the split.
  #       Need to make this clear in the function docstring.





@log_function_call
def join_vessels(firstvessel, secondvessel):
  """
  The first vessel will retain the user keys and  therefore the state.
  <Returns>
    The firstvessel (a new object that will reflect any database changes since
    the joining of the two vessels).
  """
  # This seems like a privileged operation, so the backend_authcode must be
  # provided in the request.
  
  if backend_authcode is None:
    raise ProgrammerError("You must call set_backend_authcode(authcode) before calling this function.")
  
  func = _get_backend_proxy().JoinVessels
  args = (backend_authcode, firstvessel.node.node_identifier, firstvessel.name, secondvessel.name)
  
  _do_backend_request(func, *args)
  
  # TODO: the client code needs to update the database to reflect the join. 
  #       Need to make this clear in the function docstring.

