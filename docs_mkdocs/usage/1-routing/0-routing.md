# Routing

Starlite implements its routing solution that is based on the concept of a
[radix tree](https://en.wikipedia.org/wiki/Radix_tree) or `trie`.

## Why Radix Based Routing?

The regex matching used by Starlette (and FastAPI etc.) is very good at resolving path parameters fast, giving it
an advantage when a URL has a lot of path parameters - what we can think of as `vertical` scaling. On the
other hand, it is not good at scaling horizontally - the more routes, the less performant it becomes. Thus,
there is an inverse relation between performance and application size with this approach that strongly favors very
small microservices. The **trie** based approach used by Starlite is agnostic to the number of routes of the
application giving it better horizontal scaling characteristics at the expense of somewhat slower resolution of path
parameters.

!!! tip
    If you are interested in the technical aspects of the implementation, refer to
    [this GitHub issue](https://github.com/starlite-api/starlite/issues/177) - it includes an indepth discussion of the
    pertinent code.
