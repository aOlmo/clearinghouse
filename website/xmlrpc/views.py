"""
<Program>
  views.py

<Started>
  6 July 2009

<Author>
  Jason Chen
  Justin Samuel

<Purpose>
  This file defines all of the public SeattleGeni XMLRPC functions. When the
  SeattleGENI XMLRPC API changes, this file will generally always need to be
  modified.  

  To create a new xmlrpc function, just create a new method in the
  PublicXMLRPCFunctions class below. All public methods in that class
  are automatically registered with the xmlrpc dispatcher.

  The functions defined here should generally be making calls to the
  controller interface to perform any work or retrieve data.

  Be sure to use the following decorators with each function, in this order:

  @staticmethod -- this is a python decorator that prevents 'self'
                   from being passed as the first argument.
  @log_function_call -- this is our own decorator for logging purposes.
"""

import traceback

# Make available all of our own standard exceptions.
from seattlegeni.common.exceptions import *

from seattlegeni.common.util import log

# This is the logging decorator use use.
from seattlegeni.common.util.decorators import log_function_call

# All of the work that needs to be done is passed through the controller interface.
from seattlegeni.website.control import interface

# Used for raising xmlrpc faults
import xmlrpclib

class PublicXMLRPCFunctions(object):
  """
  All public functions of this class are automatically exposed as part of the
  xmlrpc interface.
  
  Each method should be sure to check the user input and return useful errors
  to the client if the input is invalid. Note that raising an AssertionError
  (e.g. through a call to an assert_* method) won't be sufficient, as those
  should only indicate something going wrong in our code. 
  """

  def _dispatch(self, method, args):
    """
    We provide a _dispatch function (which SimpleXMLRPCServer looks for and
    uses) so that we can log exceptions due to our programming errors within
    seattlegeni as well to detect incorrect usage by clients.
    """
      
    try:
      # Get the requested function (making sure it exists).
      try:
        func = getattr(self, method)
      except AttributeError:
        raise InvalidRequestError("The requested method '" + method + "' doesn't exist.")
      
      # Call the requested function.
      return func(*args)
    
    except InvalidRequestError:
      log.error("The xmlrpc server was used incorrectly: " + traceback.format_exc())
      raise
    
    except:
      # We assume all other exceptions are bugs in our code.

      # TODO: this should probably send an email or otherwise make noise.
      log.critical("Internal error while handling an xmlrpc request: " + traceback.format_exc())

      # It's not unlikely that the user ends up seeing this message, so we
      # are careful about what the content of the message is.
      raise ProgrammerError("Internal error while handling the xmlrpc request.")
      


  @staticmethod
  @log_function_call
  def acquire_resources(auth, rspec):
    """
    <Purpose>
      Acquires resources for users over XMLRPC. 
    <Arguments>
      auth
        An authorization dict of the form {'username':username, 'password':password}
      rspec
        A resource specificiation dict of the form {'rspec_type':type, 'number_of_nodes':num}
    <Exceptions>
      Raises xmlrpclib Fault objects:
        100, "GENIOpError" for internal errors.
        103, "GENINotEnoughCredits" if user has insufficient vessel credits to complete request.
    <Returns>
      A list of 'info' dictionaries, each 'infodict' contains acquired vessel info.
    """
    geni_user = _auth(auth)
    
    resource_type = rspec['rspec_type']
    num_vessels = rspec['number_of_nodes']
    acquired_vessels = []
    
    # validate rspec data
    if not isinstance(resource_type, str) or not isinstance(resource_num, int):
      raise xmlrpclib.Fault(102, "GENIInvalidUserInput: rspec has invalid data types.")
    
    if (resource_type != "lan" and resource_type != "wan" and \
    resource_type != "random") or resource_num < 1:
      raise xmlrpclib.Fault(102, "GENIInvalidUserInput: rspec has invalid values.")
      
    # since acquired_vessels expects rand instead of random
    if resource_type == 'random':
      resource_type = 'rand'
    
    try:
      acquired_vessels = interface.acquire_vessels(geni_user, num_vessels, resource_type)
    except DoesNotExistError:
      raise xmlrpclib.Fault(100, "GENIOpError: Internal GENI Error! Recieved a DoesNotExistError while calling interface.acquire_vessels")
    except UnableToAcquireResourcesError, err:
      raise xmlrpclib.Fault(100, "GENIOpError: Internal GENI Error! Unable to fulfill vessel acquire request at this given time. Please try again later.")
    except InsufficientUserResourcesError, err:
      raise xmlrpclib.Fault(103, "GENINotEnoughCredits: You do not have enough vessel credits to acquire the number of vessels requested.")
    except ProgrammerError, err:
      raise xmlrpclib.Fault(100, "GENIOpError: Internal GENI Error! Recieved a ProgrammerError while calling interface.acquire_vessels. Details: " + str(err)) 
    
    # since acquire_vessels returns a list of Vessel objects, we
    # need to convert them into a list of 'info' dictionaries.
    return interface.get_vessel_infodict_list(acquired_vessels)
  


  @staticmethod
  @log_function_call
  def release_resources(auth, vesselhandle_list):
    """
    <Purpose>
      Release resources for a user over XMLRPC.
    <Arguments>
      auth
        An authorization dict of the form {'username':username, 'password':password}
      vesselhandle_list
        A list of vessel handles
    <Exceptions>
      Raises xmlrpclib Fault objects:
        100, "GENIOpError" for internal GENI errors.
        102, "GENIInvalidUserInput" if a user provides invalid vessel handles.
    <Returns>
      0 on success. Raises a fault otherwise.
    """
    geni_user = _auth(auth)
  
    #TODO: validate vessel_list.
    #if not isinstance(vessel_list, list):
    #  raise TypeError("Invalid data types in handle list.")
    
    # since we're given a list of vessel 'handles', we need to convert them to a 
    # list of actual Vessel objects; as release_vessels_of_user expects Vessel objs.
    try:
      list_of_vessel_objs = interface.get_vessel_list(vesselhandle_list)
    except DoesNotExistError:
      # given handle refers to a non-existant vessel
      # throw a fault?
      pass
    
    try:
      interface.release_vessels(geni_user, list_of_vessel_objs)
    except DoesNotExistError:
      raise xmlrpclib.Fault(100, "GENIOpError: Internal GENI Error! Caught a DoesNotExistError while calling interface.release_vessels")
    except InvalidRequestError, err:
      # vessel exists but isn't valid for you to use.
      raise xmlrpclib.Fault(102, "GENIInvalidUserInput: Tried to release a vessel that didn't belong to you. Details: " + str(err))
    
    return 0
  
  
  
  @staticmethod
  @log_function_call
  def get_resource_info(auth):
    """
    <Purpose>
      Gets a user's acquired vessels over XMLRPC.
    <Arguments>
      auth
        An authorization dict of the form {'username':username, 'password':password}
    <Exceptions>
      None.
    <Returns>
      A list of 'info' dictionaries, each 'infodict' contains vessel info.
    """
    geni_user = _auth(auth)
    user_vessels = interface.get_acquired_vessels(geni_user)
    return interface.get_vessel_infodict_list(user_vessels)
  
  
  @staticmethod
  @log_function_call
  def get_account_info(auth):
    """
    <Purpose>
      Gets a user's account info for a client over XMLRPC.
    <Arguments>
      auth
        An authorization dict of the form {'username':username, 'password':password}
    <Exceptions>
      None.
    <Returns>
      A dictionary containing account info.
    """
    geni_user = _auth(auth)
    user_port = geni_user.usable_vessel_port
    user_name = geni_user.username
    urlinstaller = ""
    private_key_exists = True
    if geni_user.user_privkey == "":
      private_key_exists = False
    # unsure how to get this data
    max_vessel = 0
    user_affiliation = geni_user.affiliation
    infodict = {'user_port':user_port, 'user_name':user_name, 
                'urlinstaller':urlinstaller, 'private_key_exists':private_key_exists, 
                'max_vessel':max_vessel, 'user_affiliation':user_affiliation}
    return infodict
  
  
  
  @staticmethod
  @log_function_call
  def get_public_key(auth):
    # Gets a user's public key.
    geni_user = _auth(auth)
    return geni_user.user_pubkey
  
  
  
  @staticmethod
  @log_function_call
  def get_private_key(auth):
    # Gets a user's private key.
    geni_user = _auth(auth)
    return geni_user.user_privkey
  
  
  
  @staticmethod
  @log_function_call
  def delete_private_key(auth):
    """
    <Purpose>
      Deletes a user's private key for a client over XMLRPC.
    <Arguments>
      auth
        An authorization dict of the form {'username':username, 'password':password}
    <Exceptions>
      Raises xmlrpclib Fault Objects:
        104, "GENIKeyAlreadyRemoved" if the user's privkey was already removed.
    <Returns>
      Returns True on success, raises a fault otherwise.
    """
    geni_user = _auth(auth)
    if geni_user.user_privkey == "":
      raise xmlrpclib.Fault(104, "GENIKeyAlreadyRemoved: Your private key has already been removed.")
    interface.delete_private_key(geni_user)
    return True
  
  
  
  @staticmethod
  @log_function_call
  def authcheck(auth):
    """
    <Purpose>
      Checks a user's authorization details.
    <Arguments>
      auth
        An authorization dict of the form {'username':username, 'password':password}
    <Exceptions>
      None.
    <Returns>
      Returns 0 on valid auth credentials, -1 otherwise.
    """
    username = auth['username']
    password = auth['password']
    geni_user = interface.get_user_with_password(username, password)
    if geni_user == None:
      return -1
    else:
      return 0





@log_function_call
def _auth(auth):
  """
  <Purpose>
    Internally used function that performs actual authorization.
  <Arguments>
    auth
      An authorization dict of the form {'username':username, 'password':password}
  <Exceptions>
    Raises xmlrpclib Fault Objects:
      101, "GENIAuthError" if user auth fails.
  <Returns>
    On successful authentication, returns a geniuser object. Raises a fault otherwise.
  """
  username = auth['username']
  password = auth['password']
  try:
    geni_user = interface.get_user_with_password(username, password)
  except DoesNotExistError:
    raise xmlrpclib.Fault(101, "GENIAuthError: User auth failed.")
  return geni_user