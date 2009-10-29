#!/usr/bin/env python
"""
This script is used to output single lines of comma-separated data for graphing
statistics related to seattlegeni.

Usage:
  python print_data_point.py node_overview CURRENT_VERSION
  or
  python print_data_point.py node_type
  or
  python print_data_point.py vessels
  or
  python print_data_point.py advertise

  When using the 'node_overview' option, you have to pass an extra argument of
  the current version of seattlegeni. For example:
    python print_data_point.py node_overview 0.1n

All of the usages print out something like this, just one single line:

2009-10-29 14:30,472,3

The above is a date (2009-10-29 14:30), followed by two numbers (472 and 3).
"""

from seattlegeni.website.control.models import Node
from seattlegeni.website.control.models import Vessel

from seattlegeni.common.api import maindb

import datetime
import sys




def main():
  arg_to_func_dict = {"node_overview" : get_node_overview_line, 
                      "node_type": get_node_type_line, 
                      "vessels" : get_vessels_line,
                      "advertise" : get_advertise_line}
    
  if len(sys.argv) < 2 or sys.argv[1] not in arg_to_func_dict:
    print "Usage: print_data_points.py [" + "|".join(arg_to_func_dict.keys()) + "] (possible other args)" 
    sys.exit(1)

  print arg_to_func_dict[sys.argv[1]]()





def _datestr():
  date = datetime.datetime.now()
  return "%d-%02d-%02d %02d:%02d" % (date.year, date.month, date.day,
                                     date.hour, date.minute)





def get_node_overview_line():
  parts = []
  parts.append(_datestr())
  parts.append(str(_active_node_count()))
  parts.append(str(_active_broken_node_count()))
  parts.append(str(_active_old_version_node_count()))
  return ",".join(parts)


def _active_node_count():
  return len(maindb.get_active_nodes())


def _active_broken_node_count():
  return len(maindb.get_active_nodes_include_broken()) - len(maindb.get_active_nodes())


def _active_old_version_node_count():
  currentversion = sys.argv[2]
  queryset = Node.objects.filter(is_active=True, is_broken=False)
  queryset = queryset.exclude(last_known_version=currentversion)
  return queryset.count()





def get_node_type_line():
  parts = []
  parts.append(_datestr())
  parts.append(str(_active_non_nat_node_count()))
  parts.append(str(_active_nat_node_count()))
  return ",".join(parts)


def _active_non_nat_node_count():
  queryset = Node.objects.filter(is_active=True, is_broken=False)
  queryset = queryset.exclude(last_known_ip__startswith=maindb.NAT_STRING_PREFIX)
  return queryset.count()


def _active_nat_node_count():
  queryset = Node.objects.filter(is_active=True, is_broken=False)
  queryset = queryset.filter(last_known_ip__startswith=maindb.NAT_STRING_PREFIX)
  return queryset.count()





def get_vessels_line():
  parts = []
  parts.append(_datestr())
  parts.append(str(_free_vessels()))
  parts.append(str(_acquired_vessels()))
  parts.append(str(_dirty_vessels()))
  return ",".join(parts)


def _free_vessels():
  queryset = Vessel.objects.filter(acquired_by_user=None)
  queryset = queryset.filter(node__is_active=True, node__is_broken=False)
  return queryset.count()


def _acquired_vessels():
  queryset = Vessel.objects.exclude(acquired_by_user=None)
  queryset = queryset.exclude(date_expires__lte=datetime.datetime.now())
  return queryset.count()


def _dirty_vessels():
  return len(maindb.get_vessels_needing_cleanup())





def get_advertise_line():
  parts = []
  parts.append(_datestr())
  parts.append(str(_advertising_donation()))
  parts.append(str(_advertising_canonical()))
  parts.append(str(_advertising_onepercent()))
  return ",".join(parts)


def _advertising_donation():
  # TODO: implement
  return 0


def _advertising_canonical():
  # TODO: implement
  return 0


def _advertising_onepercent():
  # TODO: implement
  return 0




    
if __name__ == "__main__":
  main()
