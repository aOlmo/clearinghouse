"""
<Program Name>
  admin.py

<Started>
  July 31, 2008

<Author>
  Justin Samuel

<Purpose>
  This module provides classes that tell django how to represent the models
  in the admin area of the website. If a class has no properties, then
  we're not customizing it and instead just using the django defaults for
  representing the model.

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



class NodeAdmin(admin.ModelAdmin):
  """Customized admin view of the Node model."""
  


class DonationAdmin(admin.ModelAdmin):
  """Customized admin view of the Donation model."""
    


class VesselAdmin(admin.ModelAdmin):
  """Customized admin view of the Vessel model."""



class VesselPortAdmin(admin.ModelAdmin):
  """Customized admin view of the VesselPort model."""



class VesselUserAccessMapAdmin(admin.ModelAdmin):
  """Customized admin view of the VesselUserAccessMap model."""



# Register/associate each custom admin view defined above with the
# corresponding model defined in seattlegeni.website.control.models
admin.site.register(GeniUser, GeniUserAdmin)
admin.site.register(Node, NodeAdmin)
admin.site.register(Donation, DonationAdmin)
admin.site.register(Vessel, VesselAdmin)
admin.site.register(VesselPort, VesselPortAdmin)
admin.site.register(VesselUserAccessMap, VesselUserAccessMapAdmin)

