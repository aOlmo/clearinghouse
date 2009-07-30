"""
Provides utilities for dealing with public keys.
"""

# TODO: use rsa.repy as soon as we can figure out a reliable way to do it in
# the website. The issue right now is that it is not clear where rsa.repy
# needs to reside. Is it impacted by the cwd that apache will run under?
# So, for now, we'll just make a copy of the rsa.repy functions we wanted.
# This may be fixed with #538 ("repyhelper.translate() should search the
# python path for repy files")
#import repyhelper
#import repyportability
#
#repyhelper.translate_and_import("rsa.repy")


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
    possiblepubkey = _rsa_string_to_publickey(pubkeystring)
  except ValueError:
    return False

  return _rsa_is_valid_publickey(possiblepubkey)





# Copied from rsa.repy. See note above the commented out repyhelper at the top
# of this module.
def _rsa_is_valid_publickey(key):
  """
  <Purpose>
    This tries to determine if a key is valid.   If it returns False, the
    key is definitely invalid.   If True, the key is almost certainly valid
  
  <Arguments>
    key:
        A dictionary of the form {'n': 1.., 'e': 6..} with the 
        keys 'n' and 'e'.  
                  
  <Exceptions>
    None

  <Side Effects>
    None
    
  <Return>
    If the key is valid, True will be returned. Otherwise False will
    be returned.
    
  """
  # must be a dict
  if type(key) is not dict:
    return False

  # missing the right keys
  if 'e' not in key or 'n' not in key:
    return False

  # has extra data in the key
  if len(key) != 2:
    return False

  for item in ['e', 'n']:
    # must have integer or long types for the key components...
    if type(key[item]) is not int and type(key[item]) is not long:
      return False

  if key['e'] < key['n']:
    # Seems valid...
    return True
  else:
    return False





# Copied from rsa.repy. See note above the commented out repyhelper at the top
# of this module.
def _rsa_string_to_publickey(mystr):
  """
  <Purpose>
    To read a private key string and return a dictionary in 
    the appropriate format: {'n': 1.., 'e': 6..} 
    with the keys 'n' and 'e'.
  
  <Arguments>
    mystr:
          A string containing the publickey, should be in the format
          created by the function rsa_publickey_to_string.
          Example if e=3 and n=21, mystr = "3 21"
          
  <Exceptions>
    ValueError if the string containing the privateky is 
    in a invalid format.

  <Side Effects>
    None
    
  <Return>
    Returns a publickey dictionary of the form 
    {'n': 1.., 'e': 6..} with the keys 'n' and 'e'.
  
  """
  if len(mystr.split()) != 2:
    raise ValueError, "Invalid public key string"
  
  return {'e':long(mystr.split()[0]), 'n':long(mystr.split()[1])}

