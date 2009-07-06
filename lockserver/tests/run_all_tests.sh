#!/bin/bash

SCRIPT_DIR=`dirname $0`

some_tests_failed=0

# Make sure we are in the tests/ directory, as the tests will be expecting it
# to be the current working directory.
pushd $SCRIPT_DIR >/dev/null

# Run the unit tests.
python run_unit_tests.py

if [ "$?" != "0" ]; then
  some_tests_failed=1
fi

# Run the integration tests.
./run_integration_tests.sh

if [ "$?" != "0" ]; then
  some_tests_failed=1
fi

popd >/dev/null

if [ "$some_tests_failed" == "1" ]; then
  echo "Some tests failed."
  exit 1
fi

