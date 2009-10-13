"""
Tests the interface.renew_vessels and interface.renew_all_vessels calls.
"""

# The seattlegeni testlib must be imported first.
from seattlegeni.tests import testlib

from seattlegeni.tests import mocklib

from seattlegeni.common.api import maindb

from seattlegeni.common.exceptions import *

from seattlegeni.website.control import interface

import datetime
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





def create_nodes_on_different_subnets(count, portlist_for_vessels_on_each_node):
  # Create 'count' nodes on different subnets and on each node create a vessel
  # with a single port for each port in 'portlist_for_vessels_on_each_node'.
  ip_prefix = "127.1."
  ip_suffix = ".0"
  for i in range(count):
    ip = ip_prefix + str(i) + ip_suffix
    create_node_and_vessels_with_one_port_each(ip, portlist_for_vessels_on_each_node)





class SeattleGeniTestCase(unittest.TestCase):


  def setUp(self):
    # Setup a fresh database for each test.
    testlib.setup_test_db()



  def tearDown(self):
    # Cleanup the test database.
    testlib.teardown_test_db()



  def test_renew_vessels_insufficient_vessel_credits(self):
    
    # Create a user who will be doing the acquiring.
    user = maindb.create_user("testuser", "password", "example@example.com", "affiliation", "1 2", "2 2 2", "3 4")
    userport = user.usable_vessel_port
    
    vesselcount = 4
    create_nodes_on_different_subnets(vesselcount, [userport])
    
    # Acquire all of the vessels the user can acquire.
    vessel_list = interface.acquire_vessels(user, vesselcount, 'rand')
    
    # Decrease the user's vessel credits to one less than the number of vessels
    # they have acquired.
    user.free_vessel_credits = 0
    user.save()
    
    func = interface.renew_vessels
    args = (user, vessel_list)
    self.assertRaises(InsufficientUserResourcesError, func, *args)      
  
    func = interface.renew_all_vessels
    args = (user,)
    self.assertRaises(InsufficientUserResourcesError, func, *args)   



  def test_renew_some_of_users_vessel(self):
    
    # Create a user who will be doing the acquiring.
    user = maindb.create_user("testuser", "password", "example@example.com", "affiliation", "1 2", "2 2 2", "3 4")
    userport = user.usable_vessel_port
    
    vesselcount = 4
    create_nodes_on_different_subnets(vesselcount, [userport])
    
    # Acquire all of the vessels the user can acquire.
    vessel_list = interface.acquire_vessels(user, vesselcount, 'rand')
    
    renew_vessels_list = vessel_list[:2]
    not_renewed_vessels_list = vessel_list[2:]
    
    interface.renew_vessels(user, renew_vessels_list)
  
    now = datetime.datetime.now()
    timedelta_oneday = datetime.timedelta(days=1)
  
    for vessel in renew_vessels_list:
      self.assertTrue(vessel.date_expires - now > timedelta_oneday)

    for vessel in not_renewed_vessels_list:
      self.assertTrue(vessel.date_expires - now < timedelta_oneday)



  def test_renew_vessels_dont_belong_to_user(self):
    
    # Create a user who will be doing the acquiring.
    user = maindb.create_user("testuser", "password", "example@example.com", "affiliation", "1 2", "2 2 2", "3 4")
    userport = user.usable_vessel_port
    
    vesselcount = 4
    create_nodes_on_different_subnets(vesselcount, [userport])
    
    # Acquire all of the vessels the user can acquire.
    vessel_list = interface.acquire_vessels(user, vesselcount, 'rand')
    
    release_vessels_list = vessel_list[:1]
    interface.release_vessels(user, release_vessels_list)
    
    # Try to renew all of the originally acquired vessels, including the ones
    # that were released.
    func = interface.renew_vessels
    args = (user, vessel_list)
    self.assertRaises(InvalidRequestError, func, *args)    
    
    # Try to renew only vessels that were released.
    func = interface.renew_vessels
    args = (user, release_vessels_list)
    self.assertRaises(InvalidRequestError, func, *args)      
  
    # Now renew all of the user's vessels and make sure the released vessels
    # are not renewed.
    interface.renew_all_vessels(user)
    
    # Get fresh vessel objects that reflect the renewal.
    remaining_vessels = interface.get_acquired_vessels(user)
  
    now = datetime.datetime.now()
    timedelta_oneday = datetime.timedelta(days=1)
  
    for vessel in remaining_vessels:
      self.assertTrue(vessel.date_expires - now > timedelta_oneday)

    for vessel in release_vessels_list:
      self.assertTrue(vessel.date_expires - now < timedelta_oneday)



def run_test():
  unittest.main()



if __name__ == "__main__":
  run_test()
