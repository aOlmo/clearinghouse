"""
<Program>
  lockserver_daemon.py

<Started>
  30 June 2009

<Author>
  Justin Samuel

<Purpose>
  This is the XML-RPC Backend that is used by various components of
  SeattleGeni.
 

XML-RPC Interface:
 
 TODO: describe the interface
"""

import sys
import time
import traceback

import thread

# These are used to build a single-threaded XMLRPC server.
import SocketServer
import SimpleXMLRPCServer

import xmlrpclib

# To send the admins emails when there's an unhandled exception.
import django.core.mail 

# We use django.db.reset_queries() to prevent memory "leaks" due to query
# logging when settings.DEBUG is True.
import django.db 

# The config module contains the authcode that is required for performing
# privileged operations.
import seattlegeni.backend.config

from seattlegeni.common.api import keydb
from seattlegeni.common.api import keygen
# The lockserver is needed by the vessel cleanup thread.
from seattlegeni.common.api import lockserver
from seattlegeni.common.api import maindb
from seattlegeni.common.api import nodemanager

from seattlegeni.common.exceptions import *

from seattlegeni.common.util import log
from seattlegeni.common.util import parallel

from seattlegeni.common.util.assertions import *

from seattlegeni.common.util.decorators import log_function_call
from seattlegeni.common.util.decorators import log_function_call_without_first_argument

from seattlegeni.website import settings


# The port that we'll listen on.
LISTENPORT = 8020





class ThreadedXMLRPCServer(SocketServer.ThreadingMixIn, SimpleXMLRPCServer.SimpleXMLRPCServer):
  """This is a threaded XMLRPC Server. """
  




def _get_node_handle_from_nodeid(nodeid):
  
  # Raises DoesNotExistError if no such node exists.
  node = maindb.get_node(nodeid)
  # Raises DoesNotExistError if no such key exists.  
  owner_privkey = keydb.get_private_key(node.owner_pubkey)
  
  return nodemanager.get_node_handle(nodeid, node.last_known_ip, node.last_known_port, node.owner_pubkey, owner_privkey)

    



def _assert_number_of_arguments(functionname, args, exact_number):
  """
  <Purpose>
    Ensure that an args tuple which one of the public xmlrpc functions was
    called with has an expected number of arguments.
  <Arguments>
    functionname:
      The name of the function whose number of arguments are being checked.
      This is just for logging in the case that the arguments don't match.
    args:
      A tuple of arguments (received by the other function through *args).
    exact_number:
      The exact number of arguments that must be in the args tuple.
  <Exceptions>
    Raises InvalidRequestError if args does not contain exact_number
    items.
  <Side Effects>
    None.
  <Returns>
    None.
  """
  if len(args) != exact_number:
    message = "Invalid number of arguments to function " + functionname + ". "
    message += "Expected " + str(exact_number) + ", received " + str(len(args)) + "."
    raise InvalidRequestError(message)





def _assert_valid_authcode(authcode):
  if authcode != seattlegeni.backend.config.authcode:
    raise InvalidRequestError("The provided authcode (" + authcode + ") is invalid.")





class BackendPublicFunctions(object):
  """
  All public functions of this class are automatically exposed as part of the
  xmlrpc interface.
  """
  
  def _dispatch(self, method, args):
    """
    We provide a _dispatch function (which SimpleXMLRPCServer looks for and
    uses) so that we can log exceptions due to our programming errors within
    the backend as well to detect incorrect usage by clients.
    """
      
    try:
      # Get the requested function (making sure it exists).
      try:
        func = getattr(self, method)
      except AttributeError:
        raise InvalidRequestError("The requested method '" + method + "' doesn't exist.")
      
      # Call the requested function.
      return func(*args)
    
    except NodemanagerCommunicationError, e:
      raise xmlrpclib.Fault(100, "Node communication failure: " + str(e))
    
    except (DoesNotExistError, InvalidRequestError, AssertionError):
      log.error("The backend was used incorrectly: " + traceback.format_exc())
      raise
    
    except:
      # We assume all other exceptions are bugs in the backend. Unlike the
      # lockserver where it might result in broader data corruption, here in
      # the backend we allow the backend to continue serving other requests.
      # That is, we don't go through steps to try to shutdown the backend.
      
      message = "The backend had an internal error: " + traceback.format_exc()
      log.critical(message)
      
      # Send an email to the addresses listed in settings.ADMINS
      if not settings.DEBUG:
        subject = "Critical SeattleGeni backend error"
        django.core.mail.mail_admins(subject, message)
      
      raise
      




  # Using @staticmethod makes it so that 'self' doesn't get passed in as the first arg.
  @staticmethod
  @log_function_call
  def GenerateKey(*args):
    """
    This is a public function of the XMLRPC server. See the module comments at
    the top of the file for a description of how it is used.
    """
    _assert_number_of_arguments('GenerateKey', args, 1)
    
    keydescription = args[0]
    
    assert_str(keydescription)
    
    # Generate a new keypair.
    (pubkey, privkey) = keygen.generate_keypair()
    
    # Store the private key in the keydb.
    keydb.set_private_key(pubkey, privkey, keydescription)
    
    # Return the public key.
    return pubkey





  # Using @staticmethod makes it so that 'self' doesn't get passed in as the first arg.
  @staticmethod
  @log_function_call
  def SetVesselUsers(*args):
    """
    This is a public function of the XMLRPC server. See the module comments at
    the top of the file for a description of how it is used.
    """
    _assert_number_of_arguments('SetVesselUsers', args, 3)
    (nodeid, vesselname, userkeylist) = args
    
    assert_str(nodeid)
    assert_str(vesselname)
    assert_list(userkeylist)
    
    for userkey in userkeylist:
      assert_str(userkey)

    # Note: The nodemanager checks whether each key is a valid key and will
    #       raise an exception if it is not.
      
    # Raises a DoesNotExistError if there is no node with this nodeid.
    nodehandle = _get_node_handle_from_nodeid(nodeid)
    
    # Raises NodemanagerCommunicationError if it fails.
    nodemanager.change_users(nodehandle, vesselname, userkeylist)





  # Using @staticmethod makes it so that 'self' doesn't get passed in as the first arg.
  @staticmethod
  @log_function_call_without_first_argument
  def SetVesselOwner(*args):
    """
    This is a public function of the XMLRPC server. See the module comments at
    the top of the file for a description of how it is used.
    """
    _assert_number_of_arguments('SetVesselOwner', args, 4)
    (authcode, nodeid, vesselname, ownerkey) = args
    
    assert_str(authcode)
    assert_str(nodeid)
    assert_str(vesselname)
    assert_str(ownerkey)
    
    _assert_valid_authcode(authcode)
    
    # Note: The nodemanager checks whether the owner key is a valid key and
    #       will raise an exception if it is not.
    
    # Raises a DoesNotExistError if there is no node with this nodeid.
    nodehandle = _get_node_handle_from_nodeid(nodeid)
    
    # Raises NodemanagerCommunicationError if it fails.
    nodemanager.change_owner(nodehandle, vesselname, ownerkey)
    
    
    
 
    
  # Using @staticmethod makes it so that 'self' doesn't get passed in as the first arg.
  @staticmethod
  @log_function_call_without_first_argument
  def SplitVessel(*args):
    """
    This is a public function of the XMLRPC server. See the module comments at
    the top of the file for a description of how it is used.
    """
    _assert_number_of_arguments('SplitVessels', args, 4)
    (authcode, nodeid, vesselname, desiredresourcedata) = args
    
    assert_str(authcode)
    assert_str(nodeid)
    assert_str(vesselname)
    assert_str(desiredresourcedata)
    
    _assert_valid_authcode(authcode)
    
    # Raises a DoesNotExistError if there is no node with this nodeid.
    nodehandle = _get_node_handle_from_nodeid(nodeid)
    
    # Raises NodemanagerCommunicationError if it fails.
    return nodemanager.split_vessel(nodehandle, vesselname, desiredresourcedata)
    
    



  # Using @staticmethod makes it so that 'self' doesn't get passed in as the first arg.
  @staticmethod
  @log_function_call_without_first_argument
  def JoinVessels(*args):
    """
    This is a public function of the XMLRPC server. See the module comments at
    the top of the file for a description of how it is used.
    """
    _assert_number_of_arguments('JoinVessels', args, 4)
    (authcode, nodeid, firstvesselname, secondvesselname) = args
    
    assert_str(authcode)
    assert_str(nodeid)
    assert_str(firstvesselname)
    assert_str(secondvesselname)
    
    _assert_valid_authcode(authcode)
    
    # Raises a DoesNotExistError if there is no node with this nodeid.
    nodehandle = _get_node_handle_from_nodeid(nodeid)
    
    # Raises NodemanagerCommunicationError if it fails.
    return nodemanager.join_vessels(nodehandle, firstvesselname, secondvesselname)
      




def cleanup_vessels():
  
  # This thread will never end this lockserver session.
  lockserver_handle = lockserver.create_lockserver_handle()

  log.info("[cleanup_vessels] cleanup thread started.")

  # Run forever.
  while True:
    
    try:
      
      # Sleep a few seconds for those times where we don't have any vessels to clean up.
      time.sleep(5)
      
      # We shouldn't be running the backend in production with
      # settings.DEBUG = True. Just in case, though, tell django to reset its
      # list of saved queries each time through the loop. Note that this is not
      # specific to the cleanup thread as other parts of the backend are using
      # the maindb, as well, so we're overloading the purpose of the cleanup
      # thread by doing this here. This is just a convenient place to do it.
      # See http://docs.djangoproject.com/en/dev/faq/models/#why-is-django-leaking-memory
      # for more info.
      if settings.DEBUG:
        django.db.reset_queries()
      
      # First, make it so that expired vessels are seen as dirty.
      markedcount = maindb.mark_expired_vessels_as_dirty()
      if markedcount > 0:
        log.info("[cleanup_vessels] " + str(markedcount) + " expired vessels have been marked as dirty.")

      # Get a list of vessels to clean up. This doesn't include nodes known to
      # be inactive as we would just continue failing to communicate with nodes
      # that are down.
      cleanupvessellist = maindb.get_vessels_needing_cleanup()
      if len(cleanupvessellist) == 0:
        continue
        
      log.info("[cleanup_vessels] " + str(len(cleanupvessellist)) + " vessels to clean up: " + str(cleanupvessellist))
      
      # Get a list of nodes to lock.
      node_id_list = []
      for vessel in cleanupvessellist:
        node_id = maindb.get_node_identifier_from_vessel(vessel)
        # Lock names must be unique, and there could be multiple vessels from the
        # same node in the vessel_list.
        if node_id not in node_id_list:
          node_id_list.append(node_id)
            
      # Lock the nodes that these vessels are on and always unlock them.
      lockserver.lock_multiple_nodes(lockserver_handle, node_id_list)
      try:
        # Parallelize the cleanup of these vessels.
        parallel_results = parallel.run_parallelized(cleanupvessellist, _cleanup_single_vessel)
        
        if len(parallel_results["exception"]) > 0:
          vessel, exception_message = parallel_results["exception"][0]
          raise InternalError("Unhandled exception during parallelized vessel cleanup: " + exception_message)
          
      finally:
        # Unlock the nodes.
        lockserver.unlock_multiple_nodes(lockserver_handle, node_id_list)
        
    except:
      message = "[cleanup_vessels] Something very bad happened: " + traceback.format_exc()
      log.critical(message)
      
      # Send an email to the addresses listed in settings.ADMINS
      if not settings.DEBUG:
        subject = "Critical SeattleGeni backend error"
        django.core.mail.mail_admins(subject, message)
        
        # Sleep for ten minutes to make sure we don't flood the admins with error
        # report emails.
        time.sleep(600)
      




def _cleanup_single_vessel(vessel):
  # Now that we have a lock on the node that this vessel is on, find out
  # if we should still clean up this vessel (e.g. maybe a node state
  # transition script moved the node to a new state and this vessel was
  # removed).
  needscleanup, reasonwhynot = maindb.does_vessel_need_cleanup(vessel)
  if not needscleanup:
    log.info("[cleanup_vessels] Vessel " + str(vessel) + " no longer needs cleanup: " + reasonwhynot)
    return
  
  nodeid = maindb.get_node_identifier_from_vessel(vessel)
  
  try:
    nodehandle = _get_node_handle_from_nodeid(nodeid)
  except DoesNotExistError:
    message = "A node doesn't in the database anymore! " + traceback.format_exc()
    log.critical(message)
    raise InternalError(message)
  
  try:
    log.info("[cleanup_vessels] About to ChangeUsers on vessel " + str(vessel))
    nodemanager.change_users(nodehandle, vessel.name, [''])
    log.info("[cleanup_vessels] About to ResetVessel on vessel " + str(vessel))
    nodemanager.reset_vessel(nodehandle, vessel.name)
  except NodemanagerCommunicationError:
    # We don't pass this exception up. Maybe the node is offline now. At some
    # point, it will be marked in the database as offline (should we be doing
    # that here?). At that time, the dirty vessels on that node will not be
    # in the cleanup list anymore.
    log.info("[cleanup_vessels] Failed to cleanup vessel " + str(vessel) + ". " + traceback.format_exc())
    return
    
  # We only mark it as clean if no exception was raised when trying to
  # perform the above nodemanager operations.
  maindb.mark_vessel_as_clean(vessel)

  log.info("[cleanup_vessels] Successfully cleaned up vessel " + str(vessel))





def main():
  
  # Initialize the main database.
  maindb.init_maindb()

  # Initialize the key database.
  keydb.init_keydb()
  
  # Initialize the nodemanager.
  nodemanager.init_nodemanager()

  # Start the background thread that does vessel cleanup.
  thread.start_new_thread(cleanup_vessels, ())

  # Register the XMLRPCServer. Use allow_none to allow allow the python None value.
  server = ThreadedXMLRPCServer(("127.0.0.1", LISTENPORT), allow_none=True)

  log.info("Backend listening on port " + str(LISTENPORT) + ".")

  server.register_instance(BackendPublicFunctions()) 
  while True:
    server.handle_request()





if __name__ == '__main__':
  try:
    main()
  except KeyboardInterrupt:
    log.info("Exiting on KeyboardInterrupt.")
    sys.exit(0)
