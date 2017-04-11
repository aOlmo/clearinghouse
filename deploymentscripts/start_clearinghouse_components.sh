#!/bin/bash
#
# <Program>
#   start_clearinghouse_components.sh
# 
# <Purpose>
#   This script will start the various components of the Clearinghouse in the 
#   correct order (namely, lockserver first, then backend, then the rest). It 
#   will also gracefully restart Apache. This script should be used rather than
#   stopping/starting components individually to ensure that all components use
#   a fresh lockserver after they have been restarted.
#
# <Usage>
#    As root, run:
#      ./start_clearinghouse_components.sh
#    Once started, the processes will not exit until its children have. To kill
#    all components of the clearinghouse (except Apache), send a SIGINT or 
#    SIGTERM to this process.

# The user account hosting and running the clearinghouse Django app
CLEARINGHOUSE_USER=ch

# The directory deployed to by deploymentscripts/deploy_clearinghouse.sh
CLEARINGHOUSE_DIR="/home/ch/deployment/clearinghouse"

# The path to the RepyV2 runtime
REPY_RUNTIME_DIR="$CLEARINGHOUSE_DIR/../seattle"

# PYTHONPATH takes the deployed clearinghouse's parent dir, and the path to 
# the RepyV2 runtime.
export PYTHONPATH="$CLEARINGHOUSE_DIR/..:$REPY_RUNTIME_DIR"

export DJANGO_SETTINGS_MODULE="clearinghouse.website.settings"


# Log output to stdout/stderr to this directory
LOG_DIR="$CLEARINGHOUSE_DIR/logs"

# A sudo command to run processes as the clearinghouse user with the correct 
# environment variables for Django.
SUDO_CMD="sudo -u $CLEARINGHOUSE_USER PYTHONPATH=$PYTHONPATH DJANGO_SETTINGS_MODULE=$DJANGO_SETTINGS_MODULE"

# When run via crontab, the $USER environment variable may not be set.
if [ "$USER" == "" ]; then
  USER=`whoami`
fi

if [ "$USER" != "root" ]; then
  echo "You must run this script as root. Exiting."
  exit 1
fi



# Count the number of other instances of this script already running, besides 
# ours. In the count, ignore our own grep, and also ignore screen instances.
ALREADY_RUNNING_COUNT=`ps -ef | grep start_clearinghouse_components.sh | grep -v grep | grep -v -i screen | grep -v $$ | wc -l`

if [ "$ALREADY_RUNNING_COUNT" != "0" ]; then
  echo "There appears to already be a copy of start_clearinghouse_components.sh running."
  echo "You'll need to kill the other running copy first."
  exit 1
fi



function shutdown() {
  echo "Shutting down Clearinghouse components."
  # Tell kill to kill the process group (so, kill children) by giving a negative process id.
  # Note: "--" means the end of options
  #kill -- -$$
  pkill -P $$
  wait
  exit
}

# Catch the signals from a CTRL-C or "kill this_pid".
trap "shutdown" SIGINT SIGTERM



echo "Starting lockserver."
$SUDO_CMD python $CLEARINGHOUSE_DIR/lockserver/lockserver_daemon.py >>$LOG_DIR/lockserver.log 2>&1 &
sleep 1 # Wait a moment to make sure it has started (lockserver is used by other components).

echo "Starting backend."
# We use dylink to enable affixes.  Dylink only imports from the current directory...
cd $REPY_RUNTIME_DIR && $SUDO_CMD python $CLEARINGHOUSE_DIR/backend/backend_daemon.py >>$LOG_DIR/backend.log 2>&1 &
sleep 1 # Wait a moment to make sure it has started (backend is used by other components).

echo "Gracefully restarting Apache."
apache2ctl graceful

echo "Starting check_active_db_nodes.py."
# We use dylink to enable affixes.  Dylink only imports from the current directory...
cd $REPY_RUNTIME_DIR && $SUDO_CMD python $CLEARINGHOUSE_DIR/polling/check_active_db_nodes.py >>$LOG_DIR/check_active_db_nodes.log 2>&1 &
sleep 1 # We need to wait for each process to start before beginning the next
        # because repyhelper has an issue with concurrent file access. 
        # (OBSOLETE?)



# Note: Don't put a ".py" on the end of the TRANSITION_NAME values.
for TRANSITION_NAME in transition_donation_to_canonical transition_canonical_to_twopercent transition_twopercent_to_twopercent transition_onepercentmanyevents_to_canonical ;
  do echo "Starting transition script $TRANSITION_NAME"
  # We use dylink to enable affixes.  Dylink only imports from the current directory...
  cd $REPY_RUNTIME_DIR && $SUDO_CMD python $CLEARINGHOUSE_DIR/node_state_transitions/$TRANSITION_NAME.py >>$LOG_DIR/$TRANSITION_NAME.log 2>&1 &
  sleep 1
done



echo "All components started. Kill this process (CTRL-C or 'kill $$') to stop all started components (except apache)."



# Wait for all background processes to terminate.
wait
