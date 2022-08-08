# Routing

Although `Starlite` builds on the `Starlette` ASGI toolkit as a basis, it does not use the `Starlette` routing system,
which uses regex matching, and instead it implements its own solution that is based on the concept of a
[radix tree](https://en.wikipedia.org/wiki/Radix_tree) or `trie`.

<!-- prettier-ignore -->
!!! important
    We are currently in the processes of porting the `Starlite` routing system into __rust__, which will increase the
    framework's velocity by an order of magnitude. You can read more about this in
    [the following GitHub issue](https://github.com/starlite-api/starlite/issues/177).

## Why Radix Based Routing?

The regex matching used by `Starlette` (and `FastAPI` etc.) is very good at resolving path parameters fast. It thus has
an advantage when a lot of path parameter are involved in an url - what we can think of as `vertical` scaling. On the
other hand, it is not good at scaling horizontally- the more routes are added, the less performant it becomes. Thus,
there is an inverse relation between performance and application size with this approach - which strongly favors very
small microservices. The **trie** based approach used by `Starlite` scales horizontally much better, and is not
affected by the number of routes added to the application. It is thus agnostic to the size of the application, at the
expanse of somewhat slower resolution of path parameters.

<!-- prettier-ignore -->
!!! tip
    If you are interested in the technical aspects of the implementation, refer to
    [this GitHub issue](https://github.com/starlite-api/starlite/issues/177) - it includes an indepth discussion of the
    pertinent code.
