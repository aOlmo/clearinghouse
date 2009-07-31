"""
Provides utilities for dealing with cryptography-related needs in seattlegeni,
such as verifying the validity of public keys.
"""

from seattle import repyhelper
from seattle import repyportability

repyhelper.translate_and_import("rsa.repy")


def is_valid_pubkey_string(pubkeystring):
  """
  <Purpose>
    Determine whether a pubkey string looks like a valid public key.
  <Arguments>
    pubkeystring
      The string we want to find out if it is a valid pubkey string.
  <Exceptions>
    None
  <Side Effects>
    None
  <Returns>
    True if pubkeystring looks like a valid pubkey, False otherwise.
    Currently this uses functions that aren't conclusive about validity of the
    key, but for our purposes we just want to make sure it's generally the
    correct data format.
  """
  try:
    possiblepubkey = rsa_string_to_publickey(pubkeystring)
  except ValueError:
    return False

  return rsa_is_valid_publickey(possiblepubkey)

