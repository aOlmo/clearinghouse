= Deploying and running SeattleGeni =

  * Do initial preparation:

    * Install django. http://docs.djangoproject.com/en/dev/topics/install/

    * Checkout the seattle trunk from svn.
  
    * Deploy all necessary files to a directory of your choice. The directory
      you deploy to should be the name of a directory that does not yet exist.
      For example:
    
      python ./trunk/seattlegeni/deploymentscripts/deploy_seattlegeni.py ./trunk /tmp/deploy
    
    * Change to the seattlegeni directory that is in the directory you deployed
      to. For example:
    
        cd /tmp/deploy/seattlegeni
    
      Note: all future steps/instructions will assume you are in this directory.


  * Start the website:

    * Create a mysql database for seattlegeni (e.g. called `seattlegeni`).
  
    * Edit website/settings.py and specify the name of the seattlegeni
      database, as well as the database username, password, etc.
      Also set a long, random string the value of SECRET_KEY.
    
      Note: using sqlite will not work for everything, but it should work for
      most things if that's more convenient during development.
      
    * TODO: describe what needs to be change din settings.py for a production
      launch.
    
    * Set your environment variables:

        export PYTHONPATH=$PYTHONPATH:/tmp/deploy:/tmp/deploy/seattle
        export DJANGO_SETTINGS_MODULE='seattlegeni.website.settings'
        
      Node: the /tmp/deploy path entry is to make available the two packages
      'seattlegeni' and 'seattle' which the deployment script created in the
      /tmp/deploy directory. The /tmp/deploy/seattle path item is to ensure
      that repyhelper can find repy files in the python path, as the repy files
      were placed in this directory by the deployment script.
    
    * Create the database structure:
  
        python website/manage.py syncdb
      
      You can use the following if you don't want to be prompted about creating
      an administrator account:
    
        python website/manage.py syncdb --noinput
   
    * For development, start the django development webserver:
  
        python website/manage.py runserver
      
      You will now have a local development server running on port 8000.
      
    * For production, setup to run through apache:
    
      TODO: add information on setting up to run through apache
      
      
  * Start the lockserver:
      
    * Set your environment variables:
  
        export PYTHONPATH=$PYTHONPATH:/tmp/deploy

      Note: we don't need to set the DJANGO_SETTINGS_MODULE environment
      variable for the lockserver, but it won't hurt if you do it.
      
    * In a new shell, start the lockserver:
  
        python lockserver/lockserver_daemon.py
      
      
  * Start the backend (including setting up the key database)
      
    * Create a database for the key database (e.g. called `keydb`)
  
    * Make sure that the file keydb/config.py is not readable by the user the
      website is running as (this is only something to worry about for production
      launch, if you are just developing or testing, this is not required.)

    * Edit the file keydb/config.py and set the database information for the key
      database.
    
    * Create the key database structure by executing the contents of the file
      keydb/schema.sql on the new key database you created.
      
        mysql -u[username] -p --database=[keydbname] < keydb/schema.sql

    * Set your environment variables:
  
        export PYTHONPATH=$PYTHONPATH:/tmp/deploy:/tmp/deploy/seattle
        export DJANGO_SETTINGS_MODULE='seattlegeni.website.settings'

    * In a new shell, start the backend_daemon from the backend directory
      (because the repy files need to be in the directory it is run from):
  
        cd backend
        python backend_daemon.py
      
      
  * Start the polling daemons:
  
    * Set your environment variables:
  
        export PYTHONPATH=$PYTHONPATH:/tmp/deploy:/tmp/deploy/seattle
        export DJANGO_SETTINGS_MODULE='seattlegeni.website.settings'
  
    * TODO: add information on running the polling daemons
      

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
    