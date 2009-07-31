"""
<Program>
  nodemanager.py

<Started>
  28 June 2009

<Author>
  Justin Cappos
  Justin Samuel

<Purpose>
  This is the nodemanager api for seattlegeni. All nodemanager communication
  that needs to be done by seattlegeni should do it through this module.
  
  Before using other functions in this module, the function init_nodemanager()
  must be called first.
  
  There are two types of functions in this module:
    1. Functions that do not require signed nodemanager communication.
    2. Functions that do require signed nodemanager communication.
    
  The functions that require signed nodemanager communication require that
  you pass in a node handle as the first argument. You can get that node
  handle by calling get_node_handle().
  
  The only functions that don't require a node handle are currently
  get_node_info() and get_vessel_resources().
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
      Initializes the node manager. Must be called before other operations.
    <Arguments>
      None
    <Exceptions>
      It is possible for a time error to be thrown (which is fatal).
    <Side Effects>
      This function contacts a NTP server and gets the current time.
      This is needed for the crypto operations that we do later.
      This uses UDP port 23421.
    <Returns>
      None
  """
  time_updatetime(23421)





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
    nmhandle = nmclient_createhandle(ip, port)
    nodeinfo = nmclient_getvesseldict(nmhandle)
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
    nmhandle = nmclient_createhandle(ip, port)
    resourcedata = nmclient_rawsay(nmhandle, "GetVesselResources", vesselname)  
    resourcesdict["usableports"] = _get_vessel_usableports(resourcedata)
    nmclient_destroyhandle(nmhandle)
    
  except NMClientException:
    nodestr = str((ip, port))
    message = "Failed to communicate with node " + nodestr + ": "
    raise NodemanagerCommunicationError(message + traceback.format_exc())
  
  return resourcesdict





def get_node_handle(nodeid, ip, port, pubkeystring, privkeystring):
  assert_str(nodeid)
  assert_str(ip)
  assert_int(port)
  assert_str(pubkeystring)
  assert_str(privkeystring)
  
  return (nodeid, ip, port, pubkeystring, privkeystring)





def change_users(nodehandle, vesselname, userkeylist):
  assert_str(vesselname)
  assert_list_of_str(userkeylist)
  
  _do_signed_call(nodehandle, 'ChangeUsers', vesselname, '|'.join(userkeylist))





def reset_vessel(nodehandle, vesselname):
  assert_str(vesselname)
  
  _do_signed_call(nodehandle, 'ResetVessel', vesselname)





def change_owner(nodehandle, vesselname, ownerkey):
  assert_str(vesselname)
  assert_str(ownerkey)
  
  # TODO: are these the correct arguments for ChangeOwner?
  _do_signed_call(nodehandle, 'ChangeOwner', vesselname, ownerkey)





def split_vessel(nodehandle, vesselname, desiredresourcedata):
  assert_str(vesselname)
  assert_str(desiredresourcedata)
  
  # TODO: are these the correct arguments for SplitVessel?
  _do_signed_call(nodehandle, 'SplitVessel', vesselname, desiredresourcedata)





def join_vessels(nodehandle, firstvesselname, secondvesselname):
  assert_str(firstvesselname)
  assert_str(secondvesselname)
  
  # TODO: are these the correct arguments for JoinVessels?
  # TODO: need to return something, I believe.
  _do_signed_call(nodehandle, 'JoinVessels', firstvesselname, secondvesselname)





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
      None.
  """
  (nodeid, ip, port, pubkeystring, privkeystring) = nodehandle
  
  try:
    nmhandle = nmclient_createhandle(ip, port)
  
    myhandleinfo = nmclient_get_handle_info(nmhandle)
    myhandleinfo['publickey'] = rsa_string_to_publickey(pubkeystring)
    myhandleinfo['privatekey'] = rsa_string_to_privatekey(privkeystring)
    nmclient_set_handle_info(nmhandle, myhandleinfo)
  
    nmclient_signedsay(nmhandle, *callargs)
    
    nmclient_destroyhandle(nmhandle)
    
  except NMClientException:
    nodestr = str((nodeid, ip, port))
    message = "Failed to communicate with node " + nodestr + ": "
    raise NodemanagerCommunicationError(message + traceback.format_exc())
  
