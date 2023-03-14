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


Pre-release versions
++++++++++++++++++++

A major release may be preceded by a number of pre-releases. The pre-release identifier
will be appended to the major version number and follow the schema ``<release type><release number>``. The resulting
version number will have the schema ``<major>.<minor>.<patch><release type><release number>``, for example
``2.0.0alpha1``.

The release types are:

``alpha``
    A developmental release, equivalent to the current status of the development branch. At this point, new
    features can still be added and breaking changes introduced. These releases should be considered very unstable and
    are intended for early developer feedback.

``beta``
    A more stable development release. New features might be added at this point, but no major breaking changes are to
    be expected

``rc``
    "Release candidate". This is the first release after the feature freeze before a new major release. No new features
    and breaking changes will be introduced at this point, only bugfixes will be added at this point. This release is
    suitable for testing migration to the upcoming major release. Each major version will be preceded by *at least* one
    release candidate.


Release schedule
----------------

Starlite follows a non-strict release schedule, targeting about 6 months between major,
and 4 weeks between minor versions. For major releases, this is to be interpreted as a
lower bound, meaning it may take longer for a particular major version to be released,
but it won't be less than 6 months after the last major release.


About major version
--------------------

Starlite's major releases are *generally backwards compatible* and usually won't include
major breaking changes. They can be seen as maintenance releases that offer the
opportunity to make some backwards incompatible changes.

Due to the frequency of major releases, Starlite evolves gradually over time and there
won't be sweeping changes that require a complete rewrite of an application or major
migration efforts when upgrading to a new major version.


Supported versions
------------------

Current version
    The current version is the last release of the most recent major version. This
    version is under active development and will receive bugfixes as well as feature
    updates in minor releases (see `Version numbering`_)

Maintenance versions
    When a new major version is released, the last *minor* version before it enters
    maintenance mode. It will receive bugfixes and other critical patches during the
    next two release cycles


In practice this means that, at any given time, there may be up to 3 currently supported
releases: The current version and the two major versions preceding it.


Deprecation policy
------------------

If a feature of Starlite is to be removed, a deprecation warning will be added in a
**minor** release. Deprecated features will still be supported throughout every release
of the respective *major* release. In practice this means that if a deprecation warning
is added in ``1.x``, the feature will continue to work for every ``1.`` release, and be
removed in the ``2.0`` release.
