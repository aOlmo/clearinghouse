"""
Populates the database with some sample data.
"""

from seattlegeni.common.api import maindb

# Decrease the amount of logging output.
from seattlegeni.common.util import log
log.loglevel = log.LOG_LEVEL_ERROR



# Delete everything from the database. To be safe, this isn't enabled by
# default. You should probably use ./managepy --flush, instead.
#Donation.objects.all().delete()
#GeniUser.objects.all().delete()
#Node.objects.all().delete()
#Vessel.objects.all().delete()
#VesselPort.objects.all().delete()
#VesselUserAccessMap.objects.all().delete()


# Create GeniUser records
user_list = []
for i in range(10):
  username = 'user' + str(i)
  user = maindb.create_user(username, 'mypassword', 'myemail', 'myaff', 'mypubkey', 'myprivkey', 'mydonorpubkey')
  user.save()
  user_list.append(user)

# Create Node records
node_list = []
for i in range(100):
  node_identifier = 'node' + str(i)
  extra_vessel_name = 'v2'
  node = maindb.create_node(node_identifier, '127.0.0.1', 1234, '0.1a', True, 'the owner pubkey', extra_vessel_name)
  node.save()
  node_list.append(node)


# Create Donation records
donation_list = []
for i in range(100):
  node = node_list[i]
  donor = user_list[i % len(user_list)]
  donation = maindb.create_donation(node, donor, 'some resource description text')
  donation.save()
  donation_list.append(donation)


# Create Vessel records
vessel_list = []
for i in range(100):
  node = node_list[i]
  name = 'v' + str(i)
  vessel = maindb.create_vessel(node, name)
  vessel.save()
  vessel_list.append(vessel)
  # Set the vessel ports.
  maindb.set_vessel_ports(vessel, range(1000, 1010))
  

