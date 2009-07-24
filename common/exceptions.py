"""
<Program>
  exceptions.py

<Started>
  6 July 2009

<Author>
  Justin Samuel
  
<Purpose>
  All exceptions used outside of a single module in seattlegeni are defined
  in this file. All seattlegeni modules should import all exceptions in this
  file. That is, the following code should be at the top of all seattlegeni
  modules:
  
  from seattlegeni.common.exceptions import *
  
  This ensures that we don't end up ever having an exception named in a
  try/catch block that isn't actually defined in that modules namespace.
  
  In general, no code in seattlegeni should knowingly let built-in
  python exceptions escape from the place where the exception occurs.
  Instead, it should be caught and, if it can't be dealt with, re-raised as
  one of the exceptions in this module (with the details of the original
  exception in the message). Generally this will be either raising the
  exception as a ProgrammerError or an InternalError. That is, if it's
  something we can't recover from, it's usually either bad code or something
  broken/a service down.
"""

# TODO: allow construction of the exceptions and passing them another exception as
# an argument, where the details of that other exception will also be printed
# when the new exception's details are.

class SeattleGeniError(Exception):
  """
  <Purpose>
    All other custom exceptions of seattlegeni inherit from this.
  """



class UserInputError(SeattleGeniError):
  """
  Indicates that some of the user input is invalid. This could be due
  trying to register a username that is taken, providing an invalid
  key, etc.
  """



class ProgrammerError(SeattleGeniError):
  """
  Indicates that a programmer is using something incorrectly. Rather than
  extend this class for many different cases, this error should be raised
  with a message that clearly explains what the programmer did wrong
  (for example, they passed an argument of the wrong type into a function).
  """



class InternalError(SeattleGeniError):
  """
  Indicates that some part of the geni system failed. E.g., a communication
  problem with the lockserver, backend, or database. Can also indicate
  the database is in a bad state. The text of the raised exception should
  clearly describe the problems and all related details.
  """



class InvalidUserError(SeattleGeniError):
  """
  Indicates that a specified user does not exist.
  """



class UsernameAlreadyExistsError(SeattleGeniError):
  """
  Indicates that registration of a username was attempted but that there
  is already a user with this username.
  """
  
  
  
class UnableToAcquireResourcesError(SeattleGeniError):
  """
  Indicates that SeattleGeni was unable to satisfy a request for resource
  acquisition.
  """

  
  
class InsufficientUserResourcesError(SeattleGeniError):
  """
  Indicates that a user requested more resources than they are allowed to have.
  """


