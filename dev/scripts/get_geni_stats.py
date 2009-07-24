"""
Prints information about the data in the database.

Currently this doesn't give much info, but it would be nice to expand it to
into a more general db querying module or package.
"""

from seattlegeni.common.api import maindb

# Importing all of these at the moment because ultimately it would be good to
# provide stats and interesting info about all of them in ways that might not
# doable directly from the maindb api.
from seattlegeni.website.control.models import Donation
from seattlegeni.website.control.models import GeniUser
from seattlegeni.website.control.models import Node
from seattlegeni.website.control.models import Vessel
from seattlegeni.website.control.models import VesselPort
from seattlegeni.website.control.models import VesselUserAccessMap

# Decrease the amount of logging output.
from seattlegeni.common.util import log
log.loglevel = log.LOG_LEVEL_ERROR


number_of_users_with_acquired_vessels = 0

for user in GeniUser.objects.all():
  acquired_vessels = maindb.get_acquired_vessels(user)
  
  if len(acquired_vessels) > 0:
    number_of_users_with_acquired_vessels += 1
    print str(user) + " has acquired " + str(len(acquired_vessels)) + " vessels."
    print "  " + str(acquired_vessels)

print "There are " +  str(number_of_users_with_acquired_vessels) + " users who have acquired vessels."
