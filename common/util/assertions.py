"""
<Program>
  assertions.py

<Started>
  29 June 2009

<Author>
  Justin Samuel

<Purpose>
  This is a utility module to provide simple assert_* functions which throw a
  ProgrammerError if the assertion fails. This is mostly intended to provide
  simple type checking of arguments to functions where the programmer calling
  the function should have been sure to provide the correct type of data.
"""

from seattlegeni.common.exceptions import *



def assert_str(value):
  """
  <Purpose>
    Ensure that value is a string (can be str or unicode).
  """
  # Check for basestring which is the superclass of str and unicode.
  if not isinstance(value, basestring):
    raise ProgrammerError("Expected string value, received " + str(type(value)))



def assert_str_or_none(value):
  """
  <Purpose>
    Ensure that value is a string (can be str or unicode) or None.
  """
  # Check for basestring which is the superclass of str and unicode.
  if not isinstance(value, basestring) and value is not None:
    raise ProgrammerError("Expected string value or None, received " + str(type(value)))

