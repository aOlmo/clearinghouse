= Running SeattleGeni for Local Development =

Note: the following steps will change as soon as we start using other seattle
code to do public key validation by the html frontend, and possibly for other
reasons, too.

  * Install django. http://docs.djangoproject.com/en/dev/topics/install/

  * Checkout the seattle trunk from svn.
  
  * cd trunk/seattlegeni/website
  
  * If desired, edit settings.py to use a mysql database if you don't want to
    develop with sqlite (you'll need to create a mysql database by the name
    you specify, in that case, as it won't be created for you).
    
  * Set your environment variables:
  
      export PYTHONPATH=$PYTHONPATH:/path/to/trunk
      export DJANGO_SETTINGS_MODULE='seattlegeni.website.settings'
    
  * Create the database structure:
  
      python manage.py syncdb
      
    You can use the following if you don't want to be prompted about creating
    an administrator account:
    
      python manage.py syncdb --noinput
   
  * Start the django development webserver:
  
      python manage.py runserver
      
    TODO: if the new backend ends up being port 8000 still, at some point
    these instructions will need to change to have the django webserver
    listen on something other than port 8000.
      
  * In a new shell, start the lockserver:
  
      python lockserver/lockserver_daemon.py
      
You will likely want to populate the database with some data for testing.

------------------------------------------------------------------------------

= SeattleGeni Directory Structure =

The following are the intended contents of the seattlegeni/ directory
in svn:

backend/
    
    This directory is not a package that would be imported in other code.
    This directory contains backend_daemon.py which is the single instance
    of the backend that will be running at any given time.


common/
    
    The package containing anything shared by all seattlegeni components.

  api/  
 
    This package contains a single module for each API that is used
    internally within seattlegeni. These are not intended to be used by code
    outside of seattlegeni. It may seem that, for example, the backend's API
    should live in the backend/ directory rather than here. The argument for
    why this is not the case is that the backend/ directory contains only what
    is needed to actually run the backend. The common/ directory, on the other
    hand, contains modules that may be useful to any component of seattlegeni,
    regardless of which physical system it is on.
  
  util/
  
    This package contains general utility functions.


dev/

    This directory contains modules and scripts intended for assisting testing
    during development. It will probably be removed when real testing code
    is added.


keydb/

    This is the directory where any code relevant to the keydb that is not part
    of the keydb API will go.


lockserver/
  
    This directory is not a package that would be imported in other code.
    This directory contains lockserver_daemon.py which is the single instance
    of the lockserver that will be running at any given time.
    
    
polling/
  
    This directory is not a package that would be imported in other code.
    This directory contains the node state transition scripts, any of their
    supporting modules, and any other scripts or daemons that monitor the
    state of seattlegeni and the nodes it controls.
  
    
website/

    This directory is the root of the website.
    
  control/
  
    This contains core functionality of the website regardless of the frontend
    used to access the website.
    
  html/
  
    This directory contains the code specific to the html frontend of the
    website.
    
  middleware/
  
    This is where we have defined any of our own custom django middleware.
    
  xmlrpc/
  
    This directory contains the code specific to the xmlrpc frontend of the
    website.
    