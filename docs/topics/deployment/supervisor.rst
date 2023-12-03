Supervisor (linux)
==================

To keep a litestar app running you need to set it as a service. The 2 main ways to do that on Ubuntui is to use systemctl or supervisor. Both use unit files to define the service

Supervisor is an additional package you need to install but i find it much easier to monitor the service than with systemctl

.. code-block:: sh

    sudo apt install supervisor

.. _conf_file:

Conf file
----------

Supervisord uses a config file for defining services http://supervisord.org/configuration.html

.. code-block:: text

    [program:api]
    directory=/opt/api/src
    command=/opt/api/venv/bin/python main.py
    redirect_stderr=true
    stdout_logfile=/var/log/api.log
    stdout_logfile_backups=10
    autostart=true
    autorestart=true


`[program:api]` will be your service name. so `supervisorctl start api`

`directory=/...` the directory where the service must run from

`command=...` the script the service must run. notice the python executable path, this uses the venv's python to run the app.

You will need to reload the supervisor config to load your new service file. do so with:

.. code-block:: sh

    sudo supervisorctl reread
    sudo supervisorctl update


to start/stop the service

.. code-block:: sh

    sudo supervisorctl start api
    sudo supervisorctl stop api


to get the status

.. code-block:: sh

    sudo supervisorctl status api


to watch the output

.. code-block:: sh

    sudo supervisorctl tail -f api


Start the service if its not started. make sure its running. check the output to make sure there aren't any errors. and if all that went according to plan your litestar application should be accessible on
http://yyy.yyy.yyy.yyy:80


Alias for easy control
=========================================

This follows onto the Supervisor setup.

To make things easier to handle the service, here's an alias to use that will make things much easier for you. this introduces some commands like:

.. code-block:: sh

    api start
    api stop
    api restart
    api status
    api watch


Create an alias file `/etc/profile.d/api.sh` this is where the magic happens to let us simply use `api start` instead of `sudo supervisorctl start api` (all that extra typing.. urrgghhh). Adding it to `/etc/profile.d/` makes the alias available for all users on that system. They would still however need to pass sudo for these commands.

.. code-block:: sh

    api() {
      case $1 in
        start)
          echo "Starting"
          sudo supervisorctl start api || true
          ;;
        stop)
          echo "Stopping"
          sudo supervisorctl stop api || true
          ;;
        restart)
          echo "Stopping"
          sudo supervisorctl stop api || true
          sleep 2
          echo "Starting"
          sudo supervisorctl start api || true
          ;;
        status)
          echo "Status"
          sudo supervisorctl status api || true
          ;;
        watch)
          sudo supervisorctl tail -f api
          ;;

        help)
          echo "Available options:"
          echo "  api start"
          echo "  api stop"
          echo "  api restart"
          echo "  api status"
          echo "  api watch"
          ;;

        *)
          cd /opt/api
        ;;
      esac
    }

To activate the alias without restarting your session use `source /etc/profile.d/api.sh`.

Using the `watch` command lets you monitor the realtime output of your application.


Updating your application
--------------------------

A cool tip that the whole alias brings to the table is that if you include your supervisor conf file and the alias in your code base, you can do something like this for for updating your entire application.

.. code-block:: sh

    api() {
      case $1 in
        # ... #
        update)
          echo " > Stopping"
          sudo supervisorctl stop api || true

          echo " > Updating files"
          cd /opt/api
          git reset --hard origin/master
          git pull origin master

          sleep 2

          echo " > Linking supervisord service file"
          sudo ln -sf /opt/api/server/service.conf /etc/supervisor/conf.d/api.conf
          echo " > Linking service alias"
          sudo ln -sf /opt/api/server/alias.sh /etc/profile.d/api.sh
          source /etc/profile.d/api.sh

          sleep 2

          echo " > Updating supervisord services"
          sudo supervisorctl reread
          sudo supervisorctl update

          sleep 2

          source venv/bin/activate
          echo " > Updating dependencies"
          pip install -U -r requirements.txt

          echo "------------------------"
          echo "Done"

          read -p "Start the service? (y/n) " -n 1 -r
          echo    # (optional) move to a new line
          if [[ $REPLY =~ ^[Yy]$ ]]
          then
              echo "Starting"
              sudo supervisorctl start api || true
          fi
          ;;

You can sym link both the alias file and the conf file into their respective locations and load them up after a git pull.
