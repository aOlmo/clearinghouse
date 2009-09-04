"""
Provides information about the data in the database. This is for generating
reports, not for any core functionality of seattlegeni.

Some of the functions in the module are very database intensive. They could
be done more efficiently, but where possible this module tries to use the
maindb api so that summarized information matches how seattlegeni actually
sees things.
"""

from seattlegeni.common.api import maindb

from seattlegeni.website.control.models import GeniUser

from seattlegeni.common.util import log






def get_vessel_acquisition_counts_by_user():

  # Set the log level high enough so that we don't produce a bunch of logging
  # output due to the logging decorators.
  initial_log_level = log.loglevel
  log.set_log_level(log.LOG_LEVEL_INFO)
  
  vessel_acquisition_dict = {}
  
  for user in GeniUser.objects.all():
    acquired_vessels = maindb.get_acquired_vessels(user)
    if len(acquired_vessels) > 0:
      vessel_acquisition_dict[user.username] = len(acquired_vessels)
      
  # Restore the original log level.
  log.set_log_level(initial_log_level)
      
  return vessel_acquisition_dict





def get_donation_counts_by_user():
  
  # Set the log level high enough so that we don't produce a bunch of logging
  # output due to the logging decorators.
  initial_log_level = log.loglevel
  log.set_log_level(log.LOG_LEVEL_INFO)
  
  donation_dict = {}
  
  for user in GeniUser.objects.all():
    active_donation_count = len(maindb.get_donations_by_user(user))
    inactive_donation_count = len(maindb.get_donations_by_user(user, include_inactive_and_broken=True)) - active_donation_count
    if active_donation_count > 0 or inactive_donation_count > 0:
      donation_dict[user.username] = (active_donation_count, inactive_donation_count)
      
  # Restore the original log level.
  log.set_log_level(initial_log_level)
      
  return donation_dict





def get_available_vessel_counts_by_port():

  # Set the log level high enough so that we don't produce a bunch of logging
  # output due to the logging decorators.
  initial_log_level = log.loglevel
  log.set_log_level(log.LOG_LEVEL_INFO)

  available_vessels_dict = {}
  
  for port in maindb.ALLOWED_USER_PORTS:
    available_vessels_dict[port] = {}
    available_vessels_dict[port]["all"] = maindb._get_queryset_of_all_available_vessels_for_a_port_include_nat_nodes(port).count()
    available_vessels_dict[port]["no_nat"] = maindb._get_queryset_of_all_available_vessels_for_a_port_exclude_nat_nodes(port).count()
    available_vessels_dict[port]["only_nat"] = maindb._get_queryset_of_all_available_vessels_for_a_port_only_nat_nodes(port).count()
  
  # Restore the original log level.
  log.set_log_level(initial_log_level)
  
  return available_vessels_dict
  
