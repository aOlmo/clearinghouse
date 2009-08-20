
# Warning: settings must be imported and the database values modified before
# anything else is imported. Failure to do this first will result in django
# trying to create a test mysql database.
from seattlegeni.website import settings

# Do not change the DATABASE_ENGINE. We want to be sure that sqlite3 is used
# for tests.
settings.DATABASE_ENGINE = 'sqlite3'
settings.TEST_DATABASE_NAME = 'test_seattlegeni'




import django.db

import django.test.utils
from django.db import transaction

from seattlegeni.common.api import backend
from seattlegeni.common.api import maindb

from seattlegeni.common.exceptions import *

from seattlegeni.node_state_transitions import mockutil
from seattlegeni.node_state_transitions import node_transition_lib
from seattlegeni.node_state_transitions import transition_canonical_to_onepercentmanyevents
from seattlegeni.node_state_transitions import transition_onepercentmanyevents_to_onepercentmanyevents

from seattle import repyhelper
from seattle import repyportability

repyhelper.translate_and_import("rsa.repy")





testusername = "testuser"

node_ip = "127.0.0.1"
node_port = 1224
node_address = node_ip + ":" + str(node_port)

nodeid_key = {"e" : 1, "n" : 2}
nodeid_key_str = str(nodeid_key["e"]) + " " + str(nodeid_key["n"])

donor_key = {"e" : 3, "n" : 4}
donor_key_str = str(donor_key["e"]) + " " + str(donor_key["n"])

per_node_key = {"e" : 5, "n" : 6}
per_node_key_str = str(per_node_key["e"]) + " " + str(per_node_key["n"])

extra_vessel_name = "v1"



# Create a dictionary that has the string representations of the same keys.
# This is useful in testing, too.
statekeystrings = {}

for keyname in range(len(node_transition_lib.known_transition_states)):
  statekeystrings[keyname] = rsa_publickey_to_string(node_transition_lib.known_transition_states[keyname])


# Use our mockutil helper functions to mock out a few simple things.

mockutil.mock_transitionlib_do_advertise_lookup([node_address])

vessels_dict = {}
vessels_dict[extra_vessel_name] = {"userkeys" : [node_transition_lib.acceptdonationpublickey],
                                   "ownerkey" : donor_key,
                                   "ownerinfo" : "",
                                   "status" : "",
                                   "advertise" : True}
vessels_dict["vessel_non_seattlegeni"] = {"userkeys" : [node_transition_lib.acceptdonationpublickey],
                                   "ownerkey" : donor_key,
                                   "ownerinfo" : "",
                                   "status" : "",
                                   "advertise" : True}
vessels_dict["random_vessel"] = {"userkeys" : ["some random key"],
                                   "ownerkey" : donor_key,
                                   "ownerinfo" : "",
                                   "status" : "",
                                   "advertise" : True}

mockutil.mock_nodemanager_get_node_info(nodeid_key, "10.0test", vessels_dict)

mockutil.mock_lockserver_calls()

mockutil.mock_backend_generate_key([per_node_key_str])

mockutil.mock_nodemanager_get_vesselresources()


# We manually mock out functions that we want to make part of our test.
# That is, we want to ensure that these functions are called the correct
# number of times with the correct arguments.

# How many times backend.set_vessel_owner_key() has been called.
set_vessel_owner_key_call_count = 0

def _mock_set_vessel_owner_key(node, vesselname, old_ownerkey, new_ownerkey):
  
  global set_vessel_owner_key_call_count
  
  print "[_mock_set_vessel_owner_key] called: ", node, vesselname, old_ownerkey, new_ownerkey
  
  assert(node == maindb.get_active_nodes()[0])
  assert(vesselname == extra_vessel_name)
  assert(old_ownerkey == donor_key_str)
  assert(new_ownerkey == per_node_key_str)
                       
  set_vessel_owner_key_call_count += 1
  

backend.set_vessel_owner_key = _mock_set_vessel_owner_key



#How many times backend.split_vessel() has been called 
split_vessel_call_count = 0

def _mock_split_vessel(node, vesselname, resource_data):

  global split_vessel_call_count

  print "[_mock_split_vessel] called: ", node, vesselname, resource_data

  assert(node == maindb.get_active_nodes()[0])
  assert(vesselname == extra_vessel_name)

  split_vessel_call_count += 1
  return (vesselname, "new_vessel"+str(split_vessel_call_count))

backend.split_vessel = _mock_split_vessel



# How many times backend.set_vessel_user_keylist() has been called.
set_vessel_user_keylist_call_count = 0

def _mock_set_vessel_user_keylist(node, vesselname, userkeylist):
  
  global set_vessel_user_keylist_call_count
  global vessels_dict

  print "[_mock_set_vessel_user_keylist] called: ", node, vesselname, userkeylist
  
  assert(node == maindb.get_active_nodes()[0])
  #assert(vesselname == extra_vessel_name)
  #assert(userkeylist == [_mock_pubkey_to_string(node_transition_lib.canonicalpublickey)])

  set_vessel_user_keylist_call_count += 1

  vessels_dict[extra_vessel_name]['userkeys'] = userkeylist
  mockutil.mock_nodemanager_get_node_info(nodeid_key, "10.0test", vessels_dict)

backend.set_vessel_user_keylist = _mock_set_vessel_user_keylist



#mock up for pubkey to string
def _mock_pubkey_to_string(pubkey):
  pub_string = str(pubkey['e'])+" "+str(pubkey['n'])  
  return pub_string 
    

node_transition_lib._do_rsa_publickey_to_string = _mock_pubkey_to_string


def setup_test():

  django.test.utils.setup_test_environment()
  
  # Creates a new test database and runs syncdb against it.
  django.db.connection.creation.create_test_db()

  # Create a user who has the donation key.
  maindb.create_user(testusername, "password", "example@example.com", "affiliation", "10 11", "2 2 2", donor_key_str)




def teardown_test():
  
  # We aren't going to use any database again in this script, so we give django
  # an empty database name to restore as the value of settings.DATABASE_NAME.
  old_database_name = ''
  django.db.connection.creation.destroy_test_db(old_database_name)
  
  django.test.utils.teardown_test_environment()




def run_onepercent_test():

  onepercentmanyevents_resource_fd = file("onepercentmanyevents.resources")
  onepercentmanyevents_resourcetemplate = onepercentmanyevents_resource_fd.read()
  onepercentmanyevents_resource_fd.close()

  global set_vessel_owner_key_call_count
  global set_vessel_user_keylist_call_count
  set_vessel_owner_key_call_count = 0
  set_vessel_user_keylist_call_count = 0

  transitionlist = [(("canonical_state", node_transition_lib.canonicalpublickey), ("movingto_onepercent_state",
                   node_transition_lib.movingtoonepercentmanyeventspublickey),
                   node_transition_lib.noop, node_transition_lib.noop),

                   (("movingto_onepercent_state", node_transition_lib.movingtoonepercentmanyeventspublickey),
                   ("onepercentmanyevents_state", node_transition_lib.onepercentmanyeventspublickey),
                   transition_canonical_to_onepercentmanyevents.onepercentmanyevents_divide, 
                   node_transition_lib.noop,onepercentmanyevents_resourcetemplate),

                   (("movingto_onepercent_state", node_transition_lib.movingtoonepercentmanyeventspublickey),
                   ("canonical_state", node_transition_lib.canonicalpublickey), node_transition_lib.combine_vessels,
                   node_transition_lib.noop, node_transition_lib.movingtoonepercentmanyeventspublickey)]


  transition_results = node_transition_lib.do_one_processnode_run(transitionlist, "startstatename", 1)

  for i in range(2):
    (success_count, failure_count) = transition_results[i]
    assert(success_count == 1)
    assert(failure_count == 0)

  #not that this should have 0 success and 1 fail, as this is the case if the node failed to go to 
  #onepercentmanyevents state.
  (success_count, failure_count) = transition_results[2]
  assert(success_count == 0)
  assert(failure_count == 1)  

  active_nodes_list = maindb.get_active_nodes()
  vessel_list_per_node = maindb.get_vessels_on_node(active_nodes_list[0])

  assert(len(active_nodes_list) == 1)
  assert(active_nodes_list[0].node_identifier == nodeid_key_str)
  assert(active_nodes_list[0].last_known_ip == node_ip)
  assert(active_nodes_list[0].last_known_port == node_port)
  assert(active_nodes_list[0].extra_vessel_name == extra_vessel_name)

  testuser = maindb.get_user(testusername)
  donations_list = maindb.get_donations_by_user(testuser)

  assert(len(donations_list) == 1)
  assert(donations_list[0].node == active_nodes_list[0])
  assert(set_vessel_owner_key_call_count == 0)
 
  #2 calls for changing the state of the extra vessel, and
  #9 calls for setting the new vessels userkeys to [] when
  #new vessels are created by split_vessels
  assert(set_vessel_user_keylist_call_count == 11)

  #testing to see if the vessels exist after splitting
  assert(split_vessel_call_count == 9)
  assert(len(vessel_list_per_node) == 9)



def run_update_db_test():

  mockutil.mock_nodemanager_get_node_info(nodeid_key, "10.0test_new", vessels_dict)

  global set_vessel_owner_key_call_count
  global set_vessel_user_keylist_call_count
  set_vessel_owner_key_call_count = 0
  set_vessel_user_keylist_call_count = 0

  #make the node inactive and make sure that update_db changes to active
  current_nodeobject = maindb.get_active_nodes()[0]
  current_nodeobject.is_active = False
  current_nodeobject.save()

  try:
    transaction.commit()
  except transaction.TransactionManagementError:
    pass



  #try the onepercentmanyevents to onepercentmanyevents test
  transitionlist = [(("onepercentmanyevents_state", node_transition_lib.onepercentmanyeventspublickey),
                   ("onepercentmanyevents_state", node_transition_lib.onepercentmanyeventspublickey),
                   transition_onepercentmanyevents_to_onepercentmanyevents.update_database, 
                   node_transition_lib.noop, transition_onepercentmanyevents_to_onepercentmanyevents.update_database_node)]

  transition_results = node_transition_lib.do_one_processnode_run(transitionlist, "startstatename", 1)

  (success_count, failure_count) = transition_results[0]
  assert(success_count == 1)
  assert(failure_count == 0)

  active_nodes_list = maindb.get_active_nodes()
  vessel_list_per_node = maindb.get_vessels_on_node(active_nodes_list[0])

  assert(len(active_nodes_list) == 1)
  assert(active_nodes_list[0].node_identifier == nodeid_key_str)
  assert(active_nodes_list[0].last_known_ip == node_ip)
  assert(active_nodes_list[0].last_known_port == node_port)
  assert(active_nodes_list[0].extra_vessel_name == extra_vessel_name)
  assert(active_nodes_list[0].last_known_version == "10.0test_new")

  testuser = maindb.get_user(testusername)
  donations_list = maindb.get_donations_by_user(testuser)

  assert(len(donations_list) == 1)
  assert(donations_list[0].node == active_nodes_list[0])
  assert(set_vessel_owner_key_call_count == 0)

  #only one call to set_vessel_user_keylist() should be called
  assert(set_vessel_user_keylist_call_count == 1)

  #testing to see if the vessels exist after splitting
  assert(split_vessel_call_count == 9)
  assert(len(vessel_list_per_node) == 9)




def run_test():

  transitionlist = []
  
  transitionlist.append((("startstatename", node_transition_lib.acceptdonationpublickey),
                        ("endstatename", node_transition_lib.canonicalpublickey),
                         node_transition_lib.noop,
                         node_transition_lib.noop))
  
  (success_count, failure_count) = node_transition_lib.do_one_processnode_run(transitionlist, "startstatename", 1)[0]
  
  assert(success_count == 1)
  assert(failure_count == 0)
  
  active_nodes_list = maindb.get_active_nodes()

  assert(len(active_nodes_list) == 1)
  assert(active_nodes_list[0].node_identifier == nodeid_key_str)
  assert(active_nodes_list[0].last_known_ip == node_ip)
  assert(active_nodes_list[0].last_known_port == node_port)
  assert(active_nodes_list[0].extra_vessel_name == extra_vessel_name)

  testuser = maindb.get_user(testusername)
  donations_list = maindb.get_donations_by_user(testuser)

  assert(len(donations_list) == 1)
  assert(donations_list[0].node == active_nodes_list[0])  
  assert(set_vessel_owner_key_call_count == 1)
  assert(set_vessel_user_keylist_call_count == 1)
  




if __name__ == "__main__":
  setup_test()
  try:
    run_test()
    run_onepercent_test()
    run_update_db_test()
  finally:
    teardown_test()

