Supervisor (Linux)
==================

``supervisor`` 是一个 Linux 进程控制系统，允许您在类 UNIX 操作系统上监视和控制多个进程。它特别适用于管理需要连续运行的进程，以及监视和控制在后台运行的进程。

何时使用
--------

``supervisor`` 非常适合管理需要持续正常运行和强大进程控制的 Python Web 应用程序。当您需要广泛的进程管理、监视、日志管理以及对应用程序进程的启动、停止和重启进行自定义控制时，它特别有用。

有关详细理解和更多信息，请参阅官方 `Supervisor 文档 <http://supervisord.org/introduction.html>`_。

替代方案
~~~~~~~~~~~~

对于不同的部署场景，请考虑以下替代方案：

- :doc:`Docker <docker>`：
    适用于容器化环境，提供隔离和可扩展性。
- `systemd <https://www.freedesktop.org/wiki/Software/systemd/>`_：
    一个系统和服务管理器，集成到许多 Linux 发行版中以管理系统进程。

    .. note:: 官方文档即将推出
- :doc:`手动使用 ASGI 服务器 <manually-with-asgi-server>`：
    通过使用 ASGI 服务器（如 Uvicorn、Hypercorn、Daphne 等）运行应用程序来直接控制。

此资源提供了有关安装、配置和使用 ``supervisor`` 进行服务管理的全面指导。

.. _conf_file:

设置
-----

``supervisor`` 使用配置文件来定义服务。您可以在 `Supervisor 配置文档 <http://supervisord.org/configuration.html>`_ 中了解有关配置文件的更多信息。

.. code-block:: ini
    :caption: 示例 supervisor 配置文件

    [program:exampleapp]  # 定义服务名称。
    directory=/opt/exampleapp/src  # 指定服务应运行的目录。
    command=/opt/exampleapp/venv/bin/litestar app.py  # 指定运行服务的命令。
    redirect_stderr=true  # 将 stderr 重定向到 stdout。
    stdout_logfile=/var/log/exampleapp.log  # 指定要写入的日志文件。
    stdout_logfile_backups=10  # 指定要保留的备份数量。
    autostart=true  # 指定服务应在 ``supervisor`` 启动时自动启动。
    autorestart=true  # 指定服务如果意外退出应自动重启。

您可以将上述配置文件放在 ``/etc/supervisor/conf.d/exampleapp.conf`` 中。
创建配置文件后，您需要重新加载 ``supervisor`` 配置以加载新的服务文件。

.. dropdown:: 有用的命令

    .. code-block:: shell
        :caption: 重新加载 supervisor 配置

        sudo supervisorctl reread
        sudo supervisorctl update

    .. code-block:: shell
        :caption: 启动/停止/重启/状态

        sudo supervisorctl start exampleapp
        sudo supervisorctl stop exampleapp
        sudo supervisorctl restart exampleapp
        sudo supervisorctl status exampleapp

    .. code-block:: shell
        :caption: 查看日志

        sudo supervisorctl tail -f exampleapp

现在您可以启动应用程序了。

#. 如果服务尚未运行，则启动服务：``sudo supervisorctl start exampleapp``。
#. 通过检查输出是否有错误来确保其正常运行：``sudo supervisorctl status exampleapp``。
#. 确认后，您的 Litestar 应用程序应该可以访问（默认在 ``http://0.0.0.0:8000``）。

之后，您就完成了！现在可以使用 ``supervisor`` 来管理您的应用程序。
以下部分旨在提供一些建议以使事情更易于管理，它们不是必需的。

建议
-----------

.. tip::

        这延续了上面的设置，但提供了一些使事情更易于管理的建议。


别名
~~~~~~~

创建一个别名文件：``/etc/profile.d/exampleapp.sh``。

这就是让我们可以简单地使用 ``exampleapp start`` 而不是 ``sudo supervisorctl start exampleapp`` 的魔法所在。

.. dropdown:: 别名示例

    .. code-block:: shell
        :caption: 别名文件提供的示例命令

        exampleapp start
        exampleapp stop
        exampleapp restart
        exampleapp status
        exampleapp watch

    .. code-block:: shell
        :caption: 示例别名文件
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

要在不重启会话的情况下激活别名，请使用 ``source /etc/profile.d/exampleapp.sh``。
使用 ``watch`` 命令可以让您监视应用程序的实时输出。

更新脚本
~~~~~~~~~~~~~

``exampleapp`` 函数可以扩展以包含 ``update`` 命令，方便应用程序的完整更新过程：

.. dropdown:: 更新脚本示例

    .. code-block:: shell
        :caption: 示例更新命令
        :linenos:

        exampleapp() {
          case $1 in
            # ... 其他情况 ... #

            update)
              echo "Updating exampleapp..."

              # 停止服务
              echo " > Stopping service..."
              sudo supervisorctl stop exampleapp

              # 更新应用程序文件
              echo " > Pulling latest changes from repository..."
              cd /opt/exampleapp
              git fetch --all
              git reset --hard origin/master

              # 更新 Supervisor 配置和别名
              echo " > Updating Supervisor and shell configurations..."
              sudo ln -sf /opt/exampleapp/server/service.conf /etc/supervisor/conf.d/exampleapp.conf
              sudo ln -sf /opt/exampleapp/server/alias.sh /etc/profile.d/exampleapp.sh
              source /etc/profile.d/exampleapp.sh

              # 更新 Supervisor 以应用新配置
              echo " > Reloading Supervisor configuration..."
              sudo supervisorctl reread
              sudo supervisorctl update

              # 使用 requirements.txt 更新 Python 依赖项
              # 这里您可以替换为 poetry、pdm 等，减轻对
              # requirements.txt 文件和虚拟环境激活的需求。
              source venv/bin/activate
              echo " > Installing updated dependencies..."
              python3 -m pip install -r requirements.txt
              deactivate

              # ... 其他更新过程，如文档构建、清理等 ... #

              echo "Update process complete."

              # 提示启动服务
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

此更新过程包括以下步骤：

#. **停止服务：** 在进行更改之前安全地停止应用程序。
#. **Git 操作：** 确保从存储库中拉取最新代码。
#. **配置符号链接：** 更新 ``supervisor`` 配置和 shell 别名以反映任何更改。
#. **Supervisor 重新加载：** 将新的配置设置应用于 ``supervisor`` 服务。
#. **依赖项更新：** 根据锁定文件或 ``requirements.txt`` 中的定义安装或更新 Python 依赖项。
#. **用户提示：** 提供在更新后立即启动服务的选择。

执行
~~~~~~~~~

运行 ``exampleapp update`` 命令来执行此更新过程。
它简化了新代码和配置更改的部署，确保流畅且一致的应用程序更新周期。
