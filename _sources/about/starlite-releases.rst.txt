Starlite releases
=================

Version numbering
-----------------

Starlite follows the `Semantic Versioning <https://semver.org/>`_ standard, using the
``<major>.<minor>.<patch>`` schema, increasing the version numbers as follows:

Major
    Backwards incompatible changes have been made

Minor
    Functionality was added, in a backwards compatible manner

Patch
    Bugfixes were applied, in a backwards compatible manner


Release schedule
----------------

Starlite follows a non-strict release schedule, targeting about 6 months between major,
and 4 weeks between minor versions. For major releases, this is to be interpreted as a
lower bound, meaning it may take longer for a particular major version to be released,
but it won't be less than 6 months after the last major release.


About major versions
--------------------

Starlite's major releases are *generally backwards compatible* and usually won't include
major breaking changes. They can be seen as maintenance releases that offer the
opportunity to make some backwards incompatible changes.

Due to the frequency of major releases, Starlite evolves gradually over time and there
won't be sweeping changes that require a complete rewrite of an application or major
migration efforts when upgrading to a new major version.


LTS releases and support
------------------------

The last released minor version becomes the current *LTS release* once a new major
version is released. These LTS releases will receive **patch** releases for security and
other critical bugfixes *at least until the next major release*.


Deprecation policy
------------------

If a feature of Starlite is to be removed, a deprecation warning will be added in a
**minor** release. Deprecated features will still be supported throughout every release
of the respective *major* release. In practice this means that if a deprecation warning
is added in ``1.x``, the feature will continue to work for every ``1.`` release, and be
removed in the ``2.0`` release.
