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

from seattlegeni.website import settings

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
    
    If you're using the maindb in long-running non-website code, you should
    either call this function on a regular basis (even if new database
    connections haven't been made) or copy the bit of code here that does the
    django.db.reset_queries() call to your own code. Otherwise, your memory
    usage will grow due to query logging when DEBUG is True.
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
  if settings.DATABASE_ENGINE is "mysql":
    django.db.connection.cursor().execute('set transaction isolation level read committed')
  else:
    log.error("init_maindb() called when not using mysql. This is only OK when developing.")

  # We shouldn't be running in production with settings.DEBUG = True. Just in
  # case, though, tell django to reset its list of saved queries. On the
  # website, init_maindb() will get called with each web request so we'll be
  # resetting the queries at the beginning of each request.
  # See http://docs.djangoproject.com/en/dev/faq/models/#why-is-django-leaking-memory
  # for more info.
  if settings.DEBUG:
    log.debug("Resetting django query log because settings.DEBUG is True.")
    log.error("Reminder: settings.DEBUG is True. Don't run in production like this!")
    django.db.reset_queries()



@transaction.commit_manually
@log_function_call_and_only_first_argument
def create_user(username, password, email, affiliation, user_pubkey, user_privkey, donor_pubkey):
  """
  <Purpose>
    Create a new seattlegeni user in the database. This user will be able to
    login to website, use the seattlegeni xmlrpc api, acquire vessels, etc.
    
    A 'user' lock should be held on the specified username before calling this
    function. The code calling this function should have already checked to
    see whether a user by this username exists (and did so while holding the
    lock on that username).
  
    The code calling this function is responsible for first storing the
    corresponding private key of donor_pubkey in the keydb. In the case of the
    website calling this function, the website will make a call to the backend
    to request a new key and that will take care of storing the donor private
    key in the keydb.
    
  <Arguments>
    username
      The username of the user to be created.
    password
      The user's password.
    email
      The user's email address.
    affiliation
      The affiliation text provided by the user.
    user_pubkey
      A string of the user's public key.
    user_privkey
      A string of the user's private key or None. This would be None if the
      user has provided their own public key rather than had us generate
      a keypair for them.
    donor_pubkey
      A string of the user's donor key. This is a key the user never sees (and
      probably never knows exists).  
      
    <Exceptions>
      None
      
    <Side Effects>
      Creates a user record in the django user table and a user record in the
      seattlegeni geniuser table, the two of which have a one-to-one mapping.
      Does not change the database if creation of either record fails.
      
    <Returns>
      A GeniUser object of the newly created user.
  """
  assert_str(username)
  assert_str(password)
  assert_str(email)
  assert_str(affiliation)
  assert_str(user_pubkey)
  assert_str_or_none(user_privkey)
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
  """
  <Purpose>
    Set a new, randomly generated api key for a user.
  <Arguments>
    geniuser
      The GeniUser object of the user whose api key is to be regenerated.
  <Exceptions>
    None
  <Side Effects>
    Updates the database as well as the geniuser object passed in with a new,
    randomly-generated api key.
  <Returns>
    None
  """
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
  <Purpose>
    Create a new node record in the database. A node lock should be held before
    calling this function.
  <Arguments>
    node_identifier
      The identifier of the node to be created (there must be any existing
      nodes with this identifier).
    last_known_ip
      The last known ip address (a string) that this node's nodemanager was
      running on.
    last_known_port
      The last known port (an int) that this node's nodemanager was running on.
    last_known_version
      The last known version of Seattle (a string) that this node was running.
    is_active
      Whether this node is considered to be up.
    owner_pubkey
      The owner public key (a string) that SeattleGeni uses for this node. The
      corresponding private key must be stored in the keydb.
    extra_vessel_name
      The name of the 'extra vessel' on this node (a string).
  <Exceptions>
    None
  <Side Effects>
    A node record is created in the database.
  <Returns>
    The Node object of the created node.
  """
  assert_str(node_identifier)
  assert_str(last_known_ip)
  assert_int(last_known_port)
  assert_str(last_known_version)
  assert_bool(is_active)
  assert_str(owner_pubkey)
  assert_str(extra_vessel_name)
  
  # Make sure there is not already a node with this node identifier.
  try:
    get_node(node_identifier)
    raise ProgrammerError("A node with this identifier already exists: " + node_identifier)
  except DoesNotExistError:
    pass
  
  # Create the Node.
  node = Node(node_identifier=node_identifier, last_known_ip=last_known_ip,
              last_known_port=last_known_port, last_known_version=last_known_version,
              is_active=is_active, owner_pubkey=owner_pubkey,
              extra_vessel_name=extra_vessel_name)
  node.save()

  return node





@log_function_call
def create_donation(node, donor, resource_description_text):
  """
  <Purpose>
    Create a new donation record in the database. A node lock and a user lock
    should be held before calling this function.
  <Arguments>
    node
      The Node object of the node that the donation was made from.
    donor
      The GeniUser object of the user that made the donation.
    resource_description_text
      A description of the donated resources (in the format of other resource
      descriptions used in Seattle).
  <Exceptions>
    None
  <Side Effects>
    A donation record is created in the database.
  <Returns>
    The Donation object of the created donation.
  """
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
  """
  <Purpose>
    Create a new vessel record in the database. A node lock should be held
    before calling this function.
  <Arguments>
    node
      The Node object of the node that the vessel exists on.
    vesselname
      The name of the vessel for the vessel record to be created.
  <Exceptions>
    None
  <Side Effects>
    A vessel record is created in the database.
  <Returns>
    The Vessel object of the created vessel.
  """
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
  """
  <Purpose>
    Change the list of ports the database considers associated with a vessel.
    A node lock should be held before calling this function.
  <Arguments>
    vessel
      The Vessel object whose list of ports is to be changed.
    port_list
      The list of port numbers (int's or long's) that are the complete list
      of ports for this vessel.
  <Exceptions>
    None
  <Side Effects>
    The database indicates that the ports in port_list (and only those ports)
    are the ports for the vessel. 
  <Returns>
    None
  """
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
  """
  <Purpose>
    Determine which users have access to a vessel according to the database.
  <Arguments>
    vessel
      The Vessel object whose user access is info is wanted.
  <Exceptions>
    None
  <Side Effects>
    None
  <Returns>
    A list of GeniUser objects of the users who have access to the vessel.
  """
  assert_vessel(vessel)

  user_list = []

  for vmap in VesselUserAccessMap.objects.filter(vessel=vessel):
    user_list.append(vmap.user)

  return user_list





@log_function_call
def get_vessels_accessible_by_user(geniuser):
  """
  <Purpose>
    Determine which vessels the database indicates the user has access to.
  <Arguments>
    geniuser
      The GeniUser object of the user whose vessel access info is wanted.
  <Exceptions>
    None
  <Side Effects>
    None
  <Returns>
    A list of Vessel objects of the vessels the user has access to.
  """
  assert_geniuser(geniuser)
  
  vessel_list = []
  
  for vmap in VesselUserAccessMap.objects.filter(user=geniuser):
    vessel_list.append(vmap.vessel)

  return vessel_list





@log_function_call
def add_vessel_access_user(vessel, geniuser):
  """
  <Purpose>
    Indicate in the database that a user has access to a vessel. A node lock
    and a user lock should be held before calling this function.
  <Arguments>
    vessel
      The Vessel object that the user is being given access to.
    geniuser
      The GeniUser object of the user that being access to the vessel.
  <Exceptions>
    None
  <Side Effects>
    The database indicates that the user has access to the vessel.
  <Returns>
    None
  """
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
  """
  <Purpose>
    Indicate in the database that a user no longer has access to a vessel. A
    node lock and a user lock should be held before calling this function.
  <Arguments>
    vessel
      The Vessel object that the user is having access removed from.
    geniuser
      The GeniUser object of the user that is having access removed.
  <Exceptions>
    None
  <Side Effects>
    The database no longer indicates that the user has access to the vessel.
  <Returns>
    None
  """
  assert_vessel(vessel)
  assert_geniuser(geniuser)

  # Delete any map records for this user/vessel.
  VesselUserAccessMap.objects.filter(vessel=vessel, user=geniuser).delete()





@log_function_call
def _remove_all_user_access_to_vessel(vessel):
  """
  <Purpose>
    Indicate in the database that no user has access to the vessel.
  <Arguments>
    vessel
      The Vessel object to have all user access removed.
  <Exceptions>
    None
  <Side Effects>
    The database no longer indicates that any user has access to the vessel.
  <Returns>
    None
  """
  assert_vessel(vessel)

  # Delete any map records for this user/vessel.
  VesselUserAccessMap.objects.filter(vessel=vessel).delete()





@log_function_call
def get_user(username):
  """
  <Purpose>
    Retrieve the user that a has the given username.
  <Arguments>
    username
      The username of the user to be retrieved.
  <Exceptions>
    DoesNotExistError
      If there is no user with the given username.
  <Side Effects>
    None
  <Returns>
    The GeniUser object of the user.
  """
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
  """
  <Purpose>
    Retrieve the user that a has the given username and password.
  <Arguments>
    username
      The username of the user to be retrieved.
    password
      The password of the user to be retrieved.
  <Exceptions>
    DoesNotExistError
      If there is no user with the given username and password.
  <Side Effects>
    None
  <Returns>
    The GeniUser object of the user.
  """
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
  """
  <Purpose>
    Retrieve the user that a has the given username and apikey.
  <Arguments>
    username
      The username of the user to be retrieved.
    apikey
      The apikey of the user to be retrieved.
  <Exceptions>
    DoesNotExistError
      If there is no user with the given username and apikey.
  <Side Effects>
    None
  <Returns>
    The GeniUser object of the user.
  """
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
def get_donor(donor_pubkey):
  """
  <Purpose>
    Retrieve the user that has the donor_pubkey,
  <Arguments>
    donor_pubkey
      The key that is the user's donor key.
  <Exceptions>
    DoesNotExistError
      If there is no user with the given donor_pubkey.
  <Side Effects>
    None
  <Returns>
    The GeniUser object of the user who is the donor.
  """
  assert_str(donor_pubkey)
  
  try:
    geniuser = GeniUser.objects.get(donor_pubkey=donor_pubkey)
    
  except django.core.exceptions.ObjectDoesNotExist:
    raise DoesNotExistError("No user exists with the specified donor_pubkey.")
    
  except django.core.exceptions.MultipleObjectsReturned:
    raise InternalError("Multiple records returned when looking up a user by donor_pubkey.")

  return geniuser





@log_function_call
def get_donations_from_node(node):
  """
  <Purpose>
    Retrieve the donation records of the donations from a node.
  <Arguments>
    node
      The Node object of the node from which the donations were made.
  <Exceptions>
    None
  <Side Effects>
    None
  <Returns>
    A list of Donation objects.
  """
  assert_node(node)
  
  return list(Donation.objects.filter(node=node))





@log_function_call
def get_node_identifier_from_vessel(vessel):
  """
  <Purpose>
    Determine the node id of the node a vessel is on.
  <Arguments>
    vessel
      The Vessel object of the vessel whose node's nodeid will be retrieved.
  <Exceptions>
    None
  <Side Effects>
    None
  <Returns>
    The node id (a string).
  """
  assert_vessel(vessel)
  
  return vessel.node.node_identifier





@log_function_call
def delete_user_private_key(geniuser):
  """
  <Purpose>
    Delete the user's private user key. A user lock should be held before
    calling this function.
  <Arguments>
    geniuser
      The user whose private key is to be deleted.
  <Exceptions>
    None
  <Side Effects>
    The user's private key has been removed from the database.
  <Returns>
    None
  """
  assert_geniuser(geniuser)
  
  geniuser.user_privkey = None
  geniuser.save()





@log_function_call
def get_donations_by_user(geniuser):
  """
  <Purpose>
    Retrieve a list of all donations made by a user.
  <Arguments>
    geniuser
      The user whose donations are to be retrieved.
  <Exceptions>
    None
  <Side Effects>
    None
  <Returns>
    A list of Donation objects.
  """
  assert_geniuser(geniuser)
  
  # Let's return it as a list() rather than a django QuerySet.
  # Using list() causes the QuerySet to be converted to a list, which also
  # means the query is executed (no lazy loading).
  return list(Donation.objects.filter(donor=geniuser))





@log_function_call
def get_node(node_identifier):
  """
  <Purpose>
    Retrieve a Node object that represents a specific node.
  <Arguments>
    node_identifier
      The identifier of the node to be retrieved.
  <Exceptions>
    DoesNotExistError
      If there is no node in the database with the provided identifier.
  <Side Effects>
    None
  <Returns>
    A Node object.
  """
  assert_str(node_identifier)

  try:
    node = Node.objects.get(node_identifier=node_identifier)
    
  except django.core.exceptions.ObjectDoesNotExist:
    raise DoesNotExistError("There is no node with the node identifier: " + str(node_identifier))
    
  except django.core.exceptions.MultipleObjectsReturned:
    raise InternalError("Multiple records returned when looking up a node by node identifier.")
  
  return node





@log_function_call
def set_node_owner_pubkey(node, ownerkeystring):
  """
  <Purpose>
    Change a node's owner key. A node lock should be held before calling this
    function.
  <Arguments>
    node
      The node object of the node whose owner key is to be modified.
    ownerkeystring
      The public key string to be set as the node's owner key.
  <Exceptions>
    None
  <Side Effects>
    The node's owner key is changed in the database.
  <Returns>
    None
  """
  assert_node(node)
  assert_str(ownerkeystring)
  
  node.owner_pubkey = ownerkeystring
  node.save()





@log_function_call
def get_vessel(node_identifier, vesselname):
  """
  <Purpose>
    Retrieve a Vessel object that represents a specific vessel.
  <Arguments>
    node_identifier
      The identifier of the node that the vessel is on.
    vesselname
      The name of the vessel.
  <Exceptions>
    DoesNotExistError
      If there is no such vessel in the database (including if there is no node
      with the given identifier).
  <Side Effects>
    None
  <Returns>
    A Vessel object.
  """
  assert_str(node_identifier)
  assert_str(vesselname)

  try:
    vessel = Vessel.objects.get(node__node_identifier=node_identifier, name=vesselname)
    
  except django.core.exceptions.ObjectDoesNotExist:
    raise DoesNotExistError("There is no vessel with the node identifier: " + 
                            str(node_identifier) + " and vessel name: " + vesselname)
    
  except django.core.exceptions.MultipleObjectsReturned:
    raise InternalError("Multiple records returned when looking up a vessel by node identifier and vessel name.")
  
  return vessel





@log_function_call
def get_acquired_vessels(geniuser):
  """
  <Purpose>
    Retrieve a list of vessels that are acquired by a user.
  <Arguments>
    geniuser
      The GeniUser object of the user whose acquired vessels are to be
      retrieved.
  <Exceptions>
    None
  <Side Effects>
    None
  <Returns>
    A list of Vessel objects.
  """
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
  
  # Note: This is not compatible with sqlite3. It may only work with mysql.
  if settings.DATABASE_ENGINE is "sqlite3":
    raise InternalError("maindb.get_available_lan_vessels_by_subnet() is not supported when using sqlite3")
  
  # Get a list of subnets that have at least vesselcount active nodes in the subnet.
  # This doesn't guarantee that there are available vessels for this user on
  # those nodes, but it's a start. We'll narrow it down further after we get
  # the list of possible subnets.
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
  """
  <Purpose>
    Determine number of free vessel credits the user gets (that is, vessel
    credits they get from registering an account without having donated any
    resources).
  <Arguments>
    geniuser
      The GeniUser object of the user whose freee vessel credit count is to be
      retrieved.
  <Exceptions>
    None
  <Side Effects>
    None
  <Returns>
    The user's number of free vessel credits.
  """
  assert_geniuser(geniuser)

  return FREE_VESSEL_CREDITS_PER_USER





@log_function_call
def get_user_vessel_credits_from_donations(geniuser):
  """
  <Purpose>
    Determine number of vessel credits the user has earned due to donations.
  <Arguments>
    geniuser
      The GeniUser object of the user whose vessel credits from donations are to
      be retrieved.
  <Exceptions>
    None
  <Side Effects>
    None
  <Returns>
    The user's number of vessel credits from donations.
  """
  assert_geniuser(geniuser)

  return len(get_donations_by_user(geniuser)) * VESSEL_CREDITS_FOR_DONATIONS_MULTIPLIER
  




@log_function_call
def get_user_total_vessel_credits(geniuser):
  """
  <Purpose>
    Determine the total number of vessel credits the user has, regardless of
    the number of vessels that already have acquired. This is the sum of the
    number of free vessel credits for the user and the number of vessel
    credits from donations by the user.
  <Arguments>
    geniuser
      The GeniUser object of the user whose total vessel credit count is to be
      retrieved.
  <Exceptions>
    None
  <Side Effects>
    None
  <Returns>
    The user's total number of vessel credits.
  """
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
  <Arguments>
    geniuser
      The GeniUser object of the user who is acquiring the vessel.
    vessel
      The Vessel object to be marked as acquired by the user.
  <Exceptions>
    None
  <Side Effects>
    The vessel is marked as acquired by geniuser. The user and vessel are
    also added to the database's VesselUserAccessMap table.
  <Returns>
    None
  """
  assert_geniuser(geniuser)
  assert_vessel(vessel)
  
  # We aren't caching any information with the user record about how many
  # resources have been acquired, so the only thing we need to do is make the
  # vessel as having been acquired by this user.
  vessel.acquired_by_user = geniuser
  vessel.date_acquired = datetime.now()
  vessel.date_expires = vessel.date_acquired + DEFAULT_VESSEL_EXPIRATION_TIMEDELTA
  vessel.save()
  
  # Update the database to reflect that this user has access to this vessel.
  add_vessel_access_user(vessel, geniuser)





@log_function_call
def record_released_vessel(vessel):
  """
  <Purpose>
    Performs all database operations necessary to record the fact that a vessel
    was released or expired.
  <Arguments>
    vessel
      The Vessel object to be marked as having been released.
  <Exceptions>
    None
  <Side Effects>
    The vessel is marked as not acquired by any user as well as marked as dirty.
    All records for this vessel in the database's VesselUserAccessMap have been
    removed.
  <Returns>
    None
  """
  assert_vessel(vessel)
  
  # We remove the VesselUserAccessMap records first just in case something
  # fails. That is, we don't want to leave the VesselUserAccessMap records
  # around with the vessel later getting cleaned up and given to another user.
  # Alternatively, we could manually commit a transaction for the
  # record_released_vessel() function that we're in to make sure all or none
  # of it gets done.
  _remove_all_user_access_to_vessel(vessel)
  
  # We aren't caching any information with the user record about how many
  # resources have been acquired, so the only thing we need to do is make the
  # vessel as having not having been acquired by any user.
  vessel.acquired_by_user = None
  vessel.is_dirty = True
  vessel.date_acquired = None
  vessel.date_expires = None
  vessel.save()





# We don't log the function call here so that we don't fill up the backend
# daemon's logs.
def mark_expired_vessels_as_dirty():
  """
  <Purpose>
    Change all vessel records in the database whose acquisitions have expired
    to be marked as dirty in the database (that is, to indicate they need to
    be cleaned up by the backend).
  <Arguments>
    None
  <Exceptions>
    None
  <Side Effects>
    All expired vessels (past expiration and acquired by users) in the database
    are marked as dirty as well as marked as not acquired by users. Additionally,
    all vessel user access map entries for each of these vessels have been
    removed.
  <Returns>
    The number of expired vessels marked as dirty.
  """
  # We want to mark as dirty all vessels past their expiration date that are
  # currently acquired by users.
  queryset = Vessel.objects.filter(date_expires__lte=datetime.now())
  queryset = queryset.exclude(acquired_by_user=None)
  
  vessel_list = list(queryset)
  
  if len(vessel_list) > 0:
    for vessel in vessel_list:
      record_released_vessel(vessel)

  # Return the number of vessels that just expired.
  return len(vessel_list)





@log_function_call
def mark_vessel_as_clean(vessel):
  """
  <Purpose>
    Change the database to indicate that a vessel has been cleaned up by the
    backend.
  <Arguments>
    vessel
      The Vessel object of the vessel to be marked as clean.
  <Exceptions>
    None
  <Side Effects>
    Marks the vessel as clean in the database.
  <Returns>
    None
  """
  assert_vessel(vessel)
  
  vessel.is_dirty = False
  vessel.save()





# We don't log the function call here so that we don't fill up the backend
# daemon's logs.
def get_vessels_needing_cleanup():
  """
  <Purpose>
    Determine which vessels need to be cleaned up by the backend.
  <Arguments>
    None
  <Exceptions>
    None
  <Side Effects>
    None
  <Returns>
    A list of Vessel objects which are the vessels needing to be cleaned up.
  """
  queryset = Vessel.objects.filter(is_dirty=True)
  queryset = queryset.filter(node__is_active=True)
  return list(queryset)






@log_function_call
def does_vessel_need_cleanup(vessel):
  """
  <Purpose>
    Determine whether a given vessel needs to be cleaned up by the backend.
  <Arguments>
    vessel
      The Vessel object that we want to know if it needs to be cleaned up.
  <Exceptions>
    None
  <Side Effects>
    None
  <Returns>
    A tuple (needs_cleanup, reason) where needs_cleanup is a boolean indicating
    whether the vessel needs cleanup and reason is a string that indicates the
    reason cleanup is needed if needs_cleanup is True.
  """
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
  <Purpose>
    Delete from the database all vessel records of a node.
  <Arguments>
    node
      The Node object whose vessel records are to be deleted.
  <Exceptions>
    None
  <Side Effects>
    All vessel records for this node have been removed from the database.
  <Returns>
    None
  """
  assert_node(node)
  
  Vessel.objects.filter(node=node).delete()





def get_active_nodes():
  return list(Node.objects.filter(is_active=True))





def get_vessels_on_node(node):
  return list(node.vessel_set.all())

