"""
<Program>
  keygen.py

<Started>
  29 June 2009

<Author>
  Justin Samuel

<Purpose>
   This is the API that should be used to generate new public/private key pairs.
"""


from seattlegeni.common.exceptions import *

from seattlegeni.common.util.decorators import log_function_call



KEYDAEMON_HOST = "127.0.0.1"

KEYDAEMON_PORT = "8030"




@log_function_call
def generate_keypair():
  """
  <Purpose>
    Obtain a new (unused) public/private keypair.
  <Arguments>
    None
  <Exceptions>
    TODO: need to revist this
  <Side Effects>
    Requests a key from the keygen daemon.
  <Returns>
    A tuple in the format (pubkey, privkey).
  """
  
  # TODO: implement
  return ('TODO', 'TODO')
