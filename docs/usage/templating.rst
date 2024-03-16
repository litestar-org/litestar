Templating
==========

.. |Jinja2| replace:: Jinja2
.. _Jinja2: https://jinja.palletsprojects.com/en/3.0.x/

.. |Mako| replace:: Mako
.. _Mako: https://www.makotemplates.org/

.. |MiniJinja| replace:: MiniJinja
.. _MiniJinja: https://github.com/mitsuhiko/minijinja/tree/main/minijinja-py

Litestar has built-in support for |Jinja2|_, |Mako|_ and |MiniJinja|_ template engines
as well as abstractions to make use of any template engine you wish.

Template engines
----------------

To stay lightweight, a Litestar installation does not include the |Jinja2|_, |Mako|_, or |MiniJinja|_
libraries themselves. Before you can start using them, you have to install it via the respective ``litestar``
`extra <https://packaging.python.org/en/latest/specifications/dependency-specifiers/#extras>`_.

.. tab-set::

    .. tab-item:: Jinja
        :sync: jinja

        .. code-block:: shell

            pip install litestar[jinja]

    .. tab-item:: Mako
        :sync: mako

        .. code-block:: shell

            pip install litestar[mako]

    .. tab-item:: MiniJinja
        :sync: minijinja

        .. code-block:: shell

            pip install litestar[minijinja]

.. tip::

    |Jinja2|_ is included in the ``standard`` extra. If you installed Litestar using
    ``litestar[standard]``, you do not need to explicitly add the ``jinja`` extra.


Registering a template engine
^^^^^^^^^^^^^^^^^^^^^^^^^^^^^

To register one of the built-in template engines you simply need to pass it to the :class:`~litestar.app.Litestar`
constructor:

.. tab-set::

    .. tab-item:: Jinja
        :sync: jinja

        .. literalinclude:: /examples/templating/template_engine_jinja.py
            :language: python

    .. tab-item:: Mako
        :sync: mako

        .. literalinclude:: /examples/templating/template_engine_mako.py
            :language: python

    .. tab-item:: MiniJinja
        :sync: minijinja

        .. literalinclude:: /examples/templating/template_engine_minijinja.py
            :language: python

.. note::

    The :attr:`~litestar.template.TemplateConfig.directory` field
    passed to :class:`TemplateConfig <litestar.template.TemplateConfig>` can be either a
    directory or list of directories to use for loading templates.

Registering a Custom Template Engine
^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^

The above example will create a ``jinja`` :class:`Environment <jinja2.Environment>` instance,
but you can also pass in your own instance.

.. code-block:: python
    :caption: Using a custom Jinja environment

    from litestar import Litestar
    from litestar.contrib.jinja import JinjaTemplateEngine
    from litestar.template import TemplateConfig
    from jinja2 import Environment, DictLoader

    my_custom_env = Environment(loader=DictLoader({"index.html": "Hello {{name}}!"}))
    app = Litestar(
        template_config=TemplateConfig(
            instance=JinjaTemplateEngine.from_environment(my_custom_env)
        )
    )


.. note:: The :attr:`~litestar.template.TemplateConfig.instance` field in
    :class:`~litestar.template.TemplateConfig` should not be used together
    with the :attr:`~litestar.template.TemplateConfig.directory` field.
    When utilizing the :attr:`~litestar.template.TemplateConfig.instance` field,
    you take full responsibility for the instantiation and management of the engine.

Defining a custom template engine
^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^

If you wish to use another templating engine, you can easily do so by implementing
:class:`TemplateEngineProtocol <litestar.template.TemplateEngineProtocol>`. This class accepts a generic
argument which should be the template class, and it specifies two methods:

.. code-block:: python

   from typing import Protocol, Union, List
   from pydantic import DirectoryPath

   # the template class of the respective library
   from some_lib import SomeTemplate


   class TemplateEngineProtocol(Protocol[SomeTemplate]):
       def __init__(self, directory: Union[DirectoryPath, List[DirectoryPath]]) -> None:
           """Builds a template engine."""
           ...

       def get_template(self, template_name: str) -> SomeTemplate:
           """Loads the template with template_name and returns it."""
           ...

Once you have your custom engine you can register it as you would the built-in engines.

Accessing the template engine instance
^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^

If you need to access the template engine instance, you can do so via the
:attr:`engine <litestar.template.TemplateConfig>` field:

.. tab-set::

    .. tab-item:: Jinja
        :sync: jinja

        .. literalinclude:: /examples/templating/engine_instance_jinja.py
            :language: python

    .. tab-item:: Mako
        :sync: mako

        .. literalinclude:: /examples/templating/engine_instance_mako.py
            :language: python

    .. tab-item:: MiniJinja
        :sync: minijinja

        .. literalinclude:: /examples/templating/engine_instance_minijinja.py
            :language: python

Template responses
------------------

Once you have a template engine registered you can return :class:`templates responses <.response.Template>` from
your route handlers:

.. tab-set::

    .. tab-item:: Jinja
        :sync: jinja

        .. literalinclude:: /examples/templating/returning_templates_jinja.py
            :language: python

    .. tab-item:: Mako
        :sync: mako

        .. literalinclude:: /examples/templating/returning_templates_mako.py
            :language: python

    .. tab-item:: MiniJinja
        :sync: minijinja

        .. literalinclude:: /examples/templating/returning_templates_minijinja.py
            :language: python

* ``name`` is the name of the template file within on of the specified directories. If
  no file with that name is found, a :class:`TemplateNotFoundException <.exceptions.TemplateNotFoundException>`
  exception will be raised.
* ``context`` is a dictionary containing arbitrary data that will be passed to the template
  engine's ``render`` method. For Jinja and Mako, this data will be available in the `template context <#template-context>`_

Template Files vs. Strings
--------------------------

When you define a template response, you can either pass a template file name or a string
containing the template. The latter is useful if you want to define the template inline
for small templates or :doc:`HTMX </usage/htmx>` responses for example.

.. tab-set::

    .. tab-item:: File name

            .. code-block:: python
                :caption: Template via file

                @get()
                async def example() -> Template:
                    return Template(template_name="test.html", context={"hello": "world"})

    .. tab-item:: String

            .. code-block:: python
                :caption: Template via string

                @get()
                async def example() -> Template:
                    template_string = "{{ hello }}"
                    return Template(template_str=template_string, context={"hello": "world"})

Template context
----------------

Both |Jinja2|_ and |Mako|_
support passing a context object to the template as well as defining callables that will be available inside the template.

Accessing the request instance
^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^

The current :class:`Request <litestar.connection.request.Request>` is available within the
template context under ``request``, which also provides access to the :doc:`app instance </usage/applications>`.

Within the template context, the current :class:`~litestar.connection.request.Request` object is accessible using
the ``request`` variable (available via the
:ref:`reserved keyword arguments <usage/routing/handlers:"reserved" keyword arguments>`).
This also provides a way to reference the :doc:`app instance </usage/applications>`.

For instance, to access ``app.state.key``, you can use the following syntax in your template:

.. code-block:: html
    :caption: Accessing the app state in a template by using the ``reserved`` kwarg in ``example.html``

    <strong>check_context_key: </strong>{{ request.app.state.some_key }}

.. tab-set::

    .. tab-item:: Jinja
        :sync: jinja

        .. code-block:: html
           :caption: Accessing the app state in a |Jinja2|_ template

           <html>
               <body>
                   <div>
                       <span>My state value: {{ request.app.state.some_key }}</span>
                   </div>
               </body>
           </html>


    .. tab-item:: Mako
        :sync: mako

        .. code-block:: html
           :caption: Accessing the app state in a |Mako|_ template

           <html>
               <body>
                   <div>
                       <span>My state value: ${request.app.state.some_key}</span>
                   </div>
               </body>
           </html>


    .. tab-item:: MiniJinja
        :sync: minijinja

        .. code-block:: html
           :caption: Accessing the app state in a |MiniJinja|_ template

           <html>
               <body>
                   <div>
                       <span>My state value: {{ request.app.state.some_key }}</span>
                   </div>
               </body>
           </html>


Adding CSRF inputs
^^^^^^^^^^^^^^^^^^

If you want to add a hidden ``<input>`` tag containing a
`CSRF token <https://developer.mozilla.org/en-US/docs/Web/Security/Types_of_attacks#cross-site_request_forgery_csrf>`_,
you first need to configure :ref:`CSRF protection <usage/middleware/builtin-middleware:csrf>`.
With that in place, you can now insert the CSRF input field inside an HTML form:

.. tab-set::

    .. tab-item:: Jinja
        :sync: jinja

        .. code-block:: html
            :caption: Adding a CSRF input in a |Jinja2|_ template

            <html>
               <body>
                   <div>
                       <form action="https://myserverurl.com/some-endpoint" method="post">
                           {{ csrf_input | safe }}
                           <label for="fname">First name:</label><br>
                           <input type="text" id="fname" name="fname">
                           <label for="lname">Last name:</label><br>
                           <input type="text" id="lname" name="lname">
                       </form>
                   </div>
               </body>
            </html>

    .. tab-item:: Mako
        :sync: mako

        .. code-block:: html
            :caption: Adding a CSRF input in a |Mako|_ template

            <html>
               <body>
                   <div>
                       <form action="https://myserverurl.com/some-endpoint" method="post">
                           ${csrf_input | n}
                           <label for="fname">First name:</label><br>
                           <input type="text" id="fname" name="fname">
                           <label for="lname">Last name:</label><br>
                           <input type="text" id="lname" name="lname">
                       </form>
                   </div>
               </body>
            </html>

    .. tab-item:: MiniJinja
        :sync: minijinja

        .. code-block:: html
            :caption: Adding a CSRF input in a |MiniJinja|_ template

            <html>
               <body>
                   <div>
                       <form action="https://myserverurl.com/some-endpoint" method="post">
                           {{ csrf_input | safe }}
                           <label for="fname">First name:</label><br>
                           <input type="text" id="fname" name="fname">
                           <label for="lname">Last name:</label><br>
                           <input type="text" id="lname" name="lname">
                       </form>
                   </div>
               </body>
            </html>

The input holds a CSRF token as its value and is hidden so users cannot see or interact with it. The token is sent
back to the server when the form is submitted, and is checked by the CSRF middleware.

.. note::

    The ``csrf_input`` must be marked as safe in order to ensure that it does not get escaped.

Passing template context
^^^^^^^^^^^^^^^^^^^^^^^^

Passing context to the template is very simple - it is one of the kwargs expected by the
:class:`Template <litestar.response.Template>` container, so simply pass a string keyed dictionary of values:

.. code-block:: python
    :caption: Passing context to a template

    from litestar import get
    from litestar.response import Template


    @get(path="/info")
    def info() -> Template:
        return Template(template_name="info.html", context={"numbers": "1234567890"})

Template callables
------------------

Both |Jinja2|_ and |Mako|_ allow users to define custom callables that are ran inside the template.
Litestar builds on this and offers some functions out of the box.

Built-in callables
^^^^^^^^^^^^^^^^^^

``url_for``
    To access urls for route handlers you can use the ``url_for`` function. Its signature and behaviour
    matches :meth:`route_reverse <litestar.app.Litestar.route_reverse>` behaviour.

    More details about route handler indexing can be found :ref:`here <usage/routing/handlers:route handler indexing>`.

``csrf_token``
    This function returns the request's unique :ref:`CSRF token <usage/middleware/builtin-middleware:csrf>`
    You can use this if you wish to insert the ``csrf_token`` into non-HTML based templates, or insert it
    into HTML templates not using a hidden input field but by some other means, for example
    inside a special ``<meta>`` tag.

``url_for_static_asset``
    URLs for static files can be created using the ``url_for_static_asset`` function.
    It is signature and behaviour are identical to
    :meth:`app.url_for_static_asset <litestar.app.Litestar.url_for_static_asset>`.


Registering template callables
^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^

The :class:`TemplateEngineProtocol <litestar.template.base.TemplateEngineProtocol>` specifies the
``register_template_callable`` method that allows defining a custom callable on a template engine.

This method is implemented for all engines implementing the
:class:`TemplateEngineProtocol <litestar.template.base.TemplateEngineProtocol>`, and it can be used to
register callables that will be injected into the template. The callable should expect one argument:
the ``context`` dictionary.

It can be any callable - a function, method, or class that defines the ``__call__`` method. For example:

.. tab-set::

    .. tab-item:: Jinja
        :sync: jinja

        .. literalinclude:: /examples/templating/template_functions_jinja.py
            :caption: Registering template callables in |Jinja2|_ in ``app.py``

        .. literalinclude:: /examples/templating/templates/index.html.jinja2
            :language: html
            :caption: Using the registered template callable in a |Jinja2|_ template

    .. tab-item:: Mako
        :sync: mako

        .. literalinclude:: /examples/templating/template_functions_mako.py
            :caption: Registering template callables in |Mako|_ in ``app.py``

        .. literalinclude:: /examples/templating/templates/index.html.mako
            :language: html
            :caption: Using the registered template callable in a |Mako|_ template

    .. tab-item:: Minijinja
        :sync: minijinja

        .. literalinclude:: /examples/templating/template_functions_minijinja.py
            :caption: Registering template callables in |MiniJinja|_ in ``app.py``

        .. literalinclude:: /examples/templating/templates/index.html.minijinja
            :language: html
            :caption: Using the registered template callable in a |MiniJinja|_ template

Run the example with ``litestar run`` and open your application
(defaults to `http://127.0.0.1:8000 <http://127.0.0.1:8000>`_) and you will see:

.. image:: /images/examples/template_engine_callable.png
    :alt: Template engine callable example
