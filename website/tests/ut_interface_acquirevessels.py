"""
Note that backend.release_vessel() calls that automatically happen when not 
enough of the requested vessels are acquired don't currently need to be
mock'd out because currently that function does nothing.
"""

# The seattlegeni testlib must be imported first.
from seattlegeni.tests import testlib

from seattlegeni.tests import mocklib

from seattlegeni.common.api import maindb

from seattlegeni.common.exceptions import *

from seattlegeni.website.control import interface

import unittest





mocklib.mock_lockserver_calls()





next_nodeid_number = 0

def create_node_and_vessels_with_one_port_each(ip, portlist, is_active=True):
  
  global next_nodeid_number
  next_nodeid_number += 1
  
  nodeid = "node" + str(next_nodeid_number)
  port = 1234
  version = "10.0test"
  owner_pubkey = "1 2"
  extra_vessel_name = "v1"
  
  node = maindb.create_node(nodeid, ip, port, version, is_active, owner_pubkey, extra_vessel_name)

  single_vessel_number = 2

  for vesselport in portlist:
    single_vessel_name = "v" + str(single_vessel_number)
    single_vessel_number += 1
    vessel = maindb.create_vessel(node, single_vessel_name)
    maindb.set_vessel_ports(vessel, [vesselport])
  
  return node





def create_nodes_on_same_subnet(count, portlist_for_vessels_on_each_node, ip_prefix="127.0.0."):
  # Create 'count' nodes on the same subnet and on each node create a vessel
  # with a single port for each port in 'portlist_for_vessels_on_each_node'.
  for i in range(count):
    ip = ip_prefix + str(i)
    create_node_and_vessels_with_one_port_each(ip, portlist_for_vessels_on_each_node)





def create_nodes_on_different_subnets(count, portlist_for_vessels_on_each_node):
  # Create 'count' nodes on different subnets and on each node create a vessel
  # with a single port for each port in 'portlist_for_vessels_on_each_node'.
  ip_prefix = "127.1."
  ip_suffix = ".0"
  for i in range(count):
    ip = ip_prefix + str(i) + ip_suffix
    create_node_and_vessels_with_one_port_each(ip, portlist_for_vessels_on_each_node)





def create_nat_nodes(count, portlist_for_vessels_on_each_node):
  # Create 'count' nat nodes and on each node create a vessel
  # with a single port for each port in 'portlist_for_vessels_on_each_node'.
  ip_prefix = maindb.NAT_STRING_PREFIX
  for i in range(count):
    ip = ip_prefix + str(i)
    create_node_and_vessels_with_one_port_each(ip, portlist_for_vessels_on_each_node)





class SeattleGeniTestCase(unittest.TestCase):


  def setUp(self):
    # Setup a fresh database for each test.
    testlib.setup_test_db()



  def tearDown(self):
    # Cleanup the test database.
    testlib.teardown_test_db()



  def test_acquire_vessels_invalid_request(self):
    
    # Create a user who will be doing the acquiring.
    user = maindb.create_user("testuser", "password", "example@example.com", "affiliation", "1 2", "2 2 2", "3 4")
    
    func = interface.acquire_vessels
    
    # Negative vesselcount.
    args = (user, -1, 'wan')
    self.assertRaises(AssertionError, func, *args)   

    # Zero vesselcount.
    args = (user, 0, 'wan')
    self.assertRaises(AssertionError, func, *args)   

    # Unrecognized vessel type.
    args = (user, 1, 'x')
    self.assertRaises(ProgrammerError, func, *args)   



  def test_acquire_vessels_insufficient_vessel_credits(self):
    
    # Create a user who will be doing the acquiring.
    user = maindb.create_user("testuser", "password", "example@example.com", "affiliation", "1 2", "2 2 2", "3 4")
    
    # TODO: need to test maindb.require_user_can_acquire_resources separately
    
    # The user doesn't have any donations, they shouldn't be able to acquire
    # more vessels than their free credits.
    credit_limit = maindb.get_user_free_vessel_credits(user)
    
    vesseltypelist = ['wan', 'lan', 'nat', 'rand']

    for vesseltype in vesseltypelist:
      func = interface.acquire_vessels
      args = (user, credit_limit + 1, vesseltype)
      self.assertRaises(InsufficientUserResourcesError, func, *args)      
  


  def test_acquire_wan_vessels_multiple_calls_wan(self):

    # Have every vessel acquisition to the backend request succeed.
    calls_results = [True] * 10
    mocklib.mock_backend_acquire_vessel(calls_results)
    
    # Create a user who will be doing the acquiring.
    user = maindb.create_user("testuser", "password", "example@example.com", "affiliation", "1 2", "2 2 2", "3 4")
    userport = user.usable_vessel_port
    
    vesselcount = maindb.get_user_free_vessel_credits(user)
    
    create_nodes_on_different_subnets(vesselcount, [userport])
    
    # First request a single vessel.
    first_vessel_list = interface.acquire_vessels(user, 1, 'wan')
    
    # Now acquire all of the rest that the user can acquire.
    second_vessel_list = interface.acquire_vessels(user, vesselcount - 1, 'wan')

    self.assertEqual(1, len(first_vessel_list))
    self.assertEqual(vesselcount - 1, len(second_vessel_list))



  def test_acquire_wan_vessels_multiple_calls_lan(self):

    # Have every vessel acquisition to the backend request succeed.
    calls_results = [True] * 10
    mocklib.mock_backend_acquire_vessel(calls_results)
    
    # Create a user who will be doing the acquiring.
    user = maindb.create_user("testuser", "password", "example@example.com", "affiliation", "1 2", "2 2 2", "3 4")
    userport = user.usable_vessel_port
    
    vesselcount = maindb.get_user_free_vessel_credits(user)
    
    create_nodes_on_same_subnet(vesselcount, [userport])
    
    # First request a single vessel.
    first_vessel_list = interface.acquire_vessels(user, 1, 'lan')
    
    # Now acquire all of the rest that the user can acquire.
    second_vessel_list = interface.acquire_vessels(user, vesselcount - 1, 'lan')

    self.assertEqual(1, len(first_vessel_list))
    self.assertEqual(vesselcount - 1, len(second_vessel_list))



  def test_acquire_wan_vessels_multiple_calls_nat(self):

    # Have every vessel acquisition to the backend request succeed.
    calls_results = [True] * 10
    mocklib.mock_backend_acquire_vessel(calls_results)
    
    # Create a user who will be doing the acquiring.
    user = maindb.create_user("testuser", "password", "example@example.com", "affiliation", "1 2", "2 2 2", "3 4")
    userport = user.usable_vessel_port
    
    vesselcount = maindb.get_user_free_vessel_credits(user)
    
    create_nat_nodes(vesselcount, [userport])
    
    # First request a single vessel.
    first_vessel_list = interface.acquire_vessels(user, 1, 'nat')
    
    # Now acquire all of the rest that the user can acquire.
    second_vessel_list = interface.acquire_vessels(user, vesselcount - 1, 'nat')

    self.assertEqual(1, len(first_vessel_list))
    self.assertEqual(vesselcount - 1, len(second_vessel_list))



  def test_acquire_wan_vessels_multiple_calls_rand(self):

    # Have every vessel acquisition to the backend request succeed.
    calls_results = [True] * 10
    mocklib.mock_backend_acquire_vessel(calls_results)
    
    # Create a user who will be doing the acquiring.
    user = maindb.create_user("testuser", "password", "example@example.com", "affiliation", "1 2", "2 2 2", "3 4")
    userport = user.usable_vessel_port
    
    vesselcount = maindb.get_user_free_vessel_credits(user)
    
    # Create vesselcount nodes split between the different types.
    create_nodes_on_different_subnets(4, [userport])
    create_nodes_on_same_subnet(4, [userport])
    create_nat_nodes(vesselcount - 8, [userport])
    
    # First request a single vessel.
    first_vessel_list = interface.acquire_vessels(user, 1, 'rand')
    
    # Now acquire all of the rest that the user can acquire.
    second_vessel_list = interface.acquire_vessels(user, vesselcount - 1, 'rand')

    self.assertEqual(1, len(first_vessel_list))
    self.assertEqual(vesselcount - 1, len(second_vessel_list))



  def test_acquire_wan_vessels_some_vessels_fail(self):

    # Have every other vessel acquisition fail. We're going to acquire 50,
    # so we'll need 100 responses alternating between failure and success
    # (we're starting with failure, so 100, not 99).
    calls_results = [False, True] * 50
    mocklib.mock_backend_acquire_vessel(calls_results)
    
    # Create a user who will be doing the acquiring.
    user = maindb.create_user("testuser", "password", "example@example.com", "affiliation", "1 2", "2 2 2", "3 4")
    userport = user.usable_vessel_port
    
    # We need to give the user some donations so they have enough credits.
    # We're assuming it's 10 credits per donation.
    self.assertEqual(10, maindb.VESSEL_CREDITS_FOR_DONATIONS_MULTIPLIER)
    
    # Also make sure the user started with 10 credits.
    self.assertEqual(10, maindb.get_user_free_vessel_credits(user))
    
    # We need 100 nodes the user can acquire vessels on as we're having half of
    # the node acquisitions fail.
    create_nodes_on_different_subnets(100, [userport])
    
    # Now credit the user for donations on 4 of these.
    for node in maindb.get_active_nodes()[:4]:
      maindb.create_donation(node, user, '')
    
    # Ok, the user now has 50 vessels the can acquire and there are 100 nodes
    # with vessels available for them. Let's try to acquire all 50 at once and
    # make sure this works even though we'll have to get through 100 requests
    # to the backend to make it happen.
    vessel_list = interface.acquire_vessels(user, 50, 'wan')
    
    self.assertEqual(50, len(vessel_list))




  def test_acquire_lan_vessels_some_subnets_have_too_many_vessels_fail(self):
    """
    We're going to be trying to acquire 4 vessels in a single subnet. We'll
    make it so that there are 3 subnets to choose from. The first two will
    potentially have enough vessels for the user to satisfy their acquisition
    request, but too many vessels in each will fail. The third subnet tried
    will have enough succeed.
    """
    
    # We're going to have three subnets with 5 potential vessels each. We
    # want the first two subnets to fail. Choosing the values creatively
    # here is helped by knowing the logic of the function
    # vessels._acquire_vessels_from_list(). Basically, it won't try to
    # acquire more than the minumum needed at a time, so the first time
    # it loops it will try to acquire all 4, then the next time it loops
    # it will try to acquire however many of the 4 failed the first time.
    # It won't bother trying again if there are too few left in the list.
    results_1 = [False, True, True, True, False]
    results_2 = [False, False, True, True]
    results_3 = [False, True, True, True, True]
    calls_results = results_1 + results_2 + results_3
    mocklib.mock_backend_acquire_vessel(calls_results)
    
    # Create a user who will be doing the acquiring.
    user = maindb.create_user("testuser", "password", "example@example.com", "affiliation", "1 2", "2 2 2", "3 4")
    userport = user.usable_vessel_port
    
    # Make sure the user starts with 10 credits.
    self.assertEqual(10, maindb.get_user_free_vessel_credits(user))
    
    # Create three subnets with 5 nodes each. We need to keep them all the same
    # size, otherwise we need to change the test to patch maindb so that the
    # subnets will be tried in the order we expect.
    create_nodes_on_same_subnet(5, [userport], ip_prefix="127.0.0.")
    create_nodes_on_same_subnet(5, [userport], ip_prefix="127.0.1.")
    create_nodes_on_same_subnet(5, [userport], ip_prefix="127.0.2.")
    
    # Now try to acquire 8 lan nodes on a single subnet.
    vessel_list = interface.acquire_vessels(user, 4, 'lan')
    
    self.assertEqual(4, len(vessel_list))
    
    # Make sure backend.acquire_vessel() got called the correct number of
    # times (that is, the call_results list got pop(0)'d enough times).
    self.assertEqual(0, len(calls_results))
    



def run_test():
  unittest.main()



if __name__ == "__main__":
  run_test()
