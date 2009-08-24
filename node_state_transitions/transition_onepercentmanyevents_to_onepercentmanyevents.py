"""
<Program>
  transition_onepercentmanyevents_to_onepercentmanyevents.py

<Purpose>
  The purpose of this program is to update the database about the 
  node, so new things such as seattle version and other stuff are
  reflected in the database

<Started>
  August 13, 2009

<Author>
  Monzur Muhammad
  monzum@cs.washington.edu

<Usage>
  Ensure that seattlegeni and seattle are in the PYTHONPATH.
  Ensure that the database is setup properly and django settings
    are set correctly.

  python transition_onepercentmanyevents_to_onepercentmanyevents.py
"""


from django.db import transaction

import traceback

from seattlegeni.common.util.decorators import log_function_call

from seattlegeni.common.api import maindb

from seattlegeni.node_state_transitions import node_transition_lib





@log_function_call
def update_database(node_string, node_info, database_nodeobject, update_database_node):
  """
  <Purpose>
    The purpose of this function is to update the database

  <Arguments>
    node_string - the name of the node. ip:port or NAT:port

    node_info - a dictionary containing information about the node

    node_database - a node object from the database

    update_database_node - This is a function that updates the database. May be replaced 
      in the future.

  <Exceptions>
    DatabaseError - raised if unable to modify the database

  <Side Effects>
    None

  <Return>
    None
  """

  node_transition_lib.log("Beginning update_database on node: "+node_string)

  # Extract the ip/NAT and the port.
  # Note that the first portion of the node might be an ip or a NAT string.
  ip_or_nat_string, port_num = node_transition_lib.split_node_string(node_string)

  # Update the database with the most up to date info about the node.
  # Currently only updates the node version 
  try:
    node_transition_lib.log("Retrieved database node object for node: " + node_string)
    update_database_node(database_nodeobject, node_info, ip_or_nat_string, port_num)
    node_transition_lib.log("updated node database record with version: "+str(database_nodeobject.last_known_version))
  except:
    raise node_transition_lib.DatabaseError("Unable to update the database." + traceback.format_exc())

  try:
    node_transition_lib.log("Commiting transaction...")
    transaction.commit()
  except transaction.TransactionManagementError:
    pass

  return





@log_function_call
def update_database_node(database_nodeobject, node_info, ip_or_nat_string, port_num):
  """
  <Purpose>
    Update the database with the information provided

  <Arguments>
    database_nodeobject - a database object of the node

    node_info - information about the node including the vesseldict

    ip_or_nat_string - the ip or nat address of the node

    port_num - the port number that is being used for the port

    node_status - the status of the node that should be set

  <Exception>
    DatabaseError - raise if we could not update database

  <Side Effects>
    None

  <Return>
    database_object
  """

  version = node_info['version']
  
  # If the node objec was inactive, then we are going to make it active.
  if not database_nodeobject.is_active:
    node_transition_lib.log("The node "+ip_or_nat_string+":"+str(port_num)+" was inactive. Now activating")

  try:
    # Update all the database info about the node.
    database_nodeobject.last_known_version = version
    database_nodeobject.last_known_ip = ip_or_nat_string
    database_nodeobject.last_known_port = port_num
    database_nodeobject.is_active = True

    database_nodeobject.save()
  except:
    raise node_transition_lib.DatabaseError("Unable to modify database to update info on node: "+ip_or_nat_string)

  node_transition_lib.log("Updated the database for node: "+ip_or_nat_string+", with the latest info")

  return database_nodeobject
  

  


def main():
  """
  <Purpose>
    The main function that calls the process_nodes_and_change_state() function
    in the node_transition_lib passing in the process and error functions.

  <Arguments>
    None

  <Exceptions>
    None

  <Side Effects>
    None
  """

  state_function_arg_tuplelist = [
    (("onepercentmanyevents_state", node_transition_lib.onepercentmanyeventspublickey), 
      ("onepercentmanyevents_state", node_transition_lib.onepercentmanyeventspublickey), 
      update_database, node_transition_lib.noop, update_database_node)]

  sleeptime = 10
  process_name = "onepercentmanyevents_to_onepercentmanyevents"
  parallel_instances = 10

  #call process_nodes_and_change_state() to start the node state transition
  node_transition_lib.process_nodes_and_change_state(state_function_arg_tuplelist, process_name, sleeptime, parallel_instances)





if __name__ == '__main__':
  main()
