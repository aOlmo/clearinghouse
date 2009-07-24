"""
<Program>
  maindb.py

<Started>
  29 June 2009

<Author>
  Justin Samuel

<Purpose>
  This is the API that should be used to interact with the Main Database.
  Functions in this module are the only way that other code should interact
  with the Main Database.
   
  Note: it is yet to be determined how strict the rule of "the only way to
  interact with the Main Database" should be. It is likely that functions
  in this module will return values that will, for example, lazily load
  data from the database. The point is to hide as much of the underlying
  database interaction from other code. It is definitely the case that
  no code outside this module should be modifying the database.
"""

import django.db

import random

from seattlegeni.common.exceptions import *

from seattlegeni.common.util.decorators import log_function_call
from seattlegeni.common.util.decorators import log_function_call_and_only_first_argument

from seattlegeni.common.util.assertions import *

from seattlegeni.website.control.models import Donation
from seattlegeni.website.control.models import GeniUser
from seattlegeni.website.control.models import Node
from seattlegeni.website.control.models import Vessel
from seattlegeni.website.control.models import VesselPort
from seattlegeni.website.control.models import VesselUserAccessMap

from django.contrib.auth.models import check_password





# The number of vessel credits each user gets regardless of donations.
FREE_VESSEL_CREDITS_PER_USER = 10

# Port from this range will be randomly selected as the usable_vessel_port for
# new users. Remember that range(x, y) is x inclusive, y exclusive. 
ALLOWED_USER_PORTS = range(63100, 63180)

# Number of ascii characters in generated API keys.
API_KEY_LENGTH = 32





@log_function_call
def init_database():
  """
  <Purpose>
    Initializes the database in a way that makes database transaction commits
    from other sources immediately visible. Must be called after creating
    any database connection. 
    scripts that need to see changes to the database even without starting a
    new transaction.
  <Arguments>
    None.
  <Exceptions>
    It is possible for a Django / Database error to be thrown (which is fatal).
  <Side Effects>
    This function makes it so that we see any transactions commits made by
    other database clients even within a single transaction on the side
    of the script that calls this function.
    This is done by changing the transaction isolation level of InnoDB from the
    default of "repeatable read" to instead be "read committed". For more info, see:
    http://dev.mysql.com/doc/refman/5.4/en/innodb-consistent-read.html
    http://dev.mysql.com/doc/refman/5.4/en/set-transaction.html
  <Returns>
    None.
  """
  # TODO: this should first check if the database is mysql, as it would be nice to be
  # able to run on sqlite for testing.
  django.db.connection.cursor().execute('set transaction isolation level read committed')





@log_function_call_and_only_first_argument
def create_user(username, password, email, affiliation, user_pubkey, user_privkey, donor_pubkey):
  """
  A 'user' lock should be held on the specified username before calling this
  function. We assume that code calling this function already checked to
  see whether a user by this username exists (and did so while holding the
  lock on that username).
  
  The code calling this function is responsible for first storing the corresponding
  private key of donor_pubkey in the keydb. In the case of the website calling this
  function, the website will make a call to the backend to request a new key.
  """
  # TODO: ensure that the password isn't being logged by @log_function_call
  # TODO: sanity check all parameters
  
  # Generate a random port for the user's usable vessel port.
  port = random.sample(ALLOWED_USER_PORTS, 1)[0]

  # Create the GeniUser (this is actually records in two different tables
  # underneath because of model inheretance, but django hides that from us).
  geniuser = GeniUser(username=username, password='', email=email,
                      affiliation=affiliation, user_pubkey=user_privkey,
                      user_privkey=user_privkey, donor_pubkey=donor_pubkey,
                      usable_vessel_port=port)
  # Set the password using this function so that it gets hashed by django.
  geniuser.set_password(password)
  geniuser.save()

  regenerate_api_key(geniuser)

  return geniuser





@log_function_call
def regenerate_api_key(geniuser):
  # Create a set of potential characters for the api key that includes the
  # numbers 0-9 and the uppercase charactesr A-Z, excluding the letter 'O'
  # because it looks too much like zero.
  population = []
  population.extend(range(ord('0'), ord('9') + 1))
  population.extend(range(ord('A'), ord('Z') + 1))
  population.remove(ord('O'))
  
  api_key = ""
  for character in random.sample(population, API_KEY_LENGTH):
    api_key += chr(character)
    
  geniuser.api_key = api_key
  geniuser.save()





@log_function_call
def create_node(node_identifier, last_known_ip, last_known_port, last_known_version, is_active, owner_pubkey, extra_vessel_name):
  """
  A 'node' lock should be held on the specified node identifier before calling this
  function. We assume that code calling this function already checked to
  see whether a node by this identifier exists (and did so while holding the
  lock on that node identifier).
  """
  # TODO: sanity check all parameters
  
  # Create the Node.
  node = Node(node_identifier=node_identifier, last_known_ip=last_known_ip,
              last_known_port=last_known_port, last_known_version=last_known_version,
              is_active=is_active, owner_pubkey=owner_pubkey,
              extra_vessel_name=extra_vessel_name)
  node.save()

  return node





@log_function_call
def create_donation(node, donor, resource_description_text):
  # TODO: sanity check all parameters
  
  # Create the Donation.
  donation = Donation(node=node, donor=donor,
                      resource_description_text=resource_description_text)
  donation.save()

  return donation





@log_function_call
def create_vessel(node, name):
  # TODO: sanity check all parameters
  
  # Create the Vessel.
  vessel = Vessel(node=node, name=name, acquired_by_user=None,
                  date_acquired=None, date_expires=None)
  vessel.save()
  
  return vessel





@log_function_call
def set_vessel_ports(vessel, port_list):
  # TODO: sanity check all parameters

  # Delete all existing VesselPort records for this vessel.
  VesselPort.objects.filter(vessel=vessel).delete()
  
  # Create a VesselPort record for each port in port_list.
  for port in port_list:
    vesselport = VesselPort(vessel=vessel, port=port)
    vesselport.save()





@log_function_call
def get_users_with_access_to_vessel(vessel):
  # TODO: sanity check all parameters

  # Let's return it as a list() rather than a django QuerySet.
  # Using list() causes the QuerySet to be converted to a list, which also
  # means the query is executed (no lazy loading).
  return list(VesselUserAccessMap.objects.filter(vessel=vessel))





@log_function_call
def get_vessels_accessible_by_user(user):
  # TODO: sanity check all parameters

  # Let's return it as a list() rather than a django QuerySet.
  # Using list() causes the QuerySet to be converted to a list, which also
  # means the query is executed (no lazy loading).
  return list(VesselUserAccessMap.objects.filter(user=user))





@log_function_call
def add_vessel_access_user(vessel, user):
  # TODO: sanity check all parameters

  # If the user already has access, don't throw an exception, just consider
  # the request done.
  mapqueryset = VesselUserAccessMap.objects.filter(vessel=vessel, user=user)
  if mapqueryset.count() == 1:
    return
  
  # Create a VesselUserAccessMap record.
  maprecord = VesselUserAccessMap(vessel=vessel, user=user)
  maprecord.save()
  
  
  
  
  
@log_function_call
def remove_vessel_access_user(vessel, user):
  # TODO: sanity check all parameters

  # Delete any map records for this user/vessel.
  VesselUserAccessMap.objects.filter(vessel=vessel, user=user).delete()





@log_function_call
def get_user(username):
  
  assert_str(username)
  
  geniuserqueryset = GeniUser.objects.filter(username=username)

  # Check if there are any users by this username.
  if geniuserqueryset.count() != 1:
    return None
  
  return geniuserqueryset[0]





@log_function_call_and_only_first_argument
def get_user_with_password(username, password):
  
  # The get_user call will assert_str(username).
  assert_str(password)
  
  geniuser = get_user(username)

  if geniuser is None:
    return None
  
  if not check_password(password, geniuser.password):
    return None
  
  return geniuser





@log_function_call_and_only_first_argument
def get_user_with_apikey(username, apikey):
  
  # The get_user call will assert_str(username).
  assert_str(apikey)
  
  geniuser = get_user(username)

  if geniuser is None:
    return None
  
  if not geniuser.apikey == apikey:
    return None
  
  return geniuser





@log_function_call
def get_node_identifier_from_vessel(vessel):
  # TODO: assert that vessel is a Vessel
  return vessel.node.node_identifier





#@log_function_call
#def set_user_keys(geniuser, user_pubkey, user_privkey=None):
#  """
#  <Purpose>
#    Change the user's user keys. This will only change it in the database.
#    The code that calls this function must make sure it is also changed
#    on any nodes the user has access to.
#  """
#  # TODO: ensure that the user_privkey isn't being logged by @log_function_call
#  # TODO: assert that geniuser is a GeniUser and that the keys are valid
#  # TODO: implement
#  raise NotImplementedError





@log_function_call
def delete_user_private_key(geniuser):
  """
  <Purpose>
    Delete the user's private user key.
  """
  # TODO assert that geniuser is a GeniUser
  geniuser.user_privkey = None
  geniuser.save()





@log_function_call
def get_donations_by_user(geniuser):
  # TODO assert that geniuser is a GeniUser
  
  # Let's return it as a list() rather than a django QuerySet.
  # Using list() causes the QuerySet to be converted to a list, which also
  # means the query is executed (no lazy loading).
  return list(Donation.objects.filter(donor=geniuser))





@log_function_call
def get_node(node_identifier):
  # TODO assert that node_identifier is a string
  return Node.objects.get(node_identifier=node_identifier)





@log_function_call
def get_acquired_vessels(geniuser):
  # TODO assert that geniuser is a GeniUser
  
  # Let's return it as a list() rather than a django QuerySet.
  # Using list() causes the QuerySet to be converted to a list, which also
  # means the query is executed (no lazy loading).
  return list(Vessel.objects.filter(acquired_by_user=geniuser))
  




@log_function_call
def get_available_wan_vessels(vesselcount):
  # TODO: this is just for initial development
  
  # Let's return it as a list() rather than a django QuerySet.
  # Using list() causes the QuerySet to be converted to a list, which also
  # means the query is executed (no lazy loading).
  return list(Vessel.objects.filter(acquired_by_user=None))





@log_function_call
def get_available_lan_vessels_by_subnet(vesselcount):
  # TODO: this is just for initial development
  
  # Let's return it as a list() rather than a django QuerySet.
  # Using list() causes the QuerySet to be converted to a list, which also
  # means the query is executed (no lazy loading).
  return [list(Vessel.objects.filter(acquired_by_user=None))]





@log_function_call
def get_available_rand_vessels(vesselcount):
  # TODO: this is just for initial development
  
  # Let's return it as a list() rather than a django QuerySet.
  # Using list() causes the QuerySet to be converted to a list, which also
  # means the query is executed (no lazy loading).
  return list(Vessel.objects.filter(acquired_by_user=None))





@log_function_call
def assert_user_can_acquire_resources(geniuser, requested_vessel_count):
  """
  Ensure the user is allowed to acquire these resources. This call will not
  only raise an InsufficientUserResourcesError if the additional vessels
  would cause the user to be over their limit, but will also throw an
  UnableToAcquireResourcesError if the user is not allowed to acquire
  resources for any other reason (e.g. they are banned?)
  If we ever started needing to ban users a lot, we'd probably want a
  separate error so the frontend can say something different in that case.
  """
  # This isn't in the assertions module because it is all database-related
  # information. I wanted to avoid making the assertions module dependent
  # on maindb. If it's confusing, the name of this method can be changed.
  
  # This can be made faster. When necessary, add a get_acquired_vessels_count() function.
  acquired_vessel_count = len(get_acquired_vessels(geniuser))

  # This can be made faster. When necessary, add a get_donations_by_user_count() function.
  vessel_credits_from_donations = len(get_donations_by_user(geniuser))  
  
  max_allowed_vessels = FREE_VESSEL_CREDITS_PER_USER + vessel_credits_from_donations 
  
  if requested_vessel_count + acquired_vessel_count > max_allowed_vessels:
    raise InsufficientUserResourcesError("Requested " + str(requested_vessel_count) + 
                                         " vessels, already acquired " + str(acquired_vessel_count) + 
                                         ", max allowed is " + str(max_allowed_vessels))





@log_function_call
def record_acquired_vessel(geniuser, vessel):
  """
  <Purpose>
    Performs all database operations necessary to record the fact that a vessel
    was acquired by a user.
  """
  # We aren't caching any information with the user record about how many
  # resources have been acquired, so the only thing we need to do is make the
  # vessel as having been acquired by this user.
  vessel.acquired_by_user = geniuser
  vessel.save()





@log_function_call
def record_released_vessel(vessel):
  """
  <Purpose>
    Performs all database operations necessary to record the fact that a vessel
    was released.
  """
  # We aren't caching any information with the user record about how many
  # resources have been acquired, so the only thing we need to do is make the
  # vessel as having not having been acquired by any user.
  vessel.acquired_by_user = None
  vessel.save()

