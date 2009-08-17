"""
<Program>
  node_transition_lib.py

<Started>
  July 29, 2009

<Author>
  Monzur Muhammad
  monzum@cs.washington.edu

<Purpose>
  This is a library file for the node transition scripts. It is a general 
  module so all the transition scripts will be able to import this file 
  and easily create a new transition script.

<Usage>
  Meant to be imported.

<Information>
  The transitional script is meant to seek out all the nodes that 
  are currently advertising and check their states. If necessary, 
  the state of the node is changed. Currently a node can be in three 
  different state: donated state, canonical state, and one percent state. 
  The donated state is when new nodes are discovered. This is usually 
  when a new user installs seattle and donates resources. The transitional
  scripts finds all the nodes that have been donated and processes them. 
  The information about the donated nodes are added to the database and 
  the node state is changed to the canonical state. The canonical state 
  is an important state, as this is the state where the nodes are ready to 
  be used, and be split up. All nodes should be able to come back to the 
  canonical state if anything goes wrong. At this point the canonical state 
  is changed to the onepercent state. This is where the 10% resource is
  taken and split into 10 sections (or into 1% resources). This 1% resource 
  is the vessel. Thus a node manager is responsible for 10 vessels (by 
  default, if only 10% resource is donated). In the future we might have 
  other states such as a twopercent state, in case we want to split the 
  resource differently.
"""

import runonce
import logging
import sys
import time
import traceback
import repyhelper
from seattlegeni.common.api import nodemanager
import seattlegeni.common.util.log
from seattlegeni.common.api import maindb
from seattlegeni.common.api import lockserver
from seattlegeni.common.api import backend
from seattlegeni.common.util.decorators import log_function_call
from seattlegeni.common.exceptions import *

#import all the repy files
repyhelper.translate_and_import('advertise.repy')
repyhelper.translate_and_import('nmclient.repy')
repyhelper.translate_and_import('rsa.repy')
repyhelper.translate_and_import('listops.repy')
repyhelper.translate_and_import('parallelize.repy')
repyhelper.translate_and_import('random.repy')


#The url to be used for lockserver
LOCKSERVER_URL = "http://127.0.0.1:8010"



canonicalpublickey = rsa_file_to_publickey("canonical.publickey")
# The key used for new donations...
acceptdonationpublickey = rsa_file_to_publickey("acceptdonation.publickey")

# Used for our first attempt at doing something sensible...
movingtoonepercentmanyeventspublickey = rsa_file_to_publickey("movingtoonepercent_manyevents.publickey")
onepercentmanyeventspublickey = rsa_file_to_publickey("onepercentmanyevents.publickey")

known_transition_states = [canonicalpublickey, acceptdonationpublickey,
                              movingtoonepercentmanyeventspublickey, 
                              onepercentmanyeventspublickey]





@log_function_call
def process_nodes_and_change_state(change_nodestate_function_tuplelist, transition_script_name, sleeptime, parallel_instances=1):
  """
  <Purpose>
    locate all the nodes in a certain state and apply the function thats in 
    the change_state_function_tuplelist and change the node state. Uses 
    public key to identify the nodes in different states.

  <Arguments>
    change_state_function_tuplelist - a list of tuples that contains all
      the info to change the state of a node.
      Tuple arguments:
        ((startstate_name, startstate_publickey), (endstate_name, endstate_publickey), processfunction, errorfunction, processfunc_args)

    transition_script_name - a unique name used to get a process lock.

    sleeptime - the amount of time to sleep between node processing.

    parallelinstances - the number of threads to run in parallel.

  <Exceptions>
    None
  <Side Effects>
    None

  <Return>
    None
  """

  init_log(transition_script_name)
  log("Starting state transition script: "+transition_script_name+".....")

  #initialize the nodemanager. does a time_update()
  nodemanager.init_nodemanager()

  #get a lock so multiple versions of the same script aren't running
  if runonce.getprocesslock("process_lock."+transition_script_name) != True:
    log("The lock for "+transition_script_name+" is being held.\nExiting...\n\n")
    return

  #initialize maindb for future use
  maindb.init_maindb()  


  #continuously run the script and keep checking for nodes whose state needs to be changed
  while True:
    node_transition_function(change_nodestate_function_tuplelist, transition_script_name, sleeptime, parallel_instances)





@log_function_call
def node_transition_function(change_nodestate_function_tuplelist, transition_script_name, sleeptime, parallel_instances=1):
  """
  <Purpose>
    This is the actual script that runs and starts everything up. It gets the list 
    of nodes that needs to be changed. Then starts up the function that tranistions
    the nodes in parallel.

  <Arguments> 
    change_state_function_tuplelist - a list of tuples that contains all
      the info to change the state of a node.
      Tuple arguments:
        ((startstate_name, startstate_publickey), (endstate_name, endstate_publickey), processfunction, errorfunction, processfunc_args)

    transition_script_name - a unique name used to get a process lock.

    sleeptime - the amount of time to sleep between node processing.

    parallelinstances - the number of threads to run in parallel.

  <Exceptions>
    None
  <Side Effects>
    None

  <Return>
    None
  """
  
  #going through the list of node state functions
  for change_nodestate_function_tuple in change_nodestate_function_tuplelist:

    #get some of the information out of the nodestate_function tuple
    startstate_name, startstate_publickey = change_nodestate_function_tuple[0]
    endstate_name, endstate_publickey = change_nodestate_function_tuple[1]

    #lookup nodes with the startstate publickey, on failure log info and continue
    log("Looking up nodes to transition from "+startstate_name+" state to "+endstate_name+" state")
    successful_lookup, nodeprocesslist = find_advertised_nodes(startstate_name, startstate_publickey)

    #if lookup was unsuccessful, then continue on. info is logged in find_advertised_nodes()
    if not successful_lookup:
      log("find_advertised_nodes() failed to look up nodes. Going on to the next nodestate_function_tuple")
      continue

    else:
      log("List of ip/NAT found in advertise_lookup(): " + str(nodeprocesslist))
      log("Length of nodeprocesslist: " + str(len(nodeprocesslist))) 
      log("Starting run_parallel_process to spawn threads to process nodes...")
    successful_processrun = run_parallel_processes(nodeprocesslist, transition_script_name, parallel_instances, *change_nodestate_function_tuple)

    if not successful_processrun:
      log("The parallel run for the transition from "+startstate_name+" state to "+endstate_name+" state failed")

    #once the processnode_function is run on the nodes, sleep for a time being before continuing
    log("Finished running processnode function on nodes in "+startstate_name+" state.\n Sleeping for "+str(sleeptime)+" seconds")
    time.sleep(sleeptime)
    print "------------------------------------------------------------------------\n"
    log("Waking up from sleep.....")





@log_function_call
def run_parallel_processes(nodeprocesslist, lockname, parallel_instances, *processargs):
  """
  <Purpose>
    Create parallel handle and run the node process functions in parallel.

  <Arguments>
    nodeprocesslist - the list of all the nodes that needs to be processed

    lockname - the name of the lock that was acquired earlier. To ensure
      that the lock is still held    

    *processargs - this includes startstate_info, endstate_info, 
      nodeprocess_func, nodeerror_func and nodeprocess_args 

  <Exceptions>
    No exceptions are raised but on excepts, everything is logged.

  <Side Effects>
    None

  <Return>
    success - boolean. weather or not the process runs were surccessful.
  """

  try:
    parallel_handle = parallelize_initfunction(nodeprocesslist, processnode_function, parallel_instances, *processargs)

  except Exception, e: 
    log("Error: failed to set up parallelize_initfunction" + str(e))
    return False




  try:
    #keep looping until all the threads in the parallel handle are finished running
    while not parallelize_isfunctionfinished(parallel_handle):
      #check to see if the lock is still held.
      if not runonce.stillhaveprocesslock("process_lock."+lockname):
        log("The lock for "+lockname+" has been lost. Exiting transitional script")
        return False
    
      #sleep for a sec to give the parallel_handle to finish
      time.sleep(1)

    #get the results to the parallel_handle for the node processing
    nodeprocessresults = parallelize_getresults(parallel_handle)

    #write to the log for all the nodes that had an exception
    for nodename, exceptionstring in nodeprocessresults['exception']:
      log("Failure on node "+nodename+"\nException String: "+exceptionstring+"\n")

    #write to the log for all the nodes that were aborted
    for nodename in nodeprocessresults['aborted']:
      log("The processnode_function was aborted for the node "+nodename)

  finally:
    #clean up the parallel_handle and make sure that the handle is closed
    log("Cleaning up and closing parallel_handle")
    parallelize_closefunction(parallel_handle)

  #everything worked out fine in the parallel_handle
  return True




    
@log_function_call
def processnode_function(node_string, startstate_info, endstate_info, nodeprocess_func, nodeerror_func, *nodeprocess_args):
  """
  <Purpose>
    First check the current state of the node, to ensure that it is in the
    correct state. Then run the nodeprocess_func on the node to process
    the node. Then set the new state of the node once the node has been
    processed properly.

  <Arguments>
    node_string - this is the node itself that is gotten from advertise_lookup,
      most likely an ip:port address or NAT:ip.

    startstate_info - a tuple about the startstate: (startstate_name,
      startstate_publickey)

    endstate_info - a tuple about the endstate that the node should be
      (endstate_name, endstate_publickey)

    nodeprocess_func - the function that is used to process the node

    nodeerror_func - the function that is run, if there is an error

    nodeprocess_args - the arguments for nodeprocess_func

  <Exceptions>
    NodeError - raised if the node is in a weird state, or if the 
      node does not exist

  <Side Effects>
    Database may get modified

  <Return>
    None
  """
 
  #the pubkey for the state
  startstate_pubkey = startstate_info[1]
  endstate_pubkey = endstate_info[1]

  #make sure that the node is just not an empty string, could happend due to bad advertise_lookup
  if not node_string:
    raise NodeError, "An empty node was passed down to processnode() with startstate: "+startstate_info[0]

  #note that the first portion of the node might be an ip or a NAT string
  ip_or_nat_string, port_string = node_string.split(":")
  port_num = int(port_string)

  log("Starting to process node: "+node_string)



 
  #try to retrieve the vessel dictionary for a node, on error raise NodeError exception
  log("Retrieving node vesseldict for node: "+node_string)
  try:
    node_info = nodemanager.get_node_info(ip_or_nat_string, port_num)
       
  except NodemanagerCommunicationError, e:
    raise NodeError("Failed to retrieve node_vesseldict for node: " + node_string + str(e))

  log("Node info for node " + node_string + ": "+str(node_info))
  nodeID =  rsa_publickey_to_string_helper(node_info['nodekey'])



  
  #if the nodes are in acceptdonationstate, update/check the database
  #to ensure that it matches the node information
  if startstate_pubkey == acceptdonationpublickey:
    log("Node in acceptdonationpublickey. Calling add_newnode_to_db() to check that node is correctly in database")
    add_newnode_to_db(ip_or_nat_string, port_num, node_info)         
    log("Returned from add_newnode_to_db() and database should be in right state...")



  log("Accessing database to retrieve node with nodeID: "+nodeID)

  #retrieve the node data from the database
  try:
    database_nodeobject = maindb.get_node(nodeID)
  except DatabaseError, e:
    raise DatabaseError("Unable to retrieve node from database with nodeID: " + nodeID + str(e))
  else:
    log("Retrieved node object successfully with nodeID: "+nodeID+" with the node: "+str(database_nodeobject))
    
  #retrieve the node state and and the list of vessels
  current_node_state_pubkey, vessel_name_list = get_node_state(node_info, database_nodeobject)
  
  #make sure that the node is in the right state
  if current_node_state_pubkey != startstate_pubkey:
    log("The node is not in the right transition state. NodeID is: "+nodeID)
    raise NodeError("Node is no longer in the right state!")



  
  #run the processnode function that was passed originally from the transition scripts
  try:
    nodeprocess_func(node_string, node_info, database_nodeobject, *nodeprocess_args)
  except Exception, e:
    log("Failed to process node: "+node_string)
    raise NodeProcessError("Could not process node: "+node_string+" "+str(e))
  else:
    #set the node state now that the node has been processed
    try:
      log("Trying to set new state for node: "+node_string)
      set_node_state(startstate_pubkey, endstate_pubkey, database_nodeobject, node_info, vessel_name_list)
      log("Finished setting new state "+endstate_info[0]+" on node "+node_string) 
    except NodeError, e:
      raise 
    except:
      raise UnexpectedError("Something unexpected happened while setting node state")




@log_function_call
def get_node_state(node_info, database_nodeobject):
  """
  <Purpose>
    Given a node, find out what state the node is in (canonical, onepercent,
    acceptdonation). And return the state of the node as well as all the
    vessels in the node whose 'userkey' is equal to the node_state_key
    that are in that particular state. The vesseldict
    is built in such a way, that only one of the vessels in the vesseldict 
    has the node_state_key. All the other vesses should have a empty node
    state key. The vessel that has the node_state_key is the 'extra' vessel.
    This 'extra' vessel is a SeattleGENI concept and not for Seattle. When
    the vessels in a nodemanager is split into 10 vessels (roughtly although 
    in more cases then not its around 8 vessels), there is usually a vessel
    thats created that does not have enough resources to be a full vessel, 
    so it is used to store information. This 'extra' vessel is never acquired
    by user, so its userkey never gets modified to the actual user keys, so
    it should hold the node_state_key.

  <Arguments>
    node_info - This contains the node information such as the nodeID (per
      node key), ip, port as well as the vesseldict. 

    database_nodeobject - this is the object that was retrieved from the database

  <Exceptions>
    None

  <Side Effects>
    None

  <Return>
    node_state - the state that the node is in.
    vesselstate_list - the list of nodes thats has userkey = node_state_key
  """

  #the state that the node is in. It gets set later in the while loop
  node_state = None
  vesselstate_list = []

  #this determines who the owner of the node is. Usually we (SeattleGENI)
  #is the owner of the node always, however the vessel's owner might be an
  #actual user who has acquired a vessel.
  node_publickey = database_nodeobject.owner_pubkey




  log("Retrieved node from database with publickey: " + node_publickey)
  #go through all the vessels in the dictionary to ensure that if we (SeattleGENI)
  #own the vessel then the vessels might have its 'userkey' as a transitional state
  #note that most likely the 'extra' vessel will have this transitional state
  for current_vessel in node_info['vessels']:

    log("Checking vessel: " + current_vessel + "....")
    if node_info['vessels'][current_vessel]['ownerkey'] == node_publickey:
      log("Vessel "+current_vessel+" belongs to SeattleGENI")
      #if the 'ownerkey' is us then check if it represents a transitional state
      log("Userkey list for vessel "+current_vessel+": "+str(node_info['vessels'][current_vessel]['userkeys']))
        
      statelisted = listops_intersect(node_info['vessels'][current_vessel]['userkeys'], known_transition_states)
      log("list of states for " + current_vessel + ": " + str(statelisted))    

      #go through the list of states to make sure that there aren't two different states 
      for state in statelisted:
        #makes sure that two different vessels dont have two different transition state
        if node_state and state != node_state:
          raise NodeError("More than one state '"+str(node_state)+"' and '"+str(state)+"' on the same node")
                       
        node_state = state
        #append the vessel to 
        vesselstate_list.append(current_vessel)
        log("vessel " + current_vessel + " added to the vesselstate_list")
  
    else:
      log("vessel" + current_vessel + " is acquired by users")
  #return the state and teh list of vessels that are in that state   
  return node_state, vesselstate_list

  

  
 
@log_function_call
def set_node_state(start_state, end_state, node_object, node_info, vessel_list):
  """
  <Purpose>
    given a list of vessels, change the userkeys of all the vessels.
    Only one of the vessel should carry the end_state, all other vessels
    will have empty state as transitional state. Keep in mind that the 
    userkey_list contains the transitional state of the node.
  
  <Arguments>
    start_state - the state the node is currently in.

    end_state - the state that the node should end in.

    node_object - an object that has been retrieved from the database

    node_info - an object with all information about the nodes including
      the vesseldict

  <Exceptions>
    NodeError - raised if unable to change node state

  <Side Effects>
    None

  <Return>
    None
  """

  #extract the nodeID
  nodeID =  rsa_publickey_to_string_helper(node_info['nodekey'])

  #go through all the vessels that have the start_state and remove it
  for current_vessel in vessel_list:
    node_info['vessels'][current_vessel]['userkeys'].remove(start_state)
    log("Removing old transition state from vessel: "+current_vessel)
    
  #add the new state key to the very first vessel
  vessel_name = vessel_list[0]
  node_info['vessels'][vessel_name]['userkeys'].append(end_state)
  log("Added the new state to the vessel: "+vessel_name)




  #initialize a lock
  lockserver_handle = lockserver.create_lockserver_handle(LOCKSERVER_URL)
  log("Created lockserver_handle for use on node: "+nodeID)  

  #acquire a lock for the node
  lockserver.lock_node(lockserver_handle, nodeID)
  log("Acquired node lock for nodeID: "+nodeID)
  
  #use a try/finally block to ensure that the lock is released at the end
  try:
    for current_vessel in vessel_list:
      #change the userkey for a vessel
      ownerkey_list = node_info['vessels'][current_vessel]['userkeys']
      backend.set_vessel_user_keylist(node_object, current_vessel, ownerkey_list)
      log("Changed userkeys for vessel: "+current_vessel)

  except Exception, e:
    raise NodeError("Unable to change state of node: "+nodeID+" "+str(e))

  finally:
    #release the node lock and destroy lock handle
    lockserver.unlock_node(lockserver_handle, nodeID)
    log("released lock for node: "+nodeID)
    lockserver.destroy_lockserver_handle(lockserver_handle) 
    log("Destroyed lockserver_handle for node: "+nodeID)
  
    



@log_function_call
def add_newnode_to_db(ip_or_nat_string, port, node_info):
  """
  <Purpose> 
    when new nodes come online, they may be not have the right data in 
    the database. This function ensures that the database has the 
    appropriate data. There are 3 different cases:
    <Case1>
      Database has no entry and Node has donor key as owner key
      Make sure to give the donor_user credit for their donation
    <Case2>
      Database has nodeID as owner key and Node has donor key
    <Case3>
      Database has nodeID and Node has nodeID as owner key

  <Arguments>
    ip_or_nat_string - the ip address of the node
    port - the port number of the node
    node_info - the information about the node, including vesseldict

  <Exceptions>
    NodeError - if the node does not have a valid state
    ProgrammerError - if node already exists in database and we're trying to
      recreate it.
    DatabaseError - if there is any problem while creating node in database

  <Side Effects>
    Database might get modified

  <Return>
    None
  """

  nodeID = rsa_publickey_to_string_helper(node_info['nodekey'])

  #extract the ownerkey and the vessel that has that info
  log("Looking for donor key for node: "+ip_or_nat_string+":"+str(port))
  log("Looking for the vessel that has the transition state in its 'userkeys'")




  for vesselname in node_info['vessels']:
    log("looking in vessel "+vesselname+".....")
    if listops_intersect(node_info['vessels'][vesselname]['userkeys'], known_transition_states):
      donation_owner_pubkey = node_info['vessels'][vesselname]['ownerkey']
      donation_vesselname = vesselname
      log("Found donation key in vessel "+donation_vesselname+" : "+str(donation_owner_pubkey))
      break
  else:
    raise NodeError("Node "+ip_or_nat_string+":"+str(port)+" does not seem to have a state after checking!")



  
  #retrieve the node data from the database
  try:
    database_nodeobject = maindb.get_node(nodeID)
    
  except DoesNotExistError, e:
    log("Database entry does not exist for node: "+ip_or_nat_string+":"+str(port))
    log("This is case 1")
    log("Generating new keys for node owner_key....")
    new_node_owner_pubkey = backend.generate_key(ip_or_nat_string+". "+nodeID)
    log("Generated publickey for node "+ip_or_nat_string+":"+str(port)+" : "+str(new_node_owner_pubkey))
    
    #This is to deal with Case1
    try:
      #attempt to add new node to db
      database_nodeobject = maindb.create_node(nodeID, ip_or_nat_string, port, node_info['version'], True, 
        rsa_publickey_to_string_helper(new_node_owner_pubkey), donation_vesselname) 
     
      log("Added node to the database with nodeID: "+nodeID)
  
    #this exception is passed down from maindb.create_node()
    except ProgrammerError:
      raise DatabaseError("Failed to create node object in database. Node already exists in database")
    except Exception, e:
      raise DatabaseError("Failed to create node and add to database. "+str(e))    


    database_userobject = ""
    #retrieve the user object for the user that donated the resource
    try:
      database_userobject = maindb.get_donor(rsa_publickey_to_string(donation_owner_pubkey))
      log("Retrieved the userobject of the donor from database: "+str(database_userobject))
    except:
      raise DatabaseError("Failed to retrieve the userobject of the donor from the database. "+str(e))
  

    #give the user credit for their donation of the node
    try:
      donation_description = "Crediting user "+database_userobject+" for donation of node "+str(database_nodeobject) 
      maindb.create_donation(database_nodeobject, database_userobject, donation_description)
      log("Registering the donation for the user with the donor_key: "+str(donation_owner_pubkey))
    except:
      raise DatabaseError("Failed to credit user for donation for user: "+str(database_userobject))

  else:
    log("Retrieved node object successfully with nodeID: "+nodeID+" with the node: "+str(database_nodeobject))
    



  #This is for Case2
  if donation_owner_pubkey != rsa_string_to_publickey(database_nodeobject.owner_pubkey):
    log("Database has nodeID but node has donation key")
    log("This is case 2")
    log("Attempting to change the owner for vessel: "+donation_vesselname)
    
    #initialize a lock
    lockserver_handle = lockserver.create_lockserver_handle(LOCKSERVER_URL)
    log("Created lockserver_handle for use on node: "+nodeID)

    #acquire a lock for the node
    lockserver.lock_node(lockserver_handle, nodeID)
    log("Acquired node lock for nodeID: "+nodeID)

    #use a try/finally block to ensure that the lock is released at the end
    try:
      backend.set_vessel_owner_key(node_object, donation_vesselname, node_object.owner_pubkey)
      
    except Exception, e:
      raise NodeError("Unable to change owner of node: "+nodeID+" "+e)

    finally:
      #release the node lock and destroy lock handle
      lockserver.unlock_node(lockserver_handle, nodeID)
      log("released lock for node: "+nodeID)
      lockserver.destroy_lockserver_handle(lockserver_handle)
      log("Destroyed lockserver_handle for node: "+nodeID)


  #For case 3 nothing needs to be done.   



@log_function_call 
def find_advertised_nodes(startstate_name, startstate_publickey):
  """
  <Purpose>
    Looks up nodes with publickeys that matches startstate_publickey. 
    If advertise_lookup fails, it sleeps and tries again. Tries upto
    10 times before it returns.

  <Arguments>
    startstate_name - the name of the state. In order for logging
    startstate_publickey - the key with which the node is identified

  <Exception>
    Nothing is raised but on failure we log the failure

  <Side Effects>
    None

  <Return>
    success, nodelist
      success - boolean, states weather advertise lookup worked
      nodelist -list of nodes that was found. Empty if advertise lookup failed

  """
 
  log("Looking for nodes with public key: \n"+str(startstate_publickey))

  #lookup nodes with the startstate_publickey. Lookup upto 10MB of nodes
  #if advertise_lookup fails, try it 10 times before moving on
  advertise_lookup_fail_count = 0
  while True:
    try:
      nodeprocesslist = advertise_lookup_helper(startstate_publickey)
      return True, nodeprocesslist

    except Exception, e:
      #increment fail count
      advertise_lookup_fail_count += 1
      log("advertise_lookup failed "+str(advertise_lookup_fail_count)+" times, while looking up nodes in "+startstate_name+" state with pub key:\n"+str(startstate_publickey))

      #if the lookup fails 10 times, break out of the while loop and log the info
      if advertise_lookup_fail_count >= 10:
        log("advertise_lookup failed 10 times...moving on to the next state transition function")
        return False, []

      print "Sleeping for 10 second before retrying advertise_lookup..."
      time.sleep(1)




@log_function_call
def combine_vessels(node_string, node_info, database_nodeobject, node_state_pubkey):
  """
  <Purpose>
    The purpose of this function is to combine all the vessels of 
    a node into one vessel.

  <Arguments>
    node_string - the name of the node. ip:port or NAT:port

    node_info - the information about the node including the vesseldict

    database_nodeobject - This is the nodeobject that was retrieved from our database

    node_state_pubkey - This is the state that the node should be in. After all the 
      vessels are combined, the final vessel should have this as its state

  <Exceptions>
    None

  <Side Effects>
    None

  <Return>
    extra_vessel - The final combined vessel
  """

  log("Beginning combine_vessels for the node: "+node_string)

  node_pubkey = database_nodeobject.owner_pubkey
  nodeID = node_info['nodekey']

  #the list that will hold all the vesselnames of the node
  vessel_list=[]

  #This is the extra vessel or the vessel that has the transition state
  extra_vessel = None





  log("Finding all the vessels in the node "+node_string+"...")
  for current_vessel in node_info['vessels']:
    #check to see if the vessels belong to us (SeattleGENI)
    if node_info['vessels'][current_vessel]['ownerkey'] == node_pubkey:
      #add the vessel to the list
      vessel_list.append(current_vessel)
      log("Added vessel "+current_vessel+" to vessel_list")
      
      #Check to see if the vessel carries the node state key
      if node_state_pubkey in node_info['vessels'][current_vessel]['userkeys']:
        #make sure that multiple vessels do not carry the node state
        if extra_vessel:
          log("There are multiple vessels with the node_state_pubkey. However we are combining vessels so this doesn't matter")
          
        #The extra vessel is the starting vessel that we start to combine with
        extra_vessel = current_vessel




  #if no vessel was found with the node_state_pubkey, then the node is corrupted
  if not extra_vessel:
    raise NodeError("Could not find any vessel with the node state key, therefore couldn't locate the extra vessel")

  #remove the starting vessel from the vessel list
  vessel_list.remove(extra_vessel)




  #combine all the vessels into one vessel
  log("Trying to combine all the vessels...")
  for current_vessel in vessel_list:
    #create a lock in order to combine vessel using the backend
    lockserver_handle = lockserver.create_lockserver_handle()
    node_transition_lib.log("Created lockserver_handle for use on node: "+nodeID)

    #acquire a lock for the node
    lockserver.lock_node(lockserver_handle, nodeID)
    node_transition_lib.log("Acquired node lock for nodeID: "+nodeID)
    
    #combine the vessels
    try:
      combined_vessel = backend.join_vessels(database_nodeobject, extra_vessel, current_vessel)
      log("Combined vessel "+extra_vessel+" and "+current_vessel+" into "+combined_vessel)
    except:
      raise NodeError("Failed to combine the vessels: "+extra_vessel+" and "+current_vessel)
    finally:
      #release the node lock and destroy lock handle
      lockserver.unlock_node(lockserver_handle, nodeID)
      node_transition_lib.log("released lock for node: "+nodeID)
      lockserver.destroy_lockserver_handle(lockserver_handle)
      node_transition_lib.log("Destroyed lockserver_handle for node: "+nodeID)

    extra_vessel = combined_vessel

  #TODO: Does the vessels need to be removed from the Database? ask jsamuel about this
  return extra_vessel    





#helper function now for testing.
@log_function_call
def advertise_lookup_helper(startstate_publickey):
  return advertise_lookup(startstate_publickey, maxvals = 10*1024*1024)



def noop(*args):
  # in some cases I don't want to do anything (i.e. just change state)
  pass



def log(message):
  """
  <Purpose>
    log information with a time stamp
  
  <Arguments>
    message - the message to log

  <Exceptions>
    None

  <Side Effects>
    log file may get edited if sterr and stdout is redirected

  <Return>
    None
  """

  seattlegeni.common.util.log.info(message)
  




def init_log(logname):
  """
  <Purpose>
    Setup circular logger
  
  <Exceptions>
    UnexpectedError - if the log system setup fails.

  <Side Effects>
    Creates a log file.

  <Argument>
    logname - the name of the logfile (log.logname)
  <Return>
    None
  """

  log_fd = "log."+str(logname)
  seattlegeni.common.util.log.set_log_level(seattlegeni.common.util.log.LOG_LEVEL_DEBUG)

  try:
    #setup a circular logger with 50MB of buffer
    log_output = logging.circular_logger(log_fd, 50*1024*1024)
    
    #redirect stderr and stdout to the log
    sys.stdout = log_output
    sys.stderr = log_output

  except:
    raise UnexpectedError, "Circular logger was not setup properly"



#a helper function to retrieve string form of pubkey, used for testing
def rsa_publickey_to_string_helper(pubkey):
  return rsa_publickey_to_string(pubkey)



#Exception if something unexpected goes wrong
class UnexpectedError(Exception):
  pass



class NodeProcessError(Exception):
  """This exception means the node is in an invalid state"""



class NodeError(Exception):
  """This exception means the node is in an invalid state"""



class DatabaseError(Exception):
  """This exception means that the database maindb had some kind of error or did not return properly"""
