
import random

from seattlegeni.common.api import backend
from seattlegeni.common.api import lockserver
from seattlegeni.common.api import nodemanager

from seattlegeni.common.exceptions import *

from seattlegeni.node_state_transitions import node_transition_lib




def mock_transitionlib_do_advertise_lookup(nodeaddress_list_to_return):
  
  def _mock_do_advertise_lookup(state):
    return nodeaddress_list_to_return
  
  node_transition_lib._do_advertise_lookup = _mock_do_advertise_lookup





def mock_nodemanager_get_node_info(nodeid_key, version, vessels_dict):
  
  def _mock_get_node_info(ip, port):
    nodeinfo = {"version" : version,
                "nodename" : "",
                "nodekey" : nodeid_key,
                "vessels" : {}}
    nodeinfo["vessels"] = vessels_dict
    return nodeinfo
  
  nodemanager.get_node_info = _mock_get_node_info





def mock_lockserver_calls():
  
  def _mock_create_lockserver_handle(lockserver_url=None):
    pass
  lockserver.create_lockserver_handle = _mock_create_lockserver_handle
  
  def _mock_destroy_lockserver_handle(lockserver_handle):
    pass
  lockserver.destroy_lockserver_handle = _mock_destroy_lockserver_handle
  
  def _mock_perform_lock_request(request_type, lockserver_handle, user_list=None, node_list=None):
    pass
  lockserver._perform_lock_request = _mock_perform_lock_request




def mock_backend_generate_key(keylist):

  def _mock_generate_key(keydescription):
    return keylist.pop()
  
  backend.generate_key = _mock_generate_key



def mock_nodemanager_get_vesselresources():
  
  def _mock_get_vessel_resources(*args):
    resource_dict={}
    resourcelist = []
    #generate resource list
    for i in range(90):
      resourcelist.append(i)
    resource_dict['usableports'] = resourcelist
    
    return resource_dict

  nodemanager.get_vessel_resources = _mock_get_vessel_resources


