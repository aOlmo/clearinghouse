"""
<Program>
  test_register.py

<Started>
  8/26/2009

<Author>
  Jason Chen
  jchen@cs.washington.edu

<Purpose>
  Tests the registration function of the HTML frontend view.

<Notes>
  We make use of the Django test client, which emulates a webclient and returns what django
  considers the final rendered result (in HTML). This allows us to test purely the view functions.
  Apart from testing the validity/sanity of the view functions, we also mock-out all calls into the
  interface, and return test values to the view functions. This way, we can ensure that the views behave
  properly in normal (and abnormal) interactions with the interface.
"""

# We import the testlib FIRST, as the test db settings 
# need to be set before we import anything else.
from seattlegeni.tests import testlib
from seattlegeni.website.control import interface
from seattlegeni.common.exceptions import *
from seattlegeni.common.util import validations
from seattlegeni.website.control import models
from django.contrib.auth.models import User as DjangoUser

# The django test client emulates a webclient, and returns what django
# considers the final rendered result (in HTML). This allows to test purely the view
# functions. 
from django.test.client import Client

testlib.setup_test_environment()
testlib.setup_test_db()

def mock_register_user(username, password, email, affiliation, pubkey=None):
  
  testuser = DjangoUser()
  testuser.username = "test_user"
  return testuser

def mock_register_user_throws_ValidationError(username, password, email, affiliation, pubkey=None):
  raise ValidationError

def mock_get_logged_in_user(request):
  raise DoesNotExistError

interface.register_user = mock_register_user
interface.get_logged_in_user = mock_get_logged_in_user

c = Client()
good_data = {'username': 'tester', 
             'password1': '12345678',
             'password2': '12345678',  
             'email': 'test@test.com',  
             'affiliation': 'test affil', 
             'gen_upload_choice':'1'}

test_data = {}
###########################################################################
# Test for posting blank form
###########################################################################
response = c.post('/html/register', {'username': '', 
                                     'password1':'', 
                                     'password2':'', 
                                     'email':'', 
                                     'affiliation':'', 
                                     'gen_upload_choice':'1'}, follow=True)

assert("Enter a username" in response.content and
       "Enter a password" in response.content and
       "Verify your password" in response.content and
       "Enter an Affiliation" in response.content and
       "Enter an E-mail Address" in response.content)

###########################################################################
# Test for username too short
###########################################################################
shortuser = ""
for n in range(0, validations.USERNAME_MIN_LENGTH - 1):
  shortuser += "a"

test_data = good_data.copy()
test_data['username'] = shortuser

response = c.post('/html/register', test_data, follow=True)
assert("errorlist" in response.content)

###########################################################################
# Test for username too long
###########################################################################
longuser = ""
for n in range(0, validations.USERNAME_MAX_LENGTH + 1):
  longuser += "a"

test_data = good_data.copy()
test_data['username'] = longuser

response = c.post('/html/register', test_data, follow=True)
assert("errorlist" in response.content)

###########################################################################
# Test for invalid username
###########################################################################
test_data = good_data.copy()
test_data['username'] = 'tester!!!'

response = c.post('/html/register', test_data, follow=True)
assert("errorlist" in response.content)

###########################################################################
# Test for password too short
###########################################################################
test_data = good_data.copy()
test_data['password1'] = '12345'

response = c.post('/html/register', test_data, follow=True)
assert("errorlist" in response.content)

###########################################################################
# Test for non-matching passwords
###########################################################################
test_data = good_data.copy()
test_data['password2'] = '87654321'

response = c.post('/html/register', test_data, follow=True)
assert("errorlist" in response.content)

###########################################################################
# Test for same username and password
###########################################################################
test_data = good_data.copy()
test_data['username'] = 'tester'
test_data['password1'] = 'tester'
test_data['password2'] = 'tester'

response = c.post('/html/register', test_data, follow=True)
assert("p class=\"warning\"" in response.content)

###########################################################################
# Test for affiliation too short
###########################################################################
shortaffil = ""
for n in range(0, validations.AFFILIATION_MIN_LENGTH - 1):
  shortaffil += "a"

test_data = good_data.copy()
test_data['affiliation'] = shortaffil

response = c.post('/html/register', test_data, follow=True)
assert("errorlist" in response.content)

###########################################################################
# Test for affiliation too long
###########################################################################
longaffil = ""
for n in range(0, validations.AFFILIATION_MAX_LENGTH + 1):
  longaffil += "a"

test_data = good_data.copy()
test_data['affiliation'] = longaffil

response = c.post('/html/register', test_data, follow=True)
assert("errorlist" in response.content)

###########################################################################
# Test for invalid e-mail
###########################################################################
test_data = good_data.copy()
test_data['email'] = 'invalid@email'

response = c.post('/html/register', test_data, follow=True)
assert("errorlist" in response.content)

# TODO: Test upload keys

###########################################################################
# If interface throws a ValidationError, even after passing all validation
###########################################################################
interface.register_user = mock_register_user_throws_ValidationError
response = c.post('/html/register', good_data, follow=True)
# TODO: Right now, this just puts up a blank "warning" box
assert("p class=\"warning\"" in response.content)


###########################################################################
# Test normal registration functionality
###########################################################################
interface.register_user = mock_register_user
response = c.post('/html/register', good_data, follow=True)

# check that the view thinks the user has been registered
assert("has been successfully registered" in response.content)

# check that the current page is now the login page
assert(response.template[0].name == "accounts/login.html")
  