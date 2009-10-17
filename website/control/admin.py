"""
<Program Name>
  admin.py

<Started>
  July 31, 2008

<Author>
  Justin Samuel

<Purpose>
  This module provides classes that tell django how to represent the models
  in the admin area of the website.

  See http://docs.djangoproject.com/en/dev/ref/contrib/admin/
"""

from seattlegeni.common.api import maindb

from seattlegeni.website.control.models import Donation
from seattlegeni.website.control.models import GeniUser
from seattlegeni.website.control.models import Node
from seattlegeni.website.control.models import Vessel
from seattlegeni.website.control.models import VesselPort
from seattlegeni.website.control.models import VesselUserAccessMap
from seattlegeni.website.control.models import ActionLogEvent
from seattlegeni.website.control.models import ActionLogVesselDetails

from django.contrib import admin





class GeniUserAdmin(admin.ModelAdmin):
  """Customized admin view of the GeniUser model."""
  list_display = ["username", "affiliation", "email", "free_vessel_credits", 
                  "usable_vessel_port", "date_created", "is_staff",
                  "is_superuser"]
  list_filter = ["free_vessel_credits", "date_created", "is_staff",
                 "is_superuser", "usable_vessel_port"]
  # Don't display the private key in the details form.
  exclude = ['user_privkey']
  search_fields = ["username", "user_pubkey", "donor_pubkey", "email",
                   "affiliation"]
  ordering = ["-date_created"]
  




def partial_node_identifier(node):
  """Used by class NodeAdmin."""
  return node.node_identifier[:16]


def is_ok(node):
  """
  Used by class NodeAdmin. We use this because otherwise the green checkmark
  indicating broken is confusing. So, instead we have the field be the
  "not broken" field where a green checkmark means it's not broken.
  """
  return not node.is_broken
# Set a boolean attribute of the function itself which tells django to use the
# boolean icons to represent this field.
is_ok.boolean = True
# Set an admin_order_field of the function which tells django that what is
# represented by this column in the admin area is a field that can be ordered.
is_ok.admin_order_field = 'is_broken'


def donor(node):
  """
  Display a list of users who made donations from the node (which will always
  be one at the moment).
  """
  donation_list = maindb.get_donations_from_node(node)
  donor_names_list = []
  for donation in donation_list:
    donor_names_list.append(donation.donor.username)
  return ",".join(donor_names_list)
  

class NodeAdmin(admin.ModelAdmin):
  """Customized admin view of the Node model."""
  list_display = [partial_node_identifier, donor, "last_known_ip",
                  "last_known_port", "last_known_version", "is_active", is_ok,
                  "extra_vessel_name", "date_last_contacted", "date_created"]
  list_filter = ["last_known_port", "last_known_version", "is_active",
                 "is_broken", "extra_vessel_name", "date_last_contacted",
                 "date_created"]
  search_fields = ["node_identifier", "last_known_ip", "owner_pubkey"]
  ordering = ["-date_created"]





class DonationAdmin(admin.ModelAdmin):
  """Customized admin view of the Donation model."""
  list_display = ["node", "donor", "date_created"]
  list_filter = ["date_created"]
  search_fields = ["node__node_identifier", "donor__username"]
  ordering = ["-date_created"]





class VesselAdmin(admin.ModelAdmin):
  """Customized admin view of the Vessel model."""
  list_display = ["node", "name", "acquired_by_user", "date_acquired",
                  "date_expires", "is_dirty", "date_created"]
  list_filter = ["date_acquired", "date_expires", "is_dirty", "date_created"]
  search_fields = ["node__node_identifier", "node__last_known_ip", "name",
                   "acquired_by_user__username"]
  ordering = ["-date_acquired"]





class VesselPortAdmin(admin.ModelAdmin):
  """Customized admin view of the VesselPort model."""
  list_display = ["vessel", "port"]
  list_filter = []
  search_fields = ["vessel__node__node_identifier",
                   "vessel__node__last_known_ip", "port"]





class VesselUserAccessMapAdmin(admin.ModelAdmin):
  """Customized admin view of the VesselUserAccessMap model."""
  list_display = ["vessel", "user", "date_created"]
  list_filter = ["date_created"]
  search_fields = ["vessel__node__node_identifier",
                   "vessel__node__last_known_ip", "user__username"]
  ordering = ["-date_created"]





class ActionLogEventAdmin(admin.ModelAdmin):
  """Customized admin view of the ActionLogEvent model."""
  
  list_display = ["function_name", "user", "second_arg", "third_arg",
                  "was_successful", "message", "vessel_count", "date_started",
                  "completion_time"]
  list_filter = ["function_name", "user", "third_arg", "was_successful",
                 "vessel_count", "date_started"]
  search_fields = ["function_name", "user"]
  ordering = ["-date_started"]





class ActionLogVesselDetailsAdmin(admin.ModelAdmin):
  """Customized admin view of the ActionLogVesselDetails model."""
  
  list_display = ["event", "node", "node_address", "node_port", "vessel_name"]
  search_fields = ["node_address"]
  ordering = ["-event"]





# Register/associate each custom admin view defined above with the
# corresponding model defined in seattlegeni.website.control.models
admin.site.register(GeniUser, GeniUserAdmin)
admin.site.register(Node, NodeAdmin)
admin.site.register(Donation, DonationAdmin)
admin.site.register(Vessel, VesselAdmin)
admin.site.register(VesselPort, VesselPortAdmin)
admin.site.register(VesselUserAccessMap, VesselUserAccessMapAdmin)
admin.site.register(ActionLogEvent, ActionLogEventAdmin)
admin.site.register(ActionLogVesselDetails, ActionLogVesselDetailsAdmin)
