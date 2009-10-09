#!/bin/bash

# This script runs all seattlegeni tests. It sends all output to stdout/stderr
# and exits with a non-zero if any tests fail.
#
# Usage: ./run_tests.sh trunkdir

trunkdir=$1

if [ ! -d "$trunkdir" ]; then
  echo "Usage: $0 trunkdir"
  exit 1
fi

# Whether any tests failed.
failure=0

# Deploy to a tmp directory.
tmpdir=`mktemp -d`

python $trunkdir/seattlegeni/deploymentscripts/deploy_seattlegeni.py $trunkdir $tmpdir/deploy
pushd $tmpdir/deploy/seattlegeni

##############################################################################
# Run the website core functionality tests.
##############################################################################
echo "############# Website core functionality tests #############"
pushd website/tests

# We assume each of these tests is a python script that returns a non-zero
# exit code on failure.
for i in *.py; do
  echo "------------ $i ------------"
  python $i
  if [ "$?" != "0" ]; then
    failure=1
  fi
done

popd

##############################################################################
# Run the website frontend tests.
##############################################################################
echo "############# Website frontend tests #############"
pushd website/html/tests

# We assume each of these tests is a python script that returns a non-zero
# exit code on failure.
for i in *.py; do
  echo "------------ $i ------------"
  python $i
  if [ "$?" != "0" ]; then
    failure=1
  fi
done

popd

##############################################################################
# Run the lockserver tests.
##############################################################################
echo "############# Lockserver tests #############"
pushd lockserver/tests

./run_all_tests.sh
if [ "$?" != "0" ]; then
  failure=1
fi

popd

##############################################################################
# Run the transition script tests.
##############################################################################
echo "############# Transition script tests #############"
pushd node_state_transitions/tests

# We assume each of these tests is a python script that returns a non-zero
# exit code on failure. This will also run __init__.py here, but that's fine.
for i in *.py; do
  echo "------------ $i ------------"
  python $i
  if [ "$?" != "0" ]; then
    failure=1
  fi
done

popd

##############################################################################
# Clean up and exit.
##############################################################################
popd
rm -rf $tmpdir

echo "############# All tests completed #############"

if [ "$failure" == "0" ]; then
  echo "All tests passed."
else
  echo "Some tests failed."
fi

exit $failure

