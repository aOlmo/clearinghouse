"""
<Program>
  transition_canonical_to_onepercentmanyevents.py

<Purpose>
  The purpose of this program is to transition nodes from the
  canonical state to the onepercentmanyevents state by bypassing
  through the movingtoonepercentmanyevents state.

<Started>
  August 13, 2009

<Author>
  Monzur Muhammad
  monzum@cs.washington.edu

<Usage>
  Ensure that seattlegeni and seattle are in the PYTHONPATH. 
  Ensure that the database is setup properly and django settings
    are set correctly.

  python transition_canonical_to_onepercentmanyevents.py 
"""


import node_transition_lib
import random
import traceback
from seattlegeni.common.api import backend
from seattlegeni.common.api import lockserver
from seattlegeni.common.api import maindb
from seattlegeni.common.api import nodemanager
from seattlegeni.common.util.decorators import log_function_call
from seattlegeni.common.exceptions import *

@log_function_call
def onepercentmanyevents_divide (node_string, nodeID, onepercent_resourcetemplate):
  """
  <Purpose>
    The purpose of this function is to take a node thats in canonical state
    with one vessel, and split it into the 1% vessels so the vessels can
    be acquired by users.

  <Arguments>
    node_string - the name of the node. ip:port or NAT:port

    nodeID - The unique ID or the per node key of the node
 
    onepercent_resourcetemplate - the file that has information about resources

  <Exceptions>
    NodeError - Error raised if node is not in the right state 

    NodemanagerCommunicationError - raised if we cannot retrieve the usable ports for a node

    NodeProcessError - raised if unable to split vessels properly

    DatabaseError - raised if unable to modify the database    

  <Side Effects>
    Database gets modified.        

  <Return>
    None
  """

  node_transition_lib.log("Beginning onepercentmanyevents_divide on node: "+node_string)

  #extract the ip/NAT and the port
  #note that the first portion of the node might be an ip or a NAT string
  ip_or_nat_string, port_string = node_string.split(":")
  port_num = int(port_string)



  #create a lock handle to be used
  lockserver_handle = lockserver.create_lockserver_handle()
  node_transition_lib.log("Created lockserver_handle for use on node: "+str(nodeID))

  #acquire a lock for the node
  lockserver.lock_node(lockserver_handle, nodeID)
  node_transition_lib.log("Acquired node lock for nodeID: "+nodeID)
 
  
  
  try:
    # Retrieve the node database object
    database_nodeobject = maindb.get_node(nodeID)
    donated_vesselname = database_nodeobject.extra_vessel_name


 
    #Retrieve the usable ports list for the node
    usable_ports_list = nodemanager.get_vessel_resources(ip_or_nat_string, port_num, donated_vesselname)['usableports']
  
    node_transition_lib.log("List of usable ports in node: "+node_string+". "+str(usable_ports_list))

    #shuffle the list of ports so when the vessel is split the vessels get a random subset
    random.shuffle(usable_ports_list)



    #the vessel that we start with
    current_vessel = donated_vesselname
    node_transition_lib.log("Name of starting vessel: "+current_vessel)



    #keep splittiing the vessel until we run out of resources  
    #Note that when split_vessel is called the left vessel has the leftover (extra vessel)
    #and the right vessel has the vessel with the exact resources.
    while len(usable_ports_list) >= 10:
      #TODO: ask jsamuel how to do this better
      desired_resourcedata = onepercent_resourcetemplate % (str(usable_ports_list[0]), str(usable_ports_list[1]), 
                             str(usable_ports_list[2]), str(usable_ports_list[3]), str(usable_ports_list[4]),
                             str(usable_ports_list[5]), str(usable_ports_list[6]), str(usable_ports_list[7]),
                             str(usable_ports_list[8]), str(usable_ports_list[9]), str(usable_ports_list[0]),
                             str(usable_ports_list[1]), str(usable_ports_list[2]), str(usable_ports_list[3]),
                             str(usable_ports_list[4]), str(usable_ports_list[5]), str(usable_ports_list[6]),
                             str(usable_ports_list[7]), str(usable_ports_list[8]), str(usable_ports_list[9]))



      #use the first 10 ports so remove them from the list of usable_ports_list
      used_ports_list = usable_ports_list[:10]
      usable_ports_list = usable_ports_list[10:]

      node_transition_lib.log("Ports we are going to use for the new vessel: "+str(used_ports_list))
      node_transition_lib.log("Starting to split vessel: "+current_vessel)



      #split the current vessel. The exact vessel is the right vessel and the extra vessel is the left vessel
      #create a record for the vessel and add its port to the database

      leftover_vessel, new_vessel = backend.split_vessel(database_nodeobject, current_vessel, desired_resourcedata)                    

      node_transition_lib.log("Successfully split vessel: "+current_vessel+" into vessels: "+leftover_vessel+" and "+new_vessel)
   
      current_vessel = leftover_vessel



      #set the user_list for the new vesel to be empty. Remember that user_list is what determines
      #the transition state, and only the extra vessel should have this set.
      backend.set_vessel_user_keylist(database_nodeobject, new_vessel, [])
      node_transition_lib.log("Changed the userkeys for the vessel "+new_vessel+" to []")



      # Add the newly created vessel to the database and then add the ports associated with
      # the vessel to the database also    
      try:
        node_transition_lib.log("Creating a vessel record in the database for vessel "+new_vessel+" for node "+node_string)
        vessel_object = maindb.create_vessel(database_nodeobject, new_vessel)
        node_transition_lib.log("Setting the vessel ports in the database for vessel "+new_vessel+" with port list: "+str(used_ports_list))
        maindb.set_vessel_ports(vessel_object, used_ports_list)
      except:
        raise node_transition_lib.DatabaseError("Failed to create vessel entry or change vessel entry for vessel: "+
                                               new_vessel+". "+traceback.format_exc())


    node_transition_lib.log("Finished splitting vessels up for the node: "+node_string)

  except NodemanagerCommunicationError, e:
    raise NodemanagerCommunicationError("Unable to retrieve usable ports for node: "+node_string+". "+traceback.format_exc())
  except node_transition_lib.DatabaseError, e:
    raise
  except Exception, e:
    raise node_transition_lib.NodeError("Failed to split vessels for node: "+node_string+". "+traceback.format_exc())
  finally:
    #release the node lock and destroy lock handle
    lockserver.unlock_node(lockserver_handle, nodeID)
    node_transition_lib.log("released lock for node: "+nodeID)
    lockserver.destroy_lockserver_handle(lockserver_handle)
    node_transition_lib.log("Destroyed lockserver_handle for node: "+nodeID)





@log_function_call
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

  #open and read the resource file that is necessary for onepercentmanyevents
  onepercentmanyevents_resource_fd = file("onepercentmanyevents.resources")
  onepercentmanyevents_resourcetemplate = onepercentmanyevents_resource_fd.read()
  onepercentmanyevents_resource_fd.close()
  
  """
  build up the tuple list to call process_nodes_and_change_state()
  The transition from canonical to onepercentmanyevents happens in 3 steps.
  Step1: Move the canonical nodes to the movingtoonepercent state (the reason
    this is done is because incase some transition fails, we know that they are 
    going to be in the movingtoonepercent state.
  Step2: Next run the process function and change the state from movingtoonepercent
    state to the onepercentmanyevents state.
  Step3: Find all the nodes that failed to transition from movingtoonepercent
    state to onepercentmanyevents and transition them back to the canonical state.
  """

  state_function_arg_tuplelist = [
    (("canonical_state", node_transition_lib.canonicalpublickey), ("movingto_onepercent_state", 
      node_transition_lib.movingtoonepercentmanyeventspublickey), 
      node_transition_lib.noop, node_transition_lib.noop),

    (("movingto_onepercent_state", node_transition_lib.movingtoonepercentmanyeventspublickey),
      ("onepercentmanyevents_state", node_transition_lib.onepercentmanyeventspublickey), 
      onepercentmanyevents_divide, node_transition_lib.noop,onepercentmanyevents_resourcetemplate),

    (("movingto_onepercent_state", node_transition_lib.movingtoonepercentmanyeventspublickey), 
      ("canonical_state", node_transition_lib.canonicalpublickey), node_transition_lib.combine_vessels, 
      node_transition_lib.noop, node_transition_lib.movingtoonepercentmanyeventspublickey)]
 
  sleeptime = 10
  process_name = "canonical_to_onepercentmanyevents"
  parallel_instances = 10

  #call process_nodes_and_change_state() to start the node state transition
  node_transition_lib.process_nodes_and_change_state(state_function_arg_tuplelist, process_name, sleeptime, parallel_instances) 





if __name__ == '__main__':
  main()
