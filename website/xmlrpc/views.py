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

# Make available all of our own standard exceptions.
from seattlegeni.common.exceptions import *

# This is the logging decorator use use.
from seattlegeni.common.util.decorators import log_function_call

# All of the work that needs to be done is passed through the controller interface.
from seattlegeni.website.control import interface



class PublicXMLRPCFunctions(object):
  

  @staticmethod
  @log_function_call
  def acquire_resources():
    return "acquire_resources"
  
  

  @staticmethod
  @log_function_call
  def release_resources():
    return "release_resources"
  
  
  
  @staticmethod
  @log_function_call
  def get_resource_info(auth):
# For example (this is not correct, just conceptual):
#    # I'd imagine you'd have a helper function that would get the geniuser
#    # and would throw some Fault or Error if the auth info isn't valid,
#    # rather than repeat this in every function.
#    username = auth["username"]
#    password = auth["password"]
#    geniuser = interface.get_user_with_password(username, password)
#    if geniuser is None:
#      # Not sure if this is the right way when doing this through django.
#      return xmlrpclib.FaultOrWhatever("Invalid authorization credentials.")
#    
#    resource_list = interface.get_vessels_acquired_by_user(geniuser)
#    resource_list = []
#    for resource_item in resource_query_set:
#      resources_list.append(resource_item.name)
#      
#    return resources_list
    pass
  
  
  @staticmethod
  @log_function_call
  def get_account_info():
    return "get_account_info"
  
  
  
  @staticmethod
  @log_function_call
  def get_public_key():
    return "get_public_key"
  
  
  
  @staticmethod
  @log_function_call
  def get_private_key():
    return "get_private_key"
  
  
  
  @staticmethod
  @log_function_call
  def delete_private_key():
    return "delete_private_key"
  
  
  
  @staticmethod
  @log_function_call
  def authcheck():
    return "authcheck"

