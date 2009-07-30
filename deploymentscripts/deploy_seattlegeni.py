"""
<Program Name>
  deploy_seattlegeni.py

<Started>
  July 29, 2009

<Author>
  Justin Samuel

<Purpose>
  Deploys all components of seattlegeni. Some things (e.g. database setup,
  config file modification to enter db user/pass info, etc.) still need
  to be done after this is run. See the instructions in:
  seattlegeni/README.txt

<Description>
  The script backs up the target deploy directory if it exists and the user
  wants to proceed. It then deploys all required files to the deploy
  directory the user specified.

<Usage>
  export PYTHONPATH=$PYTHONPATH:/path/to/sv/trunk
  python deploy_seattlegeni.py <path/to/svn/trunk> <dir/to/deploy/to>
  
"""

import glob
import os
import shutil
import subprocess
import sys
import time

try:
  import preparetest
except ImportError:
  print "Error importing preparetest, make sure that it is in your PYTHONPATH"
  print "\te.g.: export PYTHONPATH=$PYTHONPATH:/path/to/svn/trunk"
  sys.exit(0)





def _print_post_deploy_instructions():
  print
  print "Deployed successfully. The file trunk/seattlegeni/README.txt contains the"
  print "rest of the info you'll need to get things running."





def _deploy_seattle_files_to_directory(trunkdir, targetdir):
  """
  Deploys a copy of all seattle files needed to run repy code to a specified
  directory.
  """
  
  print "Deploying seattle and repy library code to " + targetdir
  
  # Copy the repy and mix files needed by various parts of seattlegeni,
  # including ones we don't use but may be required to import repyhelper.
  preparetest.copy_to_target(os.path.join(trunkdir, "repy", "*"), targetdir)
  preparetest.copy_to_target(os.path.join(trunkdir, "nodemanager", "*"), targetdir)
  preparetest.copy_to_target(os.path.join(trunkdir, "portability", "*"), targetdir)
  preparetest.copy_to_target(os.path.join(trunkdir, "seattlelib", "*"), targetdir)

  _process_mix_files_in_directory(trunkdir, targetdir)





#iterate through the .mix files in current folder and run them through the preprocessor
#script_path must specify the name of the preprocessor script
#the working directory must be set to the directory containing the preprocessor script prior to executing this function.
def _process_mix_files_in_directory(trunkdir, directory_with_mix_files):
 
  originaldir = os.getcwd()
  os.chdir(directory_with_mix_files)

  mix_files = glob.glob(os.path.join(directory_with_mix_files, "*.mix"))
 
  # Generate a .py file for each .mix file.
  for file_path in mix_files:
    processed_file_path = (os.path.basename(file_path)).replace(".mix", ".py")
    retval = subprocess.call(["python", "repypp.py", file_path, processed_file_path])
    if retval != 0:
      exit_with_message(1, "Failed converting " + file_path + " to " + processed_file_path)

  os.chdir(originaldir)





def main():
    
  if not len(sys.argv) == 3:
    exit_with_message(2, "Usage: python deploy_seattlegeni.py <path/to/svn/trunk> <dir/to/deploy/to>")
  
  trunkdir = sys.argv[1]
  deployroot = sys.argv[2]
  
  if not os.path.isdir(trunkdir):
    exit_with_message(1, "ERROR: the provided path to the svn trunk does not exist.")

  if not os.path.exists(os.path.join(trunkdir, "seattlegeni")):
    exit_with_message(1, "ERROR: the given svn trunk directory doesn't contains a seattlegeni directory.")

  # Warn the user if the provided deploy directory exists and if it should be replaced.
  # We actually rename rather than remove the old one, just to be paranoid.
  if os.path.isdir(deployroot):
    ans = raw_input("WARNING: directory found at directory to deploy to (" + deployroot + ").  Replace? [y/n]")
    ans = str.lower(ans)
    if not ans == 'y':
      exit_with_message(2, "You chose not to replace the directory.")
    else:
      print
      renameddir = deployroot.rstrip('/').rstrip('\\') + '.' + str(time.time())
      print "Renaming existing directory " + deployroot + " to " + renameddir
      shutil.move(deployroot, renameddir)

  # Create the directory we will deploy to.
  os.mkdir(deployroot)

  # Copy over the seattlegeni files from svn to the deploy directory.
  #seattlegeni_svn = os.path.join(trunkdir, "seattlegeni", "website")
  seattlegeni_svn_dir = os.path.join(trunkdir, "seattlegeni")
  seattlegeni_deploy_dir = os.path.join(deployroot, "seattlegeni")
  print "Copying " + seattlegeni_svn_dir + " to " + seattlegeni_deploy_dir
  shutil.copytree(seattlegeni_svn_dir, seattlegeni_deploy_dir, symlinks=True)
  
  # The backend_daemon.py file uses the nodemanager api, which users repy, so
  # the backend/ directory needs the repy files.
  _deploy_seattle_files_to_directory(trunkdir, os.path.join(seattlegeni_deploy_dir, "backend"))
  # The node state transition scripts use the nodemanager api as well as
  # various other repy modules, so the polling/ directory needs the repy files.
  _deploy_seattle_files_to_directory(trunkdir, os.path.join(seattlegeni_deploy_dir, "polling"))

  _print_post_deploy_instructions()





def exit_with_message(retval, message):
  print message
  print "Exiting."
  sys.exit(retval)





if __name__ == '__main__':
  main()
