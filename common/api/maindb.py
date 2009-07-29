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
  
  We try to keep all manual transaction management in seattlegeni to within
  this module. The general idea is that the default behavior of django is
  what we want in most places (to commit any time data-altering functions
  are called, such as .save() or .delete()). However, in a few cases we
  want multiple data-altering functions to be committed atomically, so we
  use @transaction.commit_manually.
"""

# It is a bit confusing to just import datetime because then you have to use
# things like 'datetime.datetime.now()'. So, import the parts we need.
from datetime import datetime
from datetime import timedelta

import django.core.exceptions
import django.db

from django.contrib.auth.models import check_password
from django.db import transaction

import random

from seattlegeni.common.exceptions import *

from seattlegeni.common.util import log

from seattlegeni.common.util.decorators import log_function_call
from seattlegeni.common.util.decorators import log_function_call_and_only_first_argument

from seattlegeni.common.util.assertions import *

from seattlegeni.website.control.models import Donation
from seattlegeni.website.control.models import GeniUser
from seattlegeni.website.control.models import Node
from seattlegeni.website.control.models import Vessel
from seattlegeni.website.control.models import VesselPort
from seattlegeni.website.control.models import VesselUserAccessMap





# The number of vessel credits each user gets regardless of donations.
FREE_VESSEL_CREDITS_PER_USER = 10

# A user gets 10 vessel credits for every donation they make.
VESSEL_CREDITS_FOR_DONATIONS_MULTIPLIER = 10

# Port from this range will be randomly selected as the usable_vessel_port for
# new users. Remember that range(x, y) is x inclusive, y exclusive. 
ALLOWED_USER_PORTS = range(63100, 63180)

# Number of ascii characters in generated API keys.
API_KEY_LENGTH = 32

# This must be a datetime.timedelta object.
DEFAULT_VESSEL_EXPIRATION_TIMEDELTA = timedelta(hours=4)

# When calls to get_available_*_vessels() are made, we try to return more
# vessels than were requested so that there will be extras in case some
# can't be acquired. The number we try to return is the number requested times
# the multiplier plus the adder. This gives the chance for half of the nodes
# to be unavailable but the adder makes sure small numbers of requested
# vessels (e.g. 1) won't fail due to really bad luck with the returned vessels.
GET_AVAILABLE_VESSELS_MULTIPLIER = 2
GET_AVAILABLE_VESSELS_ADDER = 10

# The maximum number of lists of same-subnet vessels to return from a call to
# get_available_lan_vessels_by_subnet(). This is useful because if, for example,
# the user requested one lan vessel, we might return (not to the user) a list that
# includes a list of vessels for every possible subnet covered by active nodes.
# That wouldn't be the end of the world, but it seems a bit excessive if we have
# nodes on thousands of subnets.
GET_AVAILABLE_LAN_VESSELS_MAX_SUBNETS = 10





@log_function_call
def init_maindb():
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





@transaction.commit_manually
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
  assert_str(username)
  assert_str(password)
  assert_str(email)
  assert_str(affiliation)
  assert_str(user_pubkey)
  assert_str(user_privkey)
  assert_str(donor_pubkey)
  
  # We're committing manually to make sure the multiple database writes are
  # atomic. (That is, regenerate_api_key() will do a database write.)
  try:
    # Generate a random port for the user's usable vessel port.
    port = random.sample(ALLOWED_USER_PORTS, 1)[0]
  
    # Create the GeniUser (this is actually records in two different tables
    # underneath because of model inheretance, but django hides that from us).
    geniuser = GeniUser(username=username, password='', email=email,
                        affiliation=affiliation, user_pubkey=user_pubkey,
                        user_privkey=user_privkey, donor_pubkey=donor_pubkey,
                        usable_vessel_port=port)
    # Set the password using this function so that it gets hashed by django.
    geniuser.set_password(password)
    geniuser.save()
  
    regenerate_api_key(geniuser)
    
  except:
    transaction.rollback()
    raise
  
  else:
    transaction.commit()

  return geniuser





@log_function_call
def regenerate_api_key(geniuser):
  assert_geniuser(geniuser)
  
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
  assert_str(node_identifier)
  assert_str(last_known_ip)
  assert_int(last_known_port)
  assert_str(last_known_version)
  assert_bool(is_active)
  assert_str(owner_pubkey)
  assert_str(extra_vessel_name)
  
  # Create the Node.
  node = Node(node_identifier=node_identifier, last_known_ip=last_known_ip,
              last_known_port=last_known_port, last_known_version=last_known_version,
              is_active=is_active, owner_pubkey=owner_pubkey,
              extra_vessel_name=extra_vessel_name)
  node.save()

  return node





@log_function_call
def create_donation(node, donor, resource_description_text):
  assert_node(node)
  assert_geniuser(donor)
  assert_str(resource_description_text)
  
  # Create the Donation.
  donation = Donation(node=node, donor=donor,
                      resource_description_text=resource_description_text)
  donation.save()

  return donation





@log_function_call
def create_vessel(node, vesselname):
  assert_node(node)
  assert_str(vesselname)
  
  # Create the Vessel.
  vessel = Vessel(node=node, name=vesselname, acquired_by_user=None,
                  date_acquired=None, date_expires=None, is_dirty=False)
  vessel.save()
  
  return vessel





@transaction.commit_manually
@log_function_call
def set_vessel_ports(vessel, port_list):
  assert_vessel(vessel)
  assert_list(port_list)
  for port in port_list:
    assert_int(port)

  # We're committing manually to make sure the multiple database writes are
  # atomic.
  try:
    # Delete all existing VesselPort records for this vessel.
    VesselPort.objects.filter(vessel=vessel).delete()
    
    # Create a VesselPort record for each port in port_list.
    for port in port_list:
      vesselport = VesselPort(vessel=vessel, port=port)
      vesselport.save()

  except:
    transaction.rollback()
    raise
  
  else:
    transaction.commit()





@log_function_call
def get_users_with_access_to_vessel(vessel):
  assert_vessel(vessel)

  # Let's return it as a list() rather than a django QuerySet.
  # Using list() causes the QuerySet to be converted to a list, which also
  # means the query is executed (no lazy loading).
  return list(VesselUserAccessMap.objects.filter(vessel=vessel))





@log_function_call
def get_vessels_accessible_by_user(geniuser):
  assert_geniuser(geniuser)

  # Let's return it as a list() rather than a django QuerySet.
  # Using list() causes the QuerySet to be converted to a list, which also
  # means the query is executed (no lazy loading).
  return list(VesselUserAccessMap.objects.filter(user=geniuser))





@log_function_call
def add_vessel_access_user(vessel, geniuser):
  assert_vessel(vessel)
  assert_geniuser(geniuser)

  # If the user already has access, don't throw an exception, just consider
  # the request done.
  mapqueryset = VesselUserAccessMap.objects.filter(vessel=vessel, user=geniuser)
  if mapqueryset.count() == 1:
    return
  
  # Create a VesselUserAccessMap record.
  maprecord = VesselUserAccessMap(vessel=vessel, user=geniuser)
  maprecord.save()
  
  
  
  
  
@log_function_call
def remove_vessel_access_user(vessel, geniuser):
  assert_vessel(vessel)
  assert_geniuser(geniuser)

  # Delete any map records for this user/vessel.
  VesselUserAccessMap.objects.filter(vessel=vessel, user=geniuser).delete()





@log_function_call
def get_user(username):
  assert_str(username)
  
  try:
    geniuser = GeniUser.objects.get(username=username)
    
  except django.core.exceptions.ObjectDoesNotExist:
    # Intentionally vague message to prevent a security problem if this ever
    # gets displayed on the frontend (needs to be the same message as the
    # password/apikey authentication failure messages).
    raise DoesNotExistError("No such user.")
    
  except django.core.exceptions.MultipleObjectsReturned:
    raise InternalError("Multiple records returned when looking up a user by username.")

  return geniuser





@log_function_call_and_only_first_argument
def get_user_with_password(username, password):
  assert_str(username)
  assert_str(password)
  
  # Throws a DoesNotExistError if there is no such user.
  geniuser = get_user(username)

  if not check_password(password, geniuser.password):
    # Intentionally vague message to prevent a security problem if this ever
    # gets displayed on the frontend.
    raise DoesNotExistError("No such user.")
  
  return geniuser





@log_function_call_and_only_first_argument
def get_user_with_apikey(username, apikey):
  assert_str(username)
  assert_str(apikey)
  
  # Throws a DoesNotExistError if there is no such user.
  geniuser = get_user(username)

  if not geniuser.apikey == apikey:
    # Intentionally vague message to prevent a security problem if this ever
    # gets displayed on the frontend.
    raise DoesNotExistError("No such user.")
  
  return geniuser





@log_function_call
def get_node_identifier_from_vessel(vessel):
  assert_vessel(vessel)
  
  return vessel.node.node_identifier





@log_function_call
def delete_user_private_key(geniuser):
  """
  <Purpose>
    Delete the user's private user key.
  """
  assert_geniuser(geniuser)
  
  # TODO assert that geniuser is a GeniUser
  geniuser.user_privkey = None
  geniuser.save()





@log_function_call
def get_donations_by_user(geniuser):
  assert_geniuser(geniuser)
  
  # Let's return it as a list() rather than a django QuerySet.
  # Using list() causes the QuerySet to be converted to a list, which also
  # means the query is executed (no lazy loading).
  return list(Donation.objects.filter(donor=geniuser))





@log_function_call
def get_node(node_identifier):
  assert_str(node_identifier)

  try:
    node = Node.objects.get(node_identifier=node_identifier)
    
  except django.core.exceptions.ObjectDoesNotExist:
    raise DoesNotExistError("There is no node with the node identifier: " + str(node_identifier))
    
  except django.core.exceptions.MultipleObjectsReturned:
    raise InternalError("Multiple records returned when looking up a node by node identifier.")
  
  return node




@log_function_call
def get_acquired_vessels(geniuser):
  assert_geniuser(geniuser)
  
  # Let's return it as a list() rather than a django QuerySet.
  # Using list() causes the QuerySet to be converted to a list, which also
  # means the query is executed (no lazy loading).
  queryset = Vessel.objects.filter(acquired_by_user=geniuser)
  # We don't include expired vessels. That is, as far as what the user sees and
  # is considered having acquired, vessels expire immediately when their
  # expiration time arrives.
  queryset = queryset.exclude(date_expires__lte=datetime.now())
  return list(queryset)
  




def _get_queryset_of_all_available_vessels_for_a_port(port):
  
  queryset = Vessel.objects.filter(acquired_by_user=None)
  # No dirty vessels or inactive nodes.
  queryset = queryset.exclude(is_dirty=True)
  queryset = queryset.exclude(node__is_active=False)
  # Make sure we only get vessels with the user's assigned port.
  queryset = queryset.filter(vesselport__port__exact=port)
  # Randomize the vessels returned by the query.
  # Using order_by('?') is the QuerySet way of saying ORDER BY RAND().
  queryset = queryset.order_by('?')
  
  log.debug("There are " + str(queryset.count()) + " available vessels on port " + str(port))

  return queryset





@log_function_call
def get_available_rand_vessels(geniuser, vesselcount):
  assert_geniuser(geniuser)
  assert_int(vesselcount)
  
  # We return more vessels than were asked for. This gives some room for some
  # of the vessels to be inaccessible or already acquired by the time they are
  # attempted to be acquired by the client code.
  returnvesselcount = GET_AVAILABLE_VESSELS_MULTIPLIER * vesselcount + GET_AVAILABLE_VESSELS_ADDER
  
  allvesselsqueryset = _get_queryset_of_all_available_vessels_for_a_port(geniuser.usable_vessel_port)
   
  if allvesselsqueryset.count() < vesselcount:
    message = "Requested " + str(vesselcount) + " rand vessels, but we only have " + str(allvesselsqueryset.count())
    message += " vessels with port " + str(geniuser.usable_vessel_port) + " available." 
    raise UnableToAcquireResourcesError(message)
  
  return list(allvesselsqueryset[:returnvesselcount])





@log_function_call
def get_available_wan_vessels(geniuser, vesselcount):
  assert_geniuser(geniuser)
  assert_int(vesselcount)
  
  # We return more vessels than were asked for. This gives some room for some
  # of the vessels to be inaccessible or already acquired by the time they are
  # attempted to be acquired by the client code.
  returnvesselcount = GET_AVAILABLE_VESSELS_MULTIPLIER * vesselcount + GET_AVAILABLE_VESSELS_ADDER
  
  vessellist = []
  includedsubnets = []
  
  allvesselsqueryset = _get_queryset_of_all_available_vessels_for_a_port(geniuser.usable_vessel_port)
   
  # Note: it would be more efficient to have the sql query return vessels
  # in unique subnets, but we would have to be very careful that the UNIQUE
  # wasn't being applied/interpreted "before" the RAND(). That is, we would
  # have to be careful that we weren't always getting the same node for a given
  # subnet. So, instead of worrying about the sql for that which wouldn't
  # be intuitive to do with the django ORM, let's just do that part manually.
  
  for possiblevessel in allvesselsqueryset:
    
    subnet = possiblevessel.node.last_known_ip.rpartition('.')[0]
    if not subnet:
      log.error("The vessel " + str(possiblevessel) + " has an invalid last_known_ip")
      continue
    
    # For efficiency, includedsubnets should be a constant time lookup type.
    if subnet in includedsubnets:
      continue
    
    includedsubnets.append(subnet)
    vessellist.append(possiblevessel)
    
    if len(vessellist) == returnvesselcount:
      break 

  if len(vessellist) < vesselcount:
    message = "Requested " + str(vesselcount) + " wan vessels, but we only have vessels with port "
    message += str(geniuser.usable_vessel_port) + " available on " + str(len(includedsubnets)) + " subnets." 
    raise UnableToAcquireResourcesError(message)
  
  return vessellist





@log_function_call
def get_available_lan_vessels_by_subnet(geniuser, vesselcount):
  assert_geniuser(geniuser)
  assert_int(vesselcount)
  
  # Get a list of subnets that have at least vesselcount active nodes in the subnet.
  # This doesn't guarantee that there are available vessels for this user on
  # those nodes, but it's a start. We'll narrow it down further after we get
  # the list of possible subnets.
  # Note: This is not compatible with sqlite. It may only work with mysql.
  subnetsql = """SELECT COUNT(*) AS lansize,
                        SUBSTRING_INDEX(last_known_ip, '.', 3) AS subnet
                 FROM control_node
                 WHERE is_active = TRUE
                 GROUP BY subnet
                 HAVING lansize >= %s
                 ORDER BY RAND()""" % (vesselcount)
  
  cursor = django.db.connection.cursor()
  cursor.execute(subnetsql)
  subnetlist = cursor.fetchall()
  
  if len(subnetlist) == 0:
    raise UnableToAcquireResourcesError("No subnets exist with at least " + str(vesselcount) + " active nodes")
  
  subnets_vessels_list = []
  
  allvesselsqueryset = _get_queryset_of_all_available_vessels_for_a_port(geniuser.usable_vessel_port)
  
  for subnetrow in subnetlist:
    (lansize, subnet) = subnetrow
    lanvesselsqueryset = allvesselsqueryset.filter(node__last_known_ip__startswith=subnet + '.')
    
    if lanvesselsqueryset.count() >= vesselcount:
      # We don't worry about too many vessels being in this list, as it will be 255 at most.
      subnets_vessels_list.append(list(lanvesselsqueryset))

    if len(subnets_vessels_list) >= GET_AVAILABLE_LAN_VESSELS_MAX_SUBNETS:
      break

  if len(subnets_vessels_list) == 0:
    message = "No subnets exist with at least " + str(vesselcount)
    message += " active nodes that have a vessel available on port " + str(geniuser.usable_vessel_port)
    raise UnableToAcquireResourcesError(message)
  
  return subnets_vessels_list





@log_function_call
def get_user_free_vessel_credits(geniuser):
  assert_geniuser(geniuser)

  return FREE_VESSEL_CREDITS_PER_USER





@log_function_call
def get_user_vessel_credits_from_donations(geniuser):
  assert_geniuser(geniuser)

  return len(get_donations_by_user(geniuser)) * VESSEL_CREDITS_FOR_DONATIONS_MULTIPLIER
  




@log_function_call
def get_user_total_vessel_credits(geniuser):

  return get_user_free_vessel_credits(geniuser) + get_user_vessel_credits_from_donations(geniuser) 
  




@log_function_call
def require_user_can_acquire_resources(geniuser, requested_vessel_count):
  """
  <Purpose>
    Ensure the user is allowed to acquire these resources. For now, only
    checks that a user has enough vessel credits for what they have requested.
    In the future, it could also check if the user was "banned".
    This isn't named assert_* because it doesn't raise an AssertionError
    when the user isn't allowed acquire resources.
  <Arguments>
    geniuser
    requested_vessel_count
  <Exceptions>
    InsufficientUserResourcesError
      If the user doesn't have enough vessel credits to satisfy the number
      of vessels the have requested.
  <Side Effects>
    None
  <Returns>
    None
  """
  assert_geniuser(geniuser)
  assert_int(requested_vessel_count)
  
  # This isn't in the assertions module because it is all database-related
  # information. I wanted to avoid making the assertions module dependent
  # on maindb. If it's confusing, the name of this method can be changed.
  
  # This can be made faster. When necessary, add a get_acquired_vessels_count() function.
  acquired_vessel_count = len(get_acquired_vessels(geniuser))
  
  max_allowed_vessels = get_user_total_vessel_credits(geniuser)
  
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
  assert_geniuser(geniuser)
  assert_vessel(vessel)
  
  # We aren't caching any information with the user record about how many
  # resources have been acquired, so the only thing we need to do is make the
  # vessel as having been acquired by this user.
  vessel.acquired_by_user = geniuser
  vessel.date_acquired = datetime.now() + DEFAULT_VESSEL_EXPIRATION_TIMEDELTA
  vessel.save()





@log_function_call
def record_released_vessel(vessel):
  """
  <Purpose>
    Performs all database operations necessary to record the fact that a vessel
    was released.
  """
  assert_vessel(vessel)
  
  # We aren't caching any information with the user record about how many
  # resources have been acquired, so the only thing we need to do is make the
  # vessel as having not having been acquired by any user.
  vessel.acquired_by_user = None
  vessel.is_dirty = True
  vessel.save()





@log_function_call
def mark_expired_vessels_as_dirty():
  """
  <Returns>
    The number of expired vessels marked as dirty.
  """
  
  # We want to mark as dirty all vessels past their expiration date that are
  # currently acquired by users.
  queryset = Vessel.objects.filter(date_expires__lte=datetime.now())
  queryset = queryset.exclude(acquired_by_user=None)
  
  count = queryset.count()
  
  queryset.update(is_dirty=True, acquired_by_user=None)

  # Return the number of vessels that just expired.
  return count





@log_function_call
def mark_vessel_as_clean(vessel):
  assert_vessel(vessel)
  
  vessel.is_dirty = False
  vessel.save()





@log_function_call
def get_vessels_needing_cleanup():
  queryset = Vessel.objects.filter(is_dirty=True)
  queryset = queryset.filter(node__is_active=True)
  return list(queryset)






@log_function_call
def does_vessel_need_cleanup(vessel):
  assert_vessel(vessel)
  
  # Re-query the database in case this vessel has changed or been deleted.
  try:
    vessel = Vessel.objects.get(id=vessel.id)

  except django.core.exceptions.ObjectDoesNotExist:
    # The vessel was deleted.
    return (False, "The vessel no longer exists")
  
  if vessel.node.is_active is False:
    return (False, "The node the vessel is on is not active")
  
  if vessel.is_dirty is False:
    return (False, "The vessel is not dirty")
  
  return (True, "")
  




@log_function_call
def delete_all_vessels_of_node(node):
  """
  Intended to be used when a node state transition script combines all vessels
  to move the node back to the canonical state.
  """
  assert_node(node)
  
  Vessel.objects.filter(node=node).delete()


