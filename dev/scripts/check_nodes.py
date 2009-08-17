#!/usr/bin/env python
"""
<Program>
  check_nodes.py

<Started>
  16 August 2009

<Author>
  Justin Samuel

<Purpose>
  This script currently does not modify nodes or the database, but just checks to
  see if the informatin provided by querying the node matches what we expect for
  the node (and its vessels) in the database.

  However, this script seems like it could go a bit further and actually update
  some parts of the database, such as marking vessels as dirty when they look
  like they weren't cleaned up and aren't assigned to anyone. Also, potentially
  marking a node as being in an invalid state (which would require adding a new
  field to the node table) when things appear very broken and not worth leaving
  as active until we perform potentially manual cleanup.
  
  Note: if this script gets changed so that it actually modifies the database
  or nodes, it should probably be renamed to make it clearer by the script name.

  TODO: check vessel ports
  TODO: check donation records (make sure we have at least one per node)

  Possibilities for database updates based on what we find:
  TODO: if a we expect zero user keys on a vessel but is has some, mark it is dirty?
  TODO: if a node can't be communicated with, mark it as inactive?
"""

import os

from seattlegeni.common.api import maindb
from seattlegeni.common.api import nodemanager

from seattlegeni.common.util import log

from seattlegeni.common.exceptions import *

from seattle import repyhelper
from seattle import repyportability

repyhelper.translate_and_import("rsa.repy")





def readfilecontents(filename):
  f = open(filename)
  contents = f.read()
  f.close()
  return contents



def report_node_problem(node, message):
  global nodes_with_problems
  nodes_with_problems[node.node_identifier] = True
  log.info("Problem on node " + str(node) + ": " + message)





# Decrease the amount of logging output.
log.loglevel = log.LOG_LEVEL_INFO

onepercentmanyevents_key_path = os.path.dirname(__file__) + "/../../node_state_transitions/onepercentmanyevents.publickey"
onepercentmanyevents_keydict = rsa_string_to_publickey(readfilecontents(onepercentmanyevents_key_path))

# We'll keep track which nodes had problems.
nodes_with_problems = {}





def main():
  
  active_nodes = maindb.get_active_nodes()
  log.info("Starting check of " + str(len(active_nodes)) + " active nodes.")

  checked_node_count = 0
  
  for node in active_nodes:
    
    node_is_clean = True
   
    checked_node_count += 1 
    log.info("Checking node " + str(checked_node_count) + ": " + str(node))
    
    try:
      nodeinfo = nodemanager.get_node_info(node.last_known_ip, node.last_known_port)
    except NodemanagerCommunicationError:
      report_node_problem(node, "Can't communicate with node even though it's marked as active in the database.")
      continue
    
    # Check that the nodeid matches.
    if rsa_string_to_publickey(node.node_identifier) != nodeinfo["nodekey"]:
      report_node_problem(node, "Wrong node identifier, the node reports: " + str(nodeinfo["nodekey"]))
    
    # Check that the database thinks it knows the extra vessel name.
    if node.extra_vessel_name == "":
      report_node_problem(node, "No extra_vessel_name in the database.")
    # Check that a vessel by the name of extra_vessel_name exists on the node.
    elif node.extra_vessel_name not in nodeinfo["vessels"]:
      report_node_problem(node, "The extra_vessel_name in the database is a vessel name that doesn't exist on the node.")
      
    vessels_on_node = maindb.get_vessels_on_node(node)
      
    known_vessel_names = []
    for vessel in vessels_on_node:
      known_vessel_names.append(vessel.name)

    # Check for vessels on the node with our node ownerkey where those vessels aren't in our database.
    for actualvesselname in nodeinfo["vessels"]:
      if onepercentmanyevents_keydict in nodeinfo["vessels"][actualvesselname]["userkeys"]:
        # It's the extra vessel, so we don't expect it to be in our vessels table.
        continue
      vessel_ownerkey = nodeinfo["vessels"][actualvesselname]["ownerkey"]
      if rsa_publickey_to_string(vessel_ownerkey) == node.owner_pubkey:
        if actualvesselname not in known_vessel_names:
          report_node_problem(node, "The vessel '" + actualvesselname + "' exists on the node " + 
                              "with the ownerkey for the node, but it's not in our vessels table.")
      
    # The remaining checks are only relevant if there are vessels we know about on the node.
    if len(vessels_on_node) == 0:
      continue
      
    # Do some checking on each vessel we know about.
    for vessel in vessels_on_node:
      
      # Check that each vessel we have for the node in the database actually exists on the node.
      if vessel.name not in nodeinfo["vessels"]:
        report_node_problem(node, "The vessel '" + vessel.name + "' in the database doesn't exist on the node.")
        continue
  
      vesselinfo = nodeinfo["vessels"][vessel.name]
  
      # Check that the owner key for the vessel is what we have for the node's owner key.
      if node.owner_pubkey != rsa_publickey_to_string(vesselinfo["ownerkey"]):
        report_node_problem(node, "The vessel '" + vessel.name + "' doesn't have the ownerkey we use for the node.")
      
      if not vesselinfo["advertise"]:
        report_node_problem(node, "The vessel '" + vessel.name + "' isn't advertising.")
      
      # Check that the user keys that have access are the ones that should have access.
      users_with_access = maindb.get_users_with_access_to_vessel(vessel)
      
      if len(users_with_access) != len(vesselinfo["userkeys"]):
        report_node_problem(node, "The vessel '" + vessel.name + "' reports " +
                            str(len(vesselinfo["userkeys"])) + " user keys, but we expected " + str(len(users_with_access)))
        
      for user in users_with_access:
        if rsa_string_to_publickey(user.user_pubkey) not in vesselinfo["userkeys"]:
          report_node_problem(node, "The vessel '" + vessel.name + "' doesn't have the userkey for user " + user.username + ".")
          
    # If there are any vessels (besides the empty vessel), the node should be in
    # the onepercentmanyevents state. So, check that the user key in the extra
    # vessel is the onepercentmanyevents key.
  
    extravesselinfo = nodeinfo["vessels"][node.extra_vessel_name]
  
    if len(extravesselinfo["userkeys"]) != 1:
      report_node_problem(node, "The extra vessel '" + vessel.name + 
                          "' doesn't have one user key, it has " + str(len(extravesselinfo["userkeys"])))
  
    if onepercentmanyevents_keydict not in extravesselinfo["userkeys"]:
      report_node_problem(node, "The extra vessel '" + vessel.name + "' doesn't have the onepercentmanyevents " + 
                          "key even though we believe the node is in the onepercentmanyevents state.")

  # Print summary info.
  log.info("Nodes checked: " + str(checked_node_count))
  nodes_with_problems_count = len(nodes_with_problems.keys())
  log.info("Ok nodes: " + str(checked_node_count - nodes_with_problems_count))
  log.info("Nodes with problems: " + str(nodes_with_problems_count))

      




if __name__ == "__main__":
  try:
    main()
  except KeyboardInterrupt:
    pass
