"""
<Program>
  nodemanager.py

<Started>
  28 June 2009

<Author>
  Justin Cappos
  Justin Samuel

<Purpose>
  This is the nodemanager api for seattlegeni.
  
  Unless you are are developing the backend server, all you will use this
  module for is to first call init_nodemanager() and then to call either of
  these two functions:
  
    * get_node_info()
    * get_vessel_resources()
  
  You will not be able to use any of the other functions in this module from
  most code because you will not have access to the private owner keys for the
  node. Only the backend should be accessing the private owner keys. That is,
  if you need to change the node state, use the backend api, not this api.
  
  Information for using the other functions:
  
  If you are developing the backend_daemon itself, then you have a legitimate
  reason to be calling the other functions in this module which can change the
  node state. To use those, you will first call init_nodemanager() and then do
  the following to use any of the functions that change node state:
  
    1. Call get_node_handle() to obtain a node handle that can be passed to
       the other functions in this module.
    2. Call any of the other functions in this module, passing the node handle
       as the first argument.
"""

import traceback

from seattlegeni.common.util.assertions import *

from seattlegeni.common.exceptions import *

from seattle import repyhelper
from seattle import repyportability

repyhelper.translate_and_import("listops.repy")
repyhelper.translate_and_import("nmclient.repy")
repyhelper.translate_and_import("time.repy")





def init_nodemanager():
  """
    <Purpose>
      Initializes the nodemanager api. Must be called before other operations.
    <Arguments>
      None
    <Exceptions>
      TimeUpdateError
        If unable to update time.
    <Side Effects>
      This function contacts a NTP server and gets the current time.
      This is needed for the crypto operations that we do later.
      This uses UDP port 23421.
    <Returns>
      None
  """
  try:
    time_updatetime(23421)
  except TimeError:
    # We don't want to ignore this, nor do we want to let an exception defined
    # in a repy module trickle up outside of this module, nor do we want to call
    # it an InternalError just in case it's considered non-fatal at some point
    # (because we generally don't want people catching InternalError because
    # they're bound to catch more then they intended if they do that). So, we
    # use a seattlegeni exception just for this situation. 
    raise TimeUpdateError("Failed to perform time_updatetime() in init_nodemanager(): " + 
                          traceback.format_exc())




def get_node_info(ip, port):
  """
  <Purpose>
    Query a nodemanager for information about it.
  <Arguments>
    ip
      The ip address of of the nodemanager.
    port
      The port the nodemanager is listening on.
  <Exceptions>
    NodemanagerCommunicationError
      If we cannot communicate with a nodemanager at the specified ip and port.
  <Side Effects>
    None
  <Returns>
    A dictionary as returned by nmclient_getvesseldict(). This is a dictionary
    that may have the following keys:
      version
      nodename
      nodekey
      vessels (a dict where the keys are the vessel names and the values are dict's)
        [firstvesselname]
          userkeys
          ownerkey
          ownerinfo
          status
          advertise
        [secondvesselname]
          ...
  """
  assert_str(ip)
  assert_int(port)
  
  try:
    # This can raise an NMClientException, but the handle won't be stored in
    # the nmclient module if it does so we don't have to clean it up.
    nmhandle = nmclient_createhandle(ip, port)

    # Be sure to clean up the handle.    
    try:
      nodeinfo = nmclient_getvesseldict(nmhandle)
    finally:
      nmclient_destroyhandle(nmhandle)
    
  except NMClientException:
    nodestr = str((ip, port))
    message = "Failed to communicate with node " + nodestr + ": "
    raise NodemanagerCommunicationError(message + traceback.format_exc())
  
  return nodeinfo





def _get_vessel_usableports(resourcedata):
  """
  A helper function for get_vessel_resources().
  Finds the list of ports where the resource contains both connport and messport.
  """
  # I think this code could stand to be in nmclient.repy.

  connports = []
  messports = []

  for line in resourcedata.split('\n'):

    if line.startswith('resource'):
      # Ignore the word "resource" and any comments at the end.
      (resourcetype, value) = line.split()[1:3]
      if resourcetype == 'connport':
        # We do int(float(x)) because value might be a string '13253.0'
        connports.append(int(float(value)))
      if resourcetype == 'messport':
        messports.append(int(float(value)))

  return listops_intersect(connports, messports)





def get_vessel_resources(ip, port, vesselname):
  """
  <Purpose>
    Query a nodemanager for information about a vessel's resources. Currently
    only obtains information about usableports, but can be expanded to include
    more information as needed.
  <Arguments>
    ip
      The ip address of of the nodemanager.
    port
      The port the nodemanager is listening on.
    vessel
      The vessel whose resource information we want.
  <Exceptions>
    NodemanagerCommunicationError
      If we cannot communicate with a nodemanager at the specified ip and port.
  <Side Effects>
    None
  <Returns>
    A dictionary that has the following keys:
      usableports -- the value of this key is a list of ports that the vessel
                     has available as both a connport and a messport.
  """
  assert_str(ip)
  assert_int(port)
  assert_str(vesselname)
  
  resourcesdict = {}
  
  try:
    # This can raise an NMClientException, but the handle won't be stored in
    # the nmclient module if it does so we don't have to clean it up.
    nmhandle = nmclient_createhandle(ip, port)
    
    # Be sure to clean up the handle.
    try:
      resourcedata = nmclient_rawsay(nmhandle, "GetVesselResources", vesselname)  
    finally:
      nmclient_destroyhandle(nmhandle)
    
    resourcesdict["usableports"] = _get_vessel_usableports(resourcedata)
    
    
  except NMClientException:
    nodestr = str((ip, port))
    message = "Failed to communicate with node " + nodestr + ": "
    raise NodemanagerCommunicationError(message + traceback.format_exc())
  
  return resourcesdict





def get_node_handle(nodeid, ip, port, pubkeystring, privkeystring):
  """
  <Purpose>
    Obtain a node handle that can be used with the node-state-changing
    functions in this module.
  <Arguments>
    nodeid
      The node's id (a.k.a. "nodekey").
    ip
      The ip address of of the nodemanager.
    port
      The port the nodemanager is listening on (an int or long).
    pubkeystring
      The public key string of the ownerkey that will be used for any signed
      nodemanager communication.
    privkeystring
      The private key string of the ownerkey that will be used for any signed
      nodemanager communication.
  <Exceptions>
    None
  <Side Effects>
    None
  <Returns>
    An opaque object that can be passed as the node handle to other functions
    in this module.
  """
  assert_str(nodeid)
  assert_str(ip)
  assert_int(port)
  assert_str(pubkeystring)
  assert_str(privkeystring)
  
  return (nodeid, ip, port, pubkeystring, privkeystring)





def change_users(nodehandle, vesselname, userkeylist):
  """
  <Purpose>
    Perform a ChangeUsers call on a vessel.
  <Arguments>
    nodehandle
      A node handle obtained through a call to get_node_handle().
    vesselname
      The name of the vessel.
    userkeylist
      A list of public key strings which are the user keys to be set on the
      vessel.
  <Exceptions>
    NodemanagerCommunicationError
      If we cannot communicate with a nodemanager or the request fails.
  <Side Effects>
    The user key list of the vessel has been replaced.
  <Returns>
    None
  """
  assert_str(vesselname)
  assert_list_of_str(userkeylist)
  
  _do_signed_call(nodehandle, 'ChangeUsers', vesselname, '|'.join(userkeylist))





def reset_vessel(nodehandle, vesselname):
  """
  <Purpose>
    Perform a ResetVessel call on a vessel.
  <Arguments>
    nodehandle
      A node handle obtained through a call to get_node_handle().
    vesselname
      The name of the vessel.
  <Exceptions>
    NodemanagerCommunicationError
      If we cannot communicate with a nodemanager or the request fails.
  <Side Effects>
    The vessel has been reset.
  <Returns>
    None
  """
  assert_str(vesselname)
  
  _do_signed_call(nodehandle, 'ResetVessel', vesselname)





def change_owner(nodehandle, vesselname, ownerkey):
  """
  <Purpose>
    Perform a ChangeOwner call on a vessel.
  <Arguments>
    nodehandle
      A node handle obtained through a call to get_node_handle().
    vesselname
      The name of the vessel.
    ownerkey
      The public key to set as the owner key of the vessel.
  <Exceptions>
    NodemanagerCommunicationError
      If we cannot communicate with a nodemanager or the request fails.
  <Side Effects>
    The owner key of the vessel has been replaced. Future requests that modify
    this vessel will need to use this new owner key.
  <Returns>
    None
  """
  assert_str(vesselname)
  assert_str(ownerkey)
  
  _do_signed_call(nodehandle, 'ChangeOwner', vesselname, ownerkey)





def split_vessel(nodehandle, vesselname, desiredresourcedata):
  """
  <Purpose>
    Perform a SplitVessel call on a vessel.
  <Arguments>
    nodehandle
      A node handle obtained through a call to get_node_handle().
    vesselname
      The name of the vessel.
    desiredresourcedata
      A string of resourcedata that specifies the resources of a new vessel to
      create when splitting the existing vessel. This resourcedata has the
      format of a resources file.
  <Exceptions>
    NodemanagerCommunicationError
      If we cannot communicate with a nodemanager or the request fails.
  <Side Effects>
    The vesselname no longer exists. It has been split into two new vessels,
    one of which has the resources specified in the desiredresourcedata.
  <Returns>
    A tuple of the two new vessel names that resulted from the split. The
    first element of the tuple is the name of the vessel that has the
    leftover resources from the split. The second element of the tuple is
    the name of the vessel that has the exact resources specified in the
    desiredresourcedata.
  """
  assert_str(vesselname)
  assert_str(desiredresourcedata)
  
  splitvesselretval = _do_signed_call(nodehandle, 'SplitVessel', vesselname, desiredresourcedata)
  
  # Get the new vessel names. The "left" vessel has the leftovers, the 
  # "right" is of the size requested.
  leftovervesselname, exactvesselname = splitvesselretval.split()

  return (leftovervesselname, exactvesselname)





def join_vessels(nodehandle, firstvesselname, secondvesselname):
  """
  <Purpose>
    Perform a JoinVessels call on two vessels.
  <Arguments>
    nodehandle
      A node handle obtained through a call to get_node_handle().
    firstvesselname
      The name of the first vessel to be joined.
    secondvesselname
      The name of the second vessel to be joined.
  <Exceptions>
    NodemanagerCommunicationError
      If we cannot communicate with a nodemanager or the request fails.
  <Side Effects>
    Neither firstvesselname nor secondvesselname exist. The have been joined
    together into a vessel that has a new name.
  <Returns>
    The name of the new vessel that has been created by joining together the
    two vessels.
  """
  assert_str(firstvesselname)
  assert_str(secondvesselname)
  
  combinedvesselname = _do_signed_call(nodehandle, 'JoinVessels', firstvesselname, secondvesselname)

  return combinedvesselname





def _do_signed_call(nodehandle, *callargs):
  """
    <Purpose>
      Performs an action that requires authentication on a remote node.
    <Arguments>
      ip:
        The node's IP address (a string)
      port:
        The port that the node manager is running on (an int)
      pubkeystring:
        The public key used for authentication
      privkeystring:
        The private key used for authentication
      *callargs:
        The arguments to give the node.   The first argument will usually be
        the call type (i.e. "ChangeUsers")
    <Exceptions>
      Exception / NMClientException are raised when the call fails.   
    <Side Effects>
      Whatever side effects the call has on the remote node.
    <Returns>
      None
  """
  (nodeid, ip, port, pubkeystring, privkeystring) = nodehandle
  
  try:
    # This can raise an NMClientException, but the handle won't be stored in
    # the nmclient module if it does so we don't have to clean it up.
    nmhandle = nmclient_createhandle(ip, port)
  
    # Be sure to clean up the handle.    
    try:
      myhandleinfo = nmclient_get_handle_info(nmhandle)
      myhandleinfo['publickey'] = rsa_string_to_publickey(pubkeystring)
      myhandleinfo['privatekey'] = rsa_string_to_privatekey(privkeystring)
      nmclient_set_handle_info(nmhandle, myhandleinfo)
    
      return nmclient_signedsay(nmhandle, *callargs)
      
    finally:
      nmclient_destroyhandle(nmhandle)
    
  except NMClientException:
    nodestr = str((nodeid, ip, port))
    message = "NodeManager request failed with node " + nodestr + ": "
    raise NodemanagerCommunicationError(message + traceback.format_exc())
  
