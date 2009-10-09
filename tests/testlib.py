# Warning: settings must be imported and the database values modified before
# anything else is imported. Failure to do this first will result in django
# trying to create a test mysql database.
from seattlegeni.website import settings

import os
import tempfile

# Use a database file that actually resides in memory, if possible.
# Note that we do this instead of use TEST_DATABASE_NAME = ":memory:" because
# there seems to be a problem with additional threads accessing the test
# database in memory when using an in-memory sqlite database (":memory:")
# rather than a file-backed one.
if os.path.exists("/dev/shm"):
  sqlite_database_file_dir = "/dev/shm"
else:
  sqlite_database_file_dir = None

# Do not change the DATABASE_ENGINE. We want to be sure that sqlite3 is used
# for tests.
settings.DATABASE_ENGINE = 'sqlite3'
settings.TEST_DATABASE_NAME = tempfile.NamedTemporaryFile(dir=sqlite_database_file_dir, suffix=".sqlite").name
settings.DATABASE_OPTIONS = None

import django.db

import django.test.utils

from seattlegeni.common.util import log





# Turn off most logging to speed up tests run manually. This can be removed
# to see the plentiful debug output.
log.set_log_level(log.LOG_LEVEL_CRITICAL)





def setup_test_environment():
  """
  Called once before running one or more tests. Must be called before calling
  setup_test_db().
  """
  
  django.test.utils.setup_test_environment()



def teardown_test_environment():
  """
  Called once after running one or more tests. That is, this should be called
  before the test script exits.
  """
  
  django.test.utils.teardown_test_environment()



def setup_test_db():
  
  # Creates a new test database and runs syncdb against it.
  django.db.connection.creation.create_test_db()





def teardown_test_db():
  
  # We aren't going to use any database again in this script, so we give django
  # an empty database name to restore as the value of settings.DATABASE_NAME.
  old_database_name = ''
  django.db.connection.creation.destroy_test_db(old_database_name)
  
