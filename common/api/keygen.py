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



KEYDAEMON_HOST = "localhost"

KEYDAEMON_PORT = "250"


@log_function_call
def generate_keypair(keydaemon_host=KEYDAEMON_HOST, keydaemon_port=KEYDAEMON_PORT):
  return ('TODO', 'TODO')
