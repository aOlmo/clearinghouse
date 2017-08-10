#!/bin/bash
#
# generate_state_keys.sh -- Generate the seven state keys required by the 
#   Seattle Clearinghouse backend. For details please see
#   https://seattle.poly.edu/wiki/SeattleBackend and
#   https://seattle.poly.edu/wiki/ClearinghouseInstallation
#
# Usage:
#   ./generate_state_keys.sh [ TARGET_DIR ]
#
# If the optional TARGET_DIR is omitted, the key files will end up in the current 
# working directory. Typically TARGET_DIR is chosen to be the Clearinhouse's 
# state transition keys dir, /path/to/clearinghouse/node_state_transitions/statekeys
#
# Note: This script assumes that it is copied into a directory containing
#  (1) A RepyV2 runtime environment
#  (2) The generatekeys.py script from Seattle's softwareupdater, see
#      https://github.com/SeattleTestbed/softwareupdater/

# TODO: Error handling, e.g. when the target path doesn't exist.

echo Generating state keys into directory "$1"

for STATE_NAME in acceptdonation movingto_canonical canonical movingto_onepercentmanyevents onepercentmanyevents movingto_twopercent twopercent ; 
  do python generatekeys.py $1/$STATE_NAME 4096 ;
done

echo Done generating state keys!
