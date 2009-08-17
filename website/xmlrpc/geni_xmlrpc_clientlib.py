"""
<Program Name>
  geni_xmlrpc_clientlib.py

<Started>
  6/28/2009

<Author>
  Jason Chen
  jchen@cs.washington.edu
  
<Purpose>
  A client library for communicating with the SeattleGENI XMLRPC Server.
  Clients can import this library, create an instance of the 'client' object,
  then invoke 'client' methods. These calls are translated to actual SeattleGENI
  XMLRPC calls, and after the XMLRPC call is completed, the results are returned
  back to the user.
"""

import xmlrpclib
import socket
# check to see if M2Crypto is installed
#try:
#  import M2Crypto
#except ImportError, err:
#  print "!!! ERROR: M2Crypto is not installed."
#  print "!!! Please make sure M2Crypto is properly installed into your Python distribution."

# SeattleGENI XMLRPC Fault Code Constants
FAULTCODE_OPERROR = 100
FAULTCODE_AUTHERROR = 101
FAULTCODE_INVALIDUSERINPUT = 102
FAULTCODE_NOTENOUGHCREDITS = 103
FAULTCODE_KEYALREADYREMOVED = 104

class client:
  def __init__(self, username, password,
               xmlrpc_url='https://seattlegeni.cs.washington.edu/xmlrpc', 
               allow_ssl_insecure=False):
    if not username or not password or not xmlrpc_url:
      raise ValueError("Parameters were invalid, please check your parameters.")
    elif allow_ssl_insecure == False:
      raise ValueError("WARNING: Operation of SSL in a secure manner is not available yet. Check the Seattle project website to ensure you have the latest version of geni_xmlrpc_clientlib.")

    # build authorization dict
    auth = {'username':username, 'password':password}
    self.auth = auth
    self.xmlrpc_url = xmlrpc_url
    self.allow_ssl_insecure = allow_ssl_insecure

    #self.proxy = M2Crypto.m2xmlrpclib.Server(self.xmlrpc_url,
    #             M2Crypto.m2xmlrpclib.SSL_Transport())
    try:
      self.proxy = xmlrpclib.Server(self.xmlrpc_url)
      
      # check auth is valid
      if(self.proxy.authcheck(self.auth) != 0):
        raise GENIAuthError
    except socket.error, (value, message):
      raise GENIOpError("Could not open a connection to the XMLRPC server specified at the given location.")
          
  def acquire_lan_resources(self, num):
    return self.acquire_resources('lan', num)

  def acquire_wan_resources(self, num):
    return self.acquire_resources('wan', num)

  def acquire_random_resources(self, num):
    return self.acquire_resources('random', num)
    
  def acquire_resources(self, res_type, num):
    rspec = {'rspec_type':res_type, 'number_of_nodes':num}
    acquired_list = []
    
    try:
      acquired_list = self.proxy.acquire_resources(self.auth, rspec)
    except xmlrpclib.Fault, fault:
      fault_text = str(fault).partition('\'')[2].rstrip('\'>\"')
      if fault.faultCode == FAULTCODE_INVALIDUSERINPUT:
        raise GENIInvalidUserInput(fault_text)
      elif fault.faultCode == FAULTCODE_OPERROR:
        raise GENIOpError(fault_text)
      elif fault.faultCode == FAULTCODE_NOTENOUGHCREDITS:
        raise GENINotEnoughCredits(fault_text)
      else:
        raise GENIOpError(fault_text)
    
    return acquired_list
      
  def release_resources(self, handlelist):
    if not isinstance(handlelist, list):
      raise TypeError("Invalid data type for handle list.")
    
    if not handlelist:
      raise ValueError("Given handlelist is empty.")
    
    try:
      self.proxy.release_resources(self.auth, handlelist)
    except xmlrpclib.Fault, fault:
      fault_text = str(fault).partition('\'')[2].rstrip('\'>\"')
      if fault.faultCode == FAULTCODE_INVALIDUSERINPUT:
        raise GENIInvalidUserInput(fault_text)
      else:
        raise GENIOpError(fault_text)

  def get_resource_info(self):
    return self.proxy.get_resource_info(self.auth)
      
  def get_account_info(self):
    return self.proxy.get_account_info(self.auth)
    
  def get_public_key(self):
    return self.proxy.get_public_key(self.auth)
      
  def get_private_key(self):
    try:
      self.proxy.get_private_key(self.auth)
    except xmlrpclib.Fault, fault:
      fault_text = str(fault).partition('\'')[2].rstrip('\'>\"')
      if fault.faultCode == FAULTCODE_KEYALREADYREMOVED:
        raise GENIKeyAlreadyRemoved(fault_text)
      else:
        raise GENIOpError(fault_text)
  
  def delete_private_key(self):
    try:
      self.proxy.delete_private_key(self.auth)
    except xmlrpclib.Fault, fault:
      fault_text = str(fault).partition('\'')[2].rstrip('\'>\"')
      if fault.faultCode == FAULTCODE_KEYALREADYREMOVED:
        raise GENIKeyAlreadyRemoved(fault_text)
      else:
        raise GENIOpError(fault_text)

# Custom SeattleGENI exceptions
class GENIError(Exception):
  pass

class GENIOpError(GENIError):
  pass

class GENIAuthError(GENIError):
  pass

class GENIInvalidUserInput(GENIError):
  pass

class GENINotEnoughCredits(GENIError):
  pass

class GENIKeyAlreadyRemoved(GENIError):
  pass
