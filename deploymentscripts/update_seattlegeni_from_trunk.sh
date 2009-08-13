#!/bin/bash

# <Author>
#   Justin Samuel
# <Date Started>
#   August 13, 2009
# <Purpose>
#   This script updates the /home/geni/trunk from svn trunk and then redeploys
#   the seattlegeni files to /home/geni/live. This script is the intended way
#   to update seattlegeni from trunk on the production server. The
#   configuration files will be maintained.
#
#   A backup of the replaced version of seattlegeni will be left in the
#   /home/geni/bak directory.
# 
#   After running this script, you probably want to kill the existing running
#   copy of start_seattlegeni_components.sh and start that script again. This
#   will result in all seattlegeni components running off of the newly deployed
#   version.
# <Usage>
#    update_seattlegeni_from_trunk.sh

cd /home/geni

svn up trunk/

python trunk/seattlegeni/deploymentscripts/deploy_seattlegeni.py trunk/ live/

mv live.bak.* bak/

