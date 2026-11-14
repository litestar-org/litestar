Contribution Guide
==================

Getting Started
---------------

Supported Python Versions
+++++++++++++++++++++++++

The lowest currently supported version is Python 3.11.
At a minimum you will need Python 3.11 for code changes and 3.13 if you plan on doing documentation building / changes.

You can use various tools to manage multiple Python versions on your system including:

* Using `uv built-in <https://docs.astral.sh/uv/guides/install-python/>`_ Python version management.
* `pyenv <https://github.com/pyenv/pyenv>`_ and `pyenv-win for Windows <https://github.com/pyenv-win/pyenv-win>`_
* `rtx / mise <https://mise.jdx.dev/>`_
* `asdf <https://asdf-vm.com/>`_
* `Building each version manually from source <https://www.build-python-from-source.com/>`_
* Utilizing `GitHub Codespaces <https://codespaces.new/litestar-org/litestar?quickstart=1>`_

We use the lowest supported version in our type-checking CI,
this ensures that the changes you made are backward compatible.

Setting up the environment
++++++++++++++++++++++++++

.. tip:: We maintain a Makefile with several commands to help with common tasks.
   You can run ``make help`` to see a list of available commands.

If you are utilizing `GitHub Codespaces <https://codespaces.new/litestar-org/litestar?quickstart=1>`_,
the environment will bootstrap itself automatically. The steps below are for local development.

#. Install `uv <https://docs.astral.sh/uv/getting-started/installation/>`_:

#. Run ``make install`` to create a `virtual environment <https://docs.python.org/3/tutorial/venv.html>`_
   and install the required development dependencies or run the ``uv sync`` command manually:

   .. code-block:: shell
        :caption: Installing the development dependencies

        uv sync


.. tip:: Many modern IDEs like PyCharm or VS Code will enable the uv-managed virtualenv that is created in step 2
   for you automatically.
   If your IDE / editor does not offer this functionality, then you will need to manually activate the virtualenv
   yourself. Otherwise you may encounter errors or unexpected behaviour when trying to run the commands referenced
   within this document.

   To activate the virtualenv manually, please consult uv's documentation on
   `working with virtual environments <https://docs.astral.sh/uv/pip/environments/>`_.

   The rest of this document will assume this environment is active wherever commands are referenced.

Code contributions
------------------

.. important::
    * Documentation PRs are always welcome; it's often a very good entry point to get familiar with the project.
    * Bug fixes and small improvements are also a good way to get started. There is no shortage of small things that can be improved.
    * We're all humans (hopefully) and may forget about your particular PR. If you feel your PR has stalled, feel free to gently nudge us.
    * Large features or refactors may take time. Please be patient; we're all volunteers and want to ensure the best possible outcome.
    * Use LLMs intelligently. Most PRs automatically generated are not usable, and incur a higher than normal cost from reviewers and maintainers, as they still need to be thoroughly evaluated, even if they are ultimately not acceptable.


Workflow
++++++++

#. `Fork <https://github.com/litestar-org/litestar/fork>`_ the `Litestar repository <https://github.com/litestar-org/litestar>`_
#. Clone your fork locally with git
#. `Set up the environment <#setting-up-the-environment>`_
#. Make your changes
#. If your change is user-facing (``feat`` / ``fix`` / ``perf`` / ``refactor``), add a changelog fragment
   (see `Changelog fragments`_)
#. (Optional) Run ``pre-commit run --all-files`` to run linters and formatters. This step is optional and will be executed
   automatically by git before you make a commit, but you may want to run it manually in order to apply fixes
#. Commit your changes to git. We follow `conventional commits <https://www.conventionalcommits.org/>`_
   which are enforced using a ``pre-commit`` hook.
#. Push the changes to your fork
#. Open a `pull request <https://docs.github.com/en/pull-requests>`_. Give the pull request a descriptive title
   indicating what it changes. The style of the PR title should also follow
   `conventional commits <https://www.conventionalcommits.org/>`_, and this is enforced using a GitHub action.
#. Add yourself as a contributor using the `all-contributors bot <https://allcontributors.org/docs/en/bot/usage>`_

Changelog fragments
+++++++++++++++++++

Changelog entries are assembled from *news fragments* with
`towncrier <https://towncrier.readthedocs.io>`_. Every PR that adds a feature or fixes a
bug (conventional-commit ``feat`` / ``fix`` / ``perf`` / ``refactor``) should include a
fragment under ``docs/release-notes/fragments/``.

Create ``docs/release-notes/fragments/<PR_NUMBER>.change.rst`` with a single
``.. change::`` directive:

.. code-block:: rst

    .. change:: Short, imperative summary of the change
        :type: bugfix          # one of: feature | bugfix | misc
        :pr: 1234
        :issue: 567            # optional; space-separated for multiple

        A longer description in reStructuredText. For breaking changes, add a
        ``:breaking:`` line under ``:type:`` and explain how to migrate.

If a single PR introduces several distinct entries, add ``<PR_NUMBER>-2.change.rst``,
``<PR_NUMBER>-3.change.rst``, and so on.

Optionally scaffold the file::

    uvx --from 'towncrier>=24,<26' towncrier create --edit 1234.change.rst

Preview the assembled changelog without writing anything::

    uvx --from 'towncrier>=24,<26' towncrier build --draft --version 3.0.0

Docs-only, chore, CI, or other non-user-facing PRs don't need a fragment — apply the
``skip-changelog`` label to bypass the check. The check is currently *advisory* (warn-only)
and will become required at the 3.0 final release.

Guidelines for writing code
----------------------------

- Code should be `Pythonic and zen <https://peps.python.org/pep-0020/>`_
- All code should be fully `typed <https://peps.python.org/pep-0484/>`_. This is enforced via
  `mypy <https://mypy.readthedocs.io/en/stable/>`_ and `Pyright <https://github.com/microsoft/pyright/>`_

  * When requiring complex types, use a `type alias <https://docs.python.org/3/library/typing.html#type-aliases>`_.
    Check :doc:`reference/types` if a type alias for your use case already exists
  * If something cannot be typed correctly due to a limitation of the type checkers, you may use :func:`typing.cast`
    to rectify the situation. However, you should only use this as a last resort if you've exhausted all other options
    of `type narrowing <https://mypy.readthedocs.io/en/stable/type_narrowing.html>`_, such as :func:`isinstance` checks
    and `type guards <https://docs.python.org/3/library/typing.html#typing.TypeGuard>`_.
  * You may use a properly scoped ``type: ignore`` if you ensured that a line is correct, but mypy / pyright has
    issues with it.

    Properly scoped meaning do not use blank ``type: ignore``, instead supply the specific error code, e.g.,
    ``type: ignore[attr-defined]``

- If you are adding or modifying existing code, ensure that it's fully tested. 100% test coverage is mandatory, and will
  be checked on the PR using `SonarCloud <https://www.sonarsource.com/products/sonarcloud/>`_ and
  `Codecov <https://codecov.io/>`_
- All functions, methods, classes, and attributes should be documented with a docstring. We use the
  `Google docstring style <https://sphinxcontrib-napoleon.readthedocs.io/en/latest/example_google.html>`_. If you come
  across a function or method that doesn't conform to this standard, please update it as you go
- When adding a new public interface, it has to be  included in the reference documentation located in
  ``docs/reference``. If applicable, add or modify examples in the docs related to the new functionality implemented,
  following the guidelines established in `Adding examples`_.


Writing and running tests
+++++++++++++++++++++++++

Tests are contained within the ``tests`` directory, and follow the same directory structure as the ``litestar`` module.
If you are adding a test case, it should be located within the correct submodule of ``tests``. E.g., tests for
``litestar/utils/sync.py`` reside in ``tests/utils/test_sync.py``.

The ``Makefile`` includes several commands for running tests:

- ``make test`` to run tests located in ``tests``
- ``make test-examples`` to run tests located in ``docs/examples/tests``
- ``make test-all`` to run all tests
- ``make coverage`` to run tests with coverage and generate an html report

The tests make use of `pytest-xdist <https://pytest-xdist.readthedocs.io>`_ to speed up
test runs. These are enabled by default when running ``make test``, ``make test-all``
or ``make coverage``. Due to the nature of pytest-xdist, attaching a debugger isn't as
straightforward. For debugging, it's recommended to run the tests individually with
``pytest <test name>`` or via an IDE, which will skip ``pytest-xdist``.

Benchmarks
++++++++++

Benchmarks live in ``tests/benchmarks`` and are measured by
`CodSpeed <https://codspeed.io/litestar-org/litestar>`_ in CI. They are ordinary pytest
tests, so ``make test`` runs each of them once.

When adding one, drive the app with ``ASGIRunner`` from ``tests/benchmarks/helpers.py``
rather than ``TestClient``, and assert on the result so it keeps working as a test.
``pytest-codspeed`` forwards keyword arguments to its own measuring function, so pass the
call's arguments positionally or wrap it in a ``lambda`` -- a keyword named ``target``,
``fn``, ``name``, ``uri`` or ``marker_options`` collides with it.

Running type checkers
+++++++++++++++++++++

We use `mypy <https://mypy.readthedocs.io/en/stable/>`_ and `pyright <https://github.com/microsoft/pyright/>`_ to
enforce type safety. You can run them with:

- ``make mypy``
- ``make pyright``
- ``make type-check`` to run both
- ``make lint`` to run pre-commit hooks and type checkers.

Our type checkers are run on Python 3.11 in CI, so you should make sure to run them on the same version locally as well.

Project documentation
---------------------

The documentation is located in the ``/docs`` directory and is written in
`reStructuredText <https://docutils.sourceforge.io/rst.html>`_ with the
`Sphinx <https://www.sphinx-doc.org/en/master/>`_ library. If you're unfamiliar with any of those,
`reStructuredText primer <https://www.sphinx-doc.org/en/master/usage/restructuredtext/basics.html>`_ and
`Sphinx quickstart <https://www.sphinx-doc.org/en/master/usage/quickstart.html>`_ are recommended reads.

Docs theme and appearance
+++++++++++++++++++++++++

We welcome contributions that enhance / improve the appearance and usability of the docs. We use the excellent
`PyData Sphinx Theme <https://pydata-sphinx-theme.readthedocs.io/>`_ theme, which comes with a lot of options out of the box.
If you wish to contribute to the docs style / setup, or static site generation, you should consult the theme docs
as a first step.

Running the docs locally
++++++++++++++++++++++++

You can serve the documentation locally with

.. code-block:: shell
    :caption: Serving the documentation locally

    make docs-serve

or build it with

.. code-block:: shell
    :caption: Serving the documentation locally

    make docs


Writing and editing docs
++++++++++++++++++++++++

We welcome contributions that enhance / improve the content of the docs. Feel free to add examples, clarify text,
restructure the docs, etc., but make sure to follow these guidelines:

- Write text in idiomatic English, using simple language
- Do not use contractions for ease of reading for non-native English speakers
- Opt for `Oxford commas <https://en.wikipedia.org/wiki/Serial_comma>`_ when listing a series of terms
- Keep examples simple and self contained (see `Adding examples`_). This is to ensure they are tested
  alongside the rest of the test suite and properly type checked and linted.
- Provide links where applicable.
- Use `intersphinx <https://www.sphinx-doc.org/en/master/usage/extensions/intersphinx.html>`_ wherever possible when
  referencing external libraries
- Provide diagrams using `Mermaid <https://mermaid.js.org/>`_ where applicable and possible

Adding examples
~~~~~~~~~~~~~~~

The examples from the docs are located in their own modules inside the ``/docs/examples`` folder. This makes it easier
to test them alongside the rest of the test suite, ensuring they do not become stale as Litestar evolves.

Please follow the next guidelines when adding a new example:

- Add the example in the corresponding module directory in ``/docs/examples`` or create a new one if necessary
- Create a suite for the module in ``/tests/examples`` that tests the aspects of the example that it demonstrates
- Reference the example in the rst file with an external reference code block, e.g.

.. code-block:: rst
   :caption: An example of how to use literal includes of external files

   .. literalinclude:: /examples/test_thing.py
      :language: python
      :caption: All includes should have a descriptive caption

Automatically execute examples
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

Our docs include a Sphinx extension that can automatically run requests against example apps
and include their result in the documentation page when it's being built. This only requires 2 steps:

1. Create an example file with an ``app`` object in it, which is an instance of ``Litestar``
2. Add a comment in the form of ``# run: /hello`` to the example file

When building the docs (or serving them locally), a process serving the ``app`` instance
will be launched, and the requests specified in the comments will be run against it. The
comments will be stripped from the result, and the output of the ``curl`` invocation inserted
after the example code-block.

The ``# run:`` syntax is nothing special; everything after the colon will be passed to
the ``curl`` command that's being invoked. The URL is built automatically, so the
specified path can just be a path relative to the app.

In practice, this looks like the following:

.. code-block:: python
   :caption: An example of how to use the automatic example runner
   :no-upgrade:

   from typing import Dict

   from litestar import Litestar, get


   @get("/")
   def hello_world() -> Dict[str, str]:
       """Handler function that returns a greeting dictionary."""
       return {"hello": "world"}


   app = Litestar(route_handlers=[hello_world])

   # run: /

This is equivalent to:

.. code-block:: python
   :caption: An example of how to use the automatic example runner

      from typing import Dict

      from litestar import Litestar, get


      @get("/")
      def hello_world() -> Dict[str, str]:
          """Handler function that returns a greeting dictionary."""
          return {"hello": "world"}


      app = Litestar(route_handlers=[hello_world])


.. admonition:: Run it

      .. code-block:: bash

         > curl http://127.0.0.1:8000/
         {"hello": "world"}


Creating a New Release
----------------------

Run the `Release workflow <https://github.com/litestar-org/litestar/actions/workflows/release.yml>`_
from the Actions tab:

#. Run it with ``dry_run: true``. Nothing is written — it reports readiness, previews the
   changelog entry and prints the GitHub release notes. Read the notes, especially the
   *Other changes* section: not every entry belongs in the final notes.
#. Run it again with ``dry_run: false``. It bumps the version, assembles the changelog,
   and opens a ``vX.Y.Z`` pull request. Each pre-release keeps its own changelog section.
#. Review and merge that PR. Merging creates a **draft** GitHub release with the generated
   notes.
#. Open the draft release, edit the notes if needed, and click "Publish release". That
   triggers ``publish.yml``; approve it if prompted and check that it succeeds.

While a pre-release is pending, a bump may only continue that line (``alpha`` / ``beta`` /
``rc``) or finish it (``stable``). Pass an explicit ``version`` to override. Versions follow
`semantic versioning <https://semver.org/>`_, `PEP 440 <https://peps.python.org/pep-0440/>`_
and the `versioning scheme <https://litestar.dev/about/litestar-releases#version-numbering>`_.

Locally
~~~~~~~

The same two steps, without touching GitHub:

.. code-block:: shell

    make release-preview BUMP=patch        # writes nothing; VERSION=3.0.0rc1 also works
    make release-prepare BUMP=patch        # branch + bump + changelog + commit, no push

Then push the branch and open the PR; merging it creates the draft release as above.
