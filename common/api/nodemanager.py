"""
   Author: Justin Cappos

   Start Date: 30 May 2009

   Description:

   This is the node manager interface for the backend of seattleGENI.
   This handles node communication and is stubbed out for testing / modularity.
"""

import repyhelper
from seattlegeni.common.exceptions import *

repyhelper.translate_and_import("nmclient.repy")
repyhelper.translate_and_import("time.repy")





def init_nmapi():
  """
    <Purpose>
      Initializes the node manager.   Must be called before other operations.

    <Arguments>
      None.

    <Exceptions>
      It is possible for a time error to be thrown (which is fatal).

    <Side Effects>
      This function contacts a NTP server and gets the current time.
      This is needed for the crypto operations that we do later.
      This uses UDP port 23421

    <Returns>
      None.
  """
  time_updatetime(23421)





def do_changeuser_call(ip, port, pubkeystring, privkeystring, key_list):
  # TODO
  pass





def _do_signed_call(ip, port, pubkeystring, privkeystring, *callargs):
  """
    <Purpose>
      Performs an action that requires authentication on a remote node.

    <Arguments>
      ip:
        The node's IP address (a string)
      port:
        The port that the node manager is running on (an int)
      pubkeystring:
        The public key used for authentication
      privkeystring:
        The private key used for authentication
      *callargs:
        The arguments to give the node.   The first argument will usually be
        the call type (i.e. "ChangeUsers")

    <Exceptions>
      Exception / NMClientException are raised when the call fails.   

    <Side Effects>
      Whatever side effects the call has on the remote node.

    <Returns>
      None.
  """
  nmhandle = nmclient_createhandle(ip, port)

  myhandleinfo = nmclient_get_handle_info(nmhandle)
  myhandleinfo['publickey'] = rsa_string_to_publickey(pubkeystring)
  myhandleinfo['privatekey'] = rsa_string_to_privatekey(privkeystring)
  nmclient_set_handle_info(nmhandle, myhandleinfo)

  nmclient_signedsay(nmhandle, *callargs)
