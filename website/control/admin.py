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

from seattlegeni.website.control.models import Donation
from seattlegeni.website.control.models import GeniUser
from seattlegeni.website.control.models import Node
from seattlegeni.website.control.models import Vessel
from seattlegeni.website.control.models import VesselPort
from seattlegeni.website.control.models import VesselUserAccessMap

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
  """Used by class NodeAdmin"""
  return node.node_identifier[:16]



class NodeAdmin(admin.ModelAdmin):
  """Customized admin view of the Node model."""
  list_display = [partial_node_identifier, "last_known_ip", "last_known_port",
                  "last_known_version", "is_active", "is_broken",
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





# Register/associate each custom admin view defined above with the
# corresponding model defined in seattlegeni.website.control.models
admin.site.register(GeniUser, GeniUserAdmin)
admin.site.register(Node, NodeAdmin)
admin.site.register(Donation, DonationAdmin)
admin.site.register(Vessel, VesselAdmin)
admin.site.register(VesselPort, VesselPortAdmin)
admin.site.register(VesselUserAccessMap, VesselUserAccessMapAdmin)

