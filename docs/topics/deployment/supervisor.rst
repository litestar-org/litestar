Supervisor (Linux)
==================

``supervisor`` is a process control system for Linux, which allows you to monitor and control
a number of processes on UNIX-like operating systems. It is particularly useful for managing
processes that need to be running continuously, and for monitoring and controlling processes
that are running in the background.

Use When
--------

``supervisor`` is ideal for managing Python web applications that need continuous uptime and robust process control.
It's particularly useful when you need extensive process management, monitoring, log management, and
customized control over the start, stop, and restart of application processes.

For detailed understanding and further information, refer to the official
`Supervisor documentation <http://supervisord.org/introduction.html>`_.

Alternatives
~~~~~~~~~~~~

For different deployment scenarios, consider these alternatives:

- :doc:`Docker <docker>`:
    Ideal for containerized environments, offering isolation and scalability.
- `systemd <https://www.freedesktop.org/wiki/Software/systemd/>`_:
    A system and service manager, integrated into many Linux distributions for managing system processes.

    .. note:: Official documentation coming soon
- :doc:`Manually with an ASGI server <manually-with-asgi-server>`:
    Direct control by running the application with an ASGI server like Uvicorn, Hypercorn, Daphne, etc.

This resource provides comprehensive guidance on installation, configuration, and usage of
``supervisor`` for service management.

.. _conf_file:

Setup
-----

``supervisor`` uses a config file for defining services. You can read more about the config file
in the `Supervisor configuration documentation <http://supervisord.org/configuration.html>`_.

.. code-block:: ini
    :caption: Example supervisor config file

    [program:exampleapp]  # Defines the service name.
    directory=/opt/exampleapp/src  # Specifies the directory where the service should run.
    command=/opt/exampleapp/venv/bin/litestar app.py  # Specifies the command to run the service.
    redirect_stderr=true  # Redirects stderr to stdout.
    stdout_logfile=/var/log/exampleapp.log  # Specifies the log file to write to.
    stdout_logfile_backups=10  # Specifies the number of backups to keep.
    autostart=true  # Specifies that the service should start automatically when ``supervisor`` starts.
    autorestart=true  # Specifies that the service should restart automatically if it exits unexpectedly.

You can place the above config file in ``/etc/supervisor/conf.d/exampleapp.conf``.
After you have created the config file, you will need to reload the ``supervisor`` config to load your new service file.

.. dropdown:: Helpful Commands

    .. code-block:: shell
        :caption: Reload supervisor config

        sudo supervisorctl reread
        sudo supervisorctl update

    .. code-block:: shell
        :caption: Start/Stop/Restart/Status

        sudo supervisorctl start exampleapp
        sudo supervisorctl stop exampleapp
        sudo supervisorctl restart exampleapp
        sudo supervisorctl status exampleapp

    .. code-block:: shell
        :caption: View logs

        sudo supervisorctl tail -f exampleapp

Now you are ready to start your application.

#. Start the service if it's not already running: ``sudo supervisorctl start exampleapp``.
#. Ensure it's operating correctly by checking the output for errors: ``sudo supervisorctl status exampleapp``.
#. Once confirmed, your Litestar application should be accessible (By default at ``http://0.0.0.0:8000``).

After that, you are done! You can now use ``supervisor`` to manage your application.
The following sections were written to provide suggestions for making things easier to manage and they are not required.

Suggestions
-----------

.. tip::

        This follows onto the setup above, but provides some suggestions for making things easier to manage.


Aliases
~~~~~~~

Create an alias file: ``/etc/profile.d/exampleapp.sh``.

This is where the magic happens to let us simply use ``exampleapp start`` instead of
``sudo supervisorctl start exampleapp``.

.. dropdown:: Alias Examples

    .. code-block:: shell
        :caption: Example commands provided by the alias file

        exampleapp start
        exampleapp stop
        exampleapp restart
        exampleapp status
        exampleapp watch

    .. code-block:: shell
        :caption: Example alias file
        :linenos:

        exampleapp() {
          case $1 in
            start)
              echo "Starting exampleapp..."
              sudo supervisorctl start exampleapp
              ;;

            stop)
              echo "Stopping exampleapp..."
              sudo supervisorctl stop exampleapp
              ;;

            restart)
              echo "Restarting exampleapp..."
              sudo supervisorctl restart exampleapp
              ;;

            status)
              echo "Checking status of exampleapp..."
              sudo supervisorctl status exampleapp
              ;;

            watch)
              echo "Tailing logs for exampleapp..."
              sudo supervisorctl tail -f exampleapp
              ;;

            help)
              cat << EOF
              Available options:
                exampleapp start    - Start the exampleapp service
                exampleapp stop     - Stop the exampleapp service
                exampleapp restart  - Restart the exampleapp service
                exampleapp status   - Check the status of the exampleapp service
                exampleapp watch    - Tail the logs for the exampleapp service
              EOF
              ;;

            *)
              echo "Unknown command: $1"
              echo "Use 'exampleapp help' for a list of available commands."
              ;;
          esac
        }

To activate the alias without restarting your session use ``source /etc/profile.d/exampleapp.sh``.
Using the ``watch`` command lets you monitor the realtime output of your application.

Update Script
~~~~~~~~~~~~~

The ``exampleapp`` function can be extended to include an ``update`` command,
facilitating the complete update process of the application:

.. dropdown:: Update Script Example

    .. code-block:: shell
        :caption: Example update command
        :linenos:

        exampleapp() {
          case $1 in
            # ... other cases ... #

            update)
              echo "Updating exampleapp..."

              # Stop the service
              echo " > Stopping service..."
              sudo supervisorctl stop exampleapp

              # Update application files
              echo " > Pulling latest changes from repository..."
              cd /opt/exampleapp
              git fetch --all
              git reset --hard origin/master

              # Update Supervisor configuration and alias
              echo " > Updating Supervisor and shell configurations..."
              sudo ln -sf /opt/exampleapp/server/service.conf /etc/supervisor/conf.d/exampleapp.conf
              sudo ln -sf /opt/exampleapp/server/alias.sh /etc/profile.d/exampleapp.sh
              source /etc/profile.d/exampleapp.sh

              # Update Supervisor to apply new configurations
              echo " > Reloading Supervisor configuration..."
              sudo supervisorctl reread
              sudo supervisorctl update

              # Update Python dependencies using requirements.txt
              # Here you could replace with poetry, pdm, etc., alleviating the need for
              # a requirements.txt file and virtual environment activation.
              source venv/bin/activate
              echo " > Installing updated dependencies..."
              python3 -m pip install -r requirements.txt
              deactivate

              # ... other update processes like docs building, cleanup, etc. ... #

              echo "Update process complete."

              # Prompt to start the service
              read -p "Start the service? (y/n) " -n 1 -r
              echo
              if [[ $REPLY =~ ^[Yy]$ ]]
              then
                  echo " > Starting service..."
                  sudo supervisorctl start exampleapp
              fi
              ;;

            # ... #
          esac
        }

This update process includes the following steps:

#. **Stop the Service:** Safely halts the application before making changes.
#. **Git Operations:** Ensures the latest code is pulled from the repository.
#. **Configuration Symlinking:** Updates ``supervisor`` configuration and shell alias to reflect any changes.
#. **Supervisor Reload:** Applies new configuration settings to ``supervisor`` service.
#. **Dependency Update:** Installs or updates Python dependencies as defined in lockfiles or ``requirements.txt``.
#. **User Prompt:** Offers a choice to immediately start the service after updating.

Execution
~~~~~~~~~

Run the ``exampleapp update`` command to execute this update process.
It streamlines the deployment of new code and configuration changes,
ensuring a smooth and consistent application update cycle.
