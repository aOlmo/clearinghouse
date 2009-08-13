"""
<Program>
  node_transition_test.py

<Started>
  July 1, 2009

<Author>
  Monzur Muhammad
  monzum@cs.washington.edu

<Purpose>
  To test the node_transition_lib.py thoroughly

<Usage>
  run preparetest.py on an empty folder and copy over this file
  as well as node_transition_lib.py into that folder.
  Then run: python node_transition_test.py
"""


import node_transition_lib
import runonce
import subprocess
import repyhelper
import seattlegeni.common.api.nodemanager
import seattlegeni.common.api.backend

repyhelper.translate_and_import('advertise.repy')
repyhelper.translate_and_import('rsa.repy')


#simulate pass on find_advertised_nodes()
def mock_find_advertised_nodes_pass(*args):
  return True, ['212.235.189.115:1224', '143.225.229.238:1224', '128.195.54.163:1224', '130.161.40.153:1224', '141.22.213.35:1224', '202.38.99.69:1224', '128.252.19.18:1224', '200.0.206.169:1224', '128.135.11.151:1224', '205.211.183.4:1224', '192.42.83.252:1224', '198.133.224.149:1224']


#simulate advertise_lookup return value
def mock_advertise_lookup(*args):
  return ['192.6.10.47:1224']#['212.235.189.115:1224', '143.225.229.238:1224', '128.195.54.163:1224', '130.161.40.153:1224', '141.22.213.35:1224', '202.38.99.69:1224', '12\
#8.252.19.18:1224', '200.0.206.169:1224', '128.135.11.151:1224', '205.211.183.4:1224', '192.42.83.252:1224', '198.133.224.149:1224', '132.68.237.34:1224']


#simulate failure on find_advertised_nodes()
def mock_find_advertised_nodes_fail(*args):
  return False, []


#simulate pass on run_parallel_processes()
def mock_run_parallel_processes_pass(*args):
  return True


#simulate failure on run_parallel_processes()
def mock_run_parallel_processes_fail(*args):
  return False



#mock pass for functions
def mock_general_pass(*args):
  return True


#mock fail for functions
def mock_general_fail(*args):
  return False


#mock exceptions for functions
def mock_general_exception(*args):
  raise ValueError, "Error"


def mock_maindb_getnode(*args):
  return "node1"


def mock_get_pubkey(*args):
  return "node1"


def mock_get_node_info(*args):
  mock_node_info={}
  mock_node_info['version']="0.1z"
  mock_node_info['nodename']="127.0.0.1:1234"
  mock_node_info['nodekey']="node1"
  mock_node_info['vessels']={}
  for i in range(6):
    mock_node_info['vessels']['v'+str(i)]={}
    mock_node_info['vessels']['v'+str(i)]['userkeys']=[mock_get_pubkey()]
    mock_node_info['vessels']['v'+str(i)]['ownerkey']='the owner pubkey'
    mock_node_info['vessels']['v'+str(i)]['status']="live"
    mock_node_info['vessels']['v'+str(i)]['advertise']=True

  return mock_node_info

def main():
  #  node_transition_lib.init_log("nodetransition_test")
  #test_node_transition_script()
  #test_find_advertised_nodes()
  test_whole()

def test_whole():

  node_transition_lib.advertise_lookup_helper = mock_advertise_lookup
  node_transition_lib.rsa_publickey_to_string_helper = mock_get_pubkey  
  node_transition_lib.known_transition_states = [mock_get_pubkey()] 
  node_transition_lib.acceptdonationpublickey = mock_get_pubkey()
  seattlegeni.common.api.backend.set_vessel_user_keylist = mock_general_pass
  seattlegeni.common.api.backend.set_vessel_owner_key = mock_general_pass
  seattlegeni.common.api.nodemanager.get_node_info = mock_get_node_info
  
  nodestate_tuples = [(("starttest_name", "node1"), ("endtest_name", "endtest_publickey"), mock_general_pass, mock_general_pass, "processfunc_args")]
  node_transition_lib.node_transition_script(nodestate_tuples, "transition_script_test", 4)
  


def test_find_advertised_nodes():

  node_transition_lib.log("Starting test on find_advertised_nodes()")
  
  node_transition_lib.advertise_lookup_helper = mock_advertise_lookup
  success, nodelist = node_transition_lib.find_advertised_nodes("test_advertised_lookup", "test_publickey") 

  if success:
    node_transition_lib.log("find_advertised_nodes() test passed")
  
  else:
    node_transition_lib.log("find_advertised_nodes() test failed")


  node_transition_lib.advertise_lookup_helper = mock_general_exception
  success, nodelist = node_transition_lib.find_advertised_nodes("test_advertised_lookup", "test_publickey")

  if not success:
    node_transition_lib.log("advertise_lookup fail test passed")

  else:
    node_transition_lib.log("advertise_lookup fail test failed ")


def test_node_transition_script():

  node_transition_lib.log("Starting Testing on fail on find_advertised_nodes")

  node_transition_lib.find_advertised_nodes = mock_find_advertised_nodes_fail
  node_transition_lib.run_parallel_processes = mock_run_parallel_processes_pass

  nodestate_tuples = [(("starttest_name", "starttest_publickey"), ("endtest_name", "endtest_publickey"), "processfunction", "errorfunction", "processfunc_args")]

  node_transition_lib.node_transition_script(nodestate_tuples, "transition_script_test", 4)

  node_transition_lib.log("Finished Testing find_advertised_nodes fail")
  print "---------------------------------------------------------------------"


  node_transition_lib.log("Starting Testing on fail on run_parallel_process")

  node_transition_lib.find_advertised_nodes = mock_find_advertised_nodes_pass
  node_transition_lib.run_parallel_processes = mock_run_parallel_processes_fail

  nodestate_tuples = [(("starttest_name", "starttest_publickey"), ("endtest_name", "endtest_publickey"), "processfunction", "errorfunction", "processfunc_args")]

  node_transition_lib.node_transition_script(nodestate_tuples, "transition_script_test", 4)

  node_transition_lib.log("Finished Testing run_parallel_processes fail")
  print "---------------------------------------------------------------------"

  node_transition_lib.log("Finished all Tests!!!")


if __name__ == "__main__":
  main()
