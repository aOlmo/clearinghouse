"""
<Program>
  check_active_db_nodes.py

<Started>
  16 August 2009

<Author>
  Justin Samuel

<Purpose>
  This script runs an infinite loop of checks over all of the active nodes in
  the database. It will result in inactive and broken nodes or vessels needing
  release/cleanup being marked as such in the database.
  
  This is the only place in seattlegeni where we ensure that nodes that have
  gone offline and no longer advertise get marked as inactive in the database.
  
  This script will not directly result in any state-changing nodemanager
  communication (only node information querying). It uses the check_node()
  function in the seattlegeni.common.util.nodestatus module, which means
  that only the database will be directly modified.
"""

import os
import time
import traceback

from seattlegeni.common.api import lockserver
from seattlegeni.common.api import maindb

from seattlegeni.common.util import log

from seattlegeni.common.exceptions import *

from seattlegeni.common.util import nodestatus





# The number of seconds to sleep at the end of each iteration through all
# active nodes in the database. This only applies when running this as a
# script.
SLEEP_SECONDS_BETWEEN_RUNS = 60

# If True, no database changes will be made marking nodes as inactive or broken
# when this is run as a script. This is independent of the readonly argument
# that can be passed to check_node() if check_node() is called directly from
# another module.
READONLY = False





def main():
  """
  This will run an infinite loop of checks over all of the active nodes in the
  database.
  """
  
  lockserver_handle = lockserver.create_lockserver_handle()

  # Always try to release the lockserver handle, though it's probably not
  # very useful in this case.
  try:
    
    while True:
      
      active_nodes = maindb.get_active_nodes()
      log.info("Starting check of " + str(len(active_nodes)) + " active nodes.")
    
      checked_node_count = 0
      
      for node in active_nodes:
        
        checked_node_count += 1
        log.info("Checking node " + str(checked_node_count) + ": " + str(node))
        
        nodestatus.check_node(node, readonly=READONLY, lockserver_handle=lockserver_handle)
        
      # Print summary info.
      log.info("Nodes checked: " + str(checked_node_count))
      nodes_with_problems = nodestatus.get_node_problem_info()
      nodes_with_problems_count = len(nodes_with_problems.keys())
      log.info("Nodes without problems: " + str(checked_node_count - nodes_with_problems_count))
      log.info("Nodes with problems: " + str(nodes_with_problems_count))
      
      # Print information about the database changes made.
      log.info("Number of database actions taken:")
      actionstaken = nodestatus.get_actions_taken()
      for actionname in actionstaken:
        log.info("\t" + actionname + ": " + str(len(actionstaken[actionname])) + 
                 " " + str(actionstaken[actionname]))
  
      nodestatus.reset_collected_data()
      
      log.info("Sleeping for " + str(SLEEP_SECONDS_BETWEEN_RUNS) + " seconds.")
      time.sleep(SLEEP_SECONDS_BETWEEN_RUNS)

  except:
    log.critical("Unexpected exception: " + traceback.format_exc())
    # For the moment, let's have this kill the script. It just seems risky to
    # let this continue if there are bugs.
    raise

  finally:
    lockserver.destroy_lockserver_handle(lockserver_handle)
  
  



if __name__ == "__main__":
  try:
    main()
  except KeyboardInterrupt:
    pass
