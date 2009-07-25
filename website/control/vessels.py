"""
<Program Name>
  vessels.py

<Started>
  July 16, 2009

<Author>
  Justin Samuel

<Purpose>
  Provides utilities for the controller interface (interface.py) to use for
  performing acquisition of different types of vessels as well as release of
  vessels.
"""

from seattlegeni.common.exceptions import *

from seattlegeni.common.api import backend
from seattlegeni.common.api import lockserver
from seattlegeni.common.api import maindb

from seattlegeni.common.util import assertions

from seattlegeni.common.util.decorators import log_function_call





@log_function_call
def acquire_wan_vessels(lockserver_handle, geniuser, vesselcount):
  """
  <Purpose>
    Acquire 'wan' vessels for a geniuser.
  <Arguments>
    lockserver_handle
      The lockserver handle to be used for obtaining node locks.
    geniuser
      The GeniUser the vessels should be acquired for.
    vesselcount
      The number of vessels to acquire.
  <Exceptions>
    UnableToAcquireResourcesError
      If either the user does not not have enough vessel credits to acquire the
      number of vessels they requested or if there are not enough vessels
      available to fulfill the request.
  <Side Effects>
    The vessels are acquired for the user. The database has been updated to
    reflect the acquisition.
  <Returns>
    A list of the vessels that were acquired.
  """
  
  # Get a randomized list of vessels where no two vessels are on the same subnet.
  vessel_list = maindb.get_available_wan_vessels(vesselcount)
  
  return _acquire_vessels_from_list(lockserver_handle, geniuser, vesselcount, vessel_list)





@log_function_call
def acquire_lan_vessels(lockserver_handle, geniuser, vesselcount):
  """
  <Purpose>
    Acquire 'lan' vessels for a geniuser.
  <Arguments>
    lockserver_handle
      The lockserver handle to be used for obtaining node locks.
    geniuser
      The GeniUser the vessels should be acquired for.
    vesselcount
      The number of vessels to acquire.
  <Exceptions>
    UnableToAcquireResourcesError
      If either the user does not not have enough vessel credits to acquire the
      number of vessels they requested or if there are not enough vessels
      available to fulfill the request.
  <Side Effects>
    The vessels are acquired for the user. The database has been updated to
    reflect the acquisition.
  <Returns>
    A list of the vessels that were acquired.
  """
  
  # Get a randomized list that itself contains lists of vessels on the same subnet.
  subnet_vessel_list = maindb.get_available_lan_vessels_by_subnet(vesselcount)
  
  # This case is a little more involved than with wan or rand vessels. If we
  # fail to get the number of desired vessels from one subnet, we need to try
  # another until we are out of subnets to try.
  for vessel_list in subnet_vessel_list:
    try:
      # If we don't hit an exception and return, then we found a subnet where
      # we could acquire all of the requested vessels. So, we're done.
      return _acquire_vessels_from_list(lockserver_handle, geniuser, vesselcount, vessel_list)
    except UnableToAcquireResourcesError:
      # Try the next subnet.
      continue

  # If we made it here, we tried all subnets in our list.
  raise UnableToAcquireResourcesError





@log_function_call
def acquire_rand_vessels(lockserver_handle, geniuser, vesselcount):
  """
  <Purpose>
    Acquire 'rand' vessels for a geniuser.
  <Arguments>
    lockserver_handle
      The lockserver handle to be used for obtaining node locks.
    geniuser
      The GeniUser the vessels should be acquired for.
    vesselcount
      The number of vessels to acquire.
  <Exceptions>
    UnableToAcquireResourcesError
      If either the user does not not have enough vessel credits to acquire the
      number of vessels they requested or if there are not enough vessels
      available to fulfill the request.
  <Side Effects>
    The vessels are acquired for the user. The database has been updated to
    reflect the acquisition.
  <Returns>
    A list of the vessels that were acquired.
  """
  
  # Get a randomized list of vessels where there are no guarantees about whether
  # the list includes wan vessels, lan vessels, vessels on the same subnet, etc.
  vessel_list = maindb.get_available_rand_vessels(vesselcount)
  
  return _acquire_vessels_from_list(lockserver_handle, geniuser, vesselcount, vessel_list)





@log_function_call
def _acquire_vessels_from_list(lockserver_handle, geniuser, vesselcount, vessel_list):
  """
  This function will try to acquire vesselcount vessels from vessel_list.
  If less than vesselcount can be acquired, then the partial set of
  vessels that were acquired will be released by this function before it
  returns.
  
  Returns the list of acquired vessels if successful.
  """

  # Make sure there are sufficient vessels to even try to fulfill the request.
  if len(vessel_list) < vesselcount:
    raise UnableToAcquireResourcesError("There are not enough available vessels to fulfill the request.")
  
  acquired_vessels = []

  for vessel in vessel_list:
    try:
      _do_acquire_vessel(lockserver_handle, geniuser, vessel)
    except UnableToAcquireResourcesError:
      # We don't worry about an individual vessel acquisition failing. We just
      # proceed to try to acquire others to fulfill the request.
      continue
    # We successfully acquired this vessel.
    acquired_vessels.append(vessel)
    # If we've acquired all of the vessels the user wanted, we're done.
    if len(acquired_vessels) == vesselcount:
      return acquired_vessels

  # If we got here, then we didn't acquire the vessels the user wanted. We
  # release these vessels rather than leave the user with a partial set of
  # what they requested.
  release_vessels(acquired_vessels)

  raise UnableToAcquireResourcesError("Failed to acquire enough vessels to fulfill the request")





@log_function_call
def _do_acquire_vessel(lockserver_handle, geniuser, vessel):
  """
  Perform that actual acquisition of the vessel by the user (through the
  backend) and update the database accordingly if the vessel is successfully
  acquired.
  """  
  
  node_id = maindb.get_node_identifier_from_vessel(vessel)

  # Lock the vessel.
  lockserver.lock_node(lockserver_handle, node_id)
  try:
    # TODO: We should query the db now that we hold the lock to find out if the
    #       state of the node/vessel is what we expect.
    
    # This will raise a UnableToAcquireResourcesException if it fails (e.g if
    # the node is down). We want to allow the exception to be passed up to
    # the caller.
    backend.acquire_vessel(geniuser, vessel)
    
    # Update the database to reflect the successful vessel acquisition.
    # TODO: This needs to be committed to the db immediately if we are
    #       releasing the lock on the node here.
    maindb.record_acquired_vessel(geniuser, vessel)
    
    return vessel
    
  finally:
    # Unlock the user.
    lockserver.unlock_node(lockserver_handle, node_id)





@log_function_call
def release_vessels(lockserver_handle, vessel_list):
  """
  <Purpose>
    Release vessels (regardless of which user has acquired them)
  <Arguments>
    lockserver_handle
      The lockserver handle to use for acquiring node locks.
    vessel_list
      A list of vessels to be released.
  <Exceptions>
    None.
  <Side Effects>
    The vessels in the vessel_list are released.
  <Returns>
    None.
  """
  # TODO: check validity of parameters
    
  for vessel in vessel_list:
    _do_release_vessel(lockserver_handle, vessel)





@log_function_call
def _do_release_vessel(lockserver_handle, vessel):
  """
  Obtains a lock on the node the vessel is on and then makes a call to the
  backend to release the vessel.
  """
  
  node_id = maindb.get_node_identifier_from_vessel(vessel)

  # Lock the vessel.
  lockserver.lock_node(lockserver_handle, node_id)
  try:
    # TODO: We should query the db now that we hold the lock to find out if the
    #       state of the node/vessel is what we expect. For example, what if
    #       the vessel was already released before we got the lock and another
    #       user acquired the node before we got the lock?
    
    # This will not raise an exception, even if the node the vessel is on is down.
    backend.release_vessel(vessel)
    
    # Update the database to reflect the release of the vessel.
    # TODO: This needs to be committed to the db immediately if we are
    #       releasing the lock on the node here.
    maindb.record_released_vessel(vessel)
    
  finally:
    # Unlock the user.
    lockserver.unlock_node(lockserver_handle, node_id)

