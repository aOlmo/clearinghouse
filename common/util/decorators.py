"""
<Program>
  decorators.py

<Started>
  6 July 2009

<Author>
  Justin Samuel

<Purpose>
  These define the decorators used in seattlegeni code. Decorators are something
  we try to avoid using, so they should only be used if absolutely necessary.
  Currently we only use them for logging function calls (such as the public
  api functions).

  The simple_decorator approach here is borrowed from:
  http://wiki.python.org/moin/PythonDecoratorLibrary

  The general idea is that we have one simple_decorator that does magic python
  stuff (_simple_decorator), and we write our actual decorators that are more
  sane and are themselves decorated with the _simple_decorator.
"""


from seattlegeni.common.util import log

from django.http import HttpRequest


def _simple_decorator(decorator):
  """
  This is not for use outside of this module.
  
  This decorator can be used to turn simple functions into well-behaved
  decorators, so long as the decorators are fairly simple. If a decorator
  expects a function and returns a function (no descriptors), and if it doesn't
  modify function attributes or docstring, then it is eligible to use this.
  Simply apply @simple_decorator to your decorator and it will automatically
  preserve the docstring and function attributes of functions to which it is
  applied.
  """
  def new_decorator(f):
    g = decorator(f)
    g.__name__ = f.__name__
    g.__doc__ = f.__doc__
    g.__dict__.update(f.__dict__)
    return g
  # Now a few lines needed to make simple_decorator itself
  # be a well-behaved decorator.
  new_decorator.__name__ = decorator.__name__
  new_decorator.__doc__ = decorator.__doc__
  new_decorator.__dict__.update(decorator.__dict__)
  return new_decorator





@_simple_decorator
def log_function_call(func):
  """
  <Purpose>
    Logs when the function is called, along with the arguments, and logs when
    the function returns, along with the return value. Will also log any
    exception that is raised.
    
    Be careful when using this to log functions that take sensitive values
    (e.g. passwords) as arguments or that return sensitive values (e.g.
    private keys).
  """
  
  # The name "do_logging_func_call" is never seen anywhere but here.
  def do_logging_func_call(*args, **kwargs):
    _log_call_info(func, args, kwargs)
    
    try:
      result = func(*args, **kwargs)
      log.info('Returning from %s: %s' % (func.__name__, str(result)))
      return result
    
    except Exception, e:
      log.info('Exception from %s: %s' % (func.__name__, str(e)))
      raise
    
  return do_logging_func_call





@_simple_decorator
def log_function_call_without_return(func):
  """
  <Purpose>
    Logs when the function is called, along with the arguments, and logs when
    the function returns, but doesn't log the return value. Will also log any
    exception that is raised.
    
    Be careful when using this to log functions that take sensitive values
    (e.g. passwords) as arguments.
  """
  
  # The name "do_logging_func_call" is never seen anywhere but here.
  def do_logging_func_call(*args, **kwargs):
    _log_call_info(func, args, kwargs)
    
    try:
      result = func(*args, **kwargs)
      log.info('Returning from %s: [Not logging return value]' % (func.__name__))
      return result
    
    except Exception, e:
      log.info('Exception from %s: %s' % (func.__name__, str(e)))
      raise
  
  return do_logging_func_call





@_simple_decorator
def log_function_call_without_arguments(func):
  """
  <Purpose>
    Logs when the function is called, without the arguments, and logs when
    the function returns, including the return value. Will also log any
    exception that is raised.
    
    Be careful when using this to log functions that return sensitive values
    (e.g. private keys).
  """
  
  # The name "do_logging_func_call" is never seen anywhere but here.
  def do_logging_func_call(*args, **kwargs):
    log.info('Calling: %s (module %s), args: [Not logging], kwargs: [Not logging].' %
             (func.__name__, func.__module__))
    
    try:
      result = func(*args, **kwargs)
      log.info('Returning from %s: %s' % (func.__name__, str(result)))
      return result
    
    except Exception, e:
      log.info('Exception from %s: %s' % (func.__name__, str(e)))
      raise
  
  return do_logging_func_call





@_simple_decorator
def log_function_call_and_only_first_argument(func):
  """
  <Purpose>
    Logs when the function is called, with only the first, and logs when
    the function returns, including the return value. Will also log any
    exception that is raised.
    
    Be careful when using this to log functions that return sensitive values
    (e.g. private keys).
    
    The reason this decorator exists is that there are a handful of functions
    that take sensitive data as arguments (like passwords) but they are
    not the first argument, and logging the first argument could be useful.
    This could probably be accomplished by making a decorator that itself
    took arguments about which arguments to log, but that crosses well over
    the line of maintainability by people who didn't write the initial code.
  """
  
  # The name "do_logging_func_call" is never seen anywhere but here.
  def do_logging_func_call(*args, **kwargs):
    log.info('Calling: %s (module %s), 1st arg: %s, other args: [Not logging].' % 
             (func.__name__, func.__module__, str(_get_cleaned_args(args)[0])))
    
    try:
      result = func(*args, **kwargs)
      log.info('Returning from %s: %s' % (func.__name__, str(result)))
      return result
    
    except Exception, e:
      log.info('Exception from %s: %s' % (func.__name__, str(e)))
      raise
  
  return do_logging_func_call





def _log_call_info(func, args, kwargs):
  # This is a separate function because I didn't want to repeat it the code in
  # both log_function_call and log_function_call_without_return.
  
  # TODO: clean up this line
  log.info('Calling: %s (module %s), args: %s, kwargs: %s.' %
           (func.__name__, func.__module__, str(_get_cleaned_args(args)), str(_get_cleaned_args(kwargs))))




def _get_cleaned_args(args):
  
  cleanedargslist = []

  for item in args:
    if isinstance(item, HttpRequest):
      cleanedargslist.append("<HttpRequest>")
    else:
      cleanedargslist.append(item)
    
  return tuple(cleanedargslist)
      
      
      
      
      
def _get_cleaned_kwargs(kwargs):
  
  cleanedkwargs = {}

  for key in kwargs:
    if isinstance(kwargs[key], HttpRequest):
      cleanedkwargs[key] = "<HttpRequest>"
    elif key == "password":
      cleanedkwargs[key] = "***"
    else:
      cleanedkwargs[key] = kwargs[key]
    
  return cleanedkwargs
  
