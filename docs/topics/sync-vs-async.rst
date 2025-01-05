Sync vs. Async
==============


Litestar supports synchronous as well as asynchronous callables in almost all places
where it's possible to do so. In general, three different modes of execution are
supported:

- Running asynchronous callables directly
- Running synchronous callables directly
- Running synchronous callables in a thread pool

This article gives an overview of important differences between these modes.


Blocking and non-blocking
-------------------------

In the context of asynchronous programming, the terms *blocking* and *non-blocking*
are often used to describe a particular quality of a function: Blocking the flow of
execution.

Asynchronous functions are not inherently non-blocking. What they do instead is allow a
programmer to control exactly *where* they unblock and return control to the main loop,
allowing other asynchronous tasks to run, which is usually indicated by the use of the
``await`` keyword.  This is a very important aspect to note, since an async function
that never calls ``await`` and, for example, performs a computationally intensive task,
*will* block the main thread for its entire runtime, just like a synchronous function
would. More importantly, anything that happens inside an asynchronous function
*between* the parts where it waits will also be blocked.

Technically speaking, this means that there are no non-blocking functions in Python,
since async functions only "unblock" at each ``await``. As this is not a useful
definition of the term, "blocking" usually refers to callables that *block for a long
time*.

.. note::

    Since "blocking" is about the flow of execution, one might think of ``await`` as
    blocking as well; the execution will not proceed past it until the awaitable has
    been resolved, which fits the definition of the term. However, since at the same
    time *other parts of the program* (more precisely, other coroutines which had
    given up control at an ``await`` that has since completed) are allowed to
    proceed, this is not considered blocking and usually referred to as "waiting".


I/O bound vs. CPU bound
-----------------------

Another important aspect to consider when trying to determine whether a function should
be asynchronous or not is *why* it might block. In general, there are two different
categories of blocking operations:

I/O bound
    Calls to the file system or network are typical examples of I/O-bound blocking.
    Their execution speed is largely limited by the time it takes for the external
    resource to complete, which makes them "bound" to that resource.

    They are a good fit for async because most of the time is spent waiting for these
    operations to complete. This means that other tasks can be executed during this
    time, "waiting in parallel", greatly reducing the overall runtime.

CPU bound
    Operations that do not wait on I/O can be usually considered CPU bound. Since they
    don't wait for external resources, their execution speed is bound to the CPU, i.e.
    how fast it can execute the instructions given.

    They do not benefit from asynchronous execution like I/O bound tasks, since they
    don't spend a significant amount of time waiting.


Asynchronous CPU-bound tasks
++++++++++++++++++++++++++++

In some cases, CPU bound tasks can be made asynchronous, by introducing points for the
event loop to switch to other tasks. An example of this would be an inner loop which
awaits :func:`asyncio.sleep(0) <asyncio.sleep>` at the beginning of each iteration.

This technique is mostly useful for long-running tasks, where each individual step does
not block for an extended period of time.


When to use an asynchronous function
------------------------------------

Asynchronous functions should be used when they can benefit from a concurrent execution,
that is, they themselves perform asynchronous operations, such as calling other
asynchronous functions or iterating asynchronously, and do not perform any blocking
operations, such as calling synchronous functions that are I/O bound.

**Why not use async by default?**

It might be tempting to look at this and think a function should be async by default,
unless it's performing blocking operations synchronously, but this is not the case.
Async itself has an overhead attached to it which, while very small, can in some
situations become non negligible. A synchronous function performing non-blocking
operations will outperform an asynchronous function doing the same.


When to use a synchronous function
----------------------------------

As an inverse of the previous paragraph, it follows that synchronous functions should
be used for non-io intensive tasks. The synchronous execution
model allows for the smallest amount of overhead and should therefore be preferred in
such situations where no asynchronous functionality is made use of.


When to use a thread pool
-------------------------

If a function performs computationally intense or I/O bound operations, which can not be
replaced by asynchronous equivalents, ``sync_to_thread=True`` can be used to run it in
a thread pool.

**Why not make this the default for synchronous functions?**

Running in a thread pool has a very high overhead, greatly reducing an application's
performance. Its use should therefore be restricted to cases where it's absolutely
necessary.


Limitations
+++++++++++

While running a CPU bound function in a thread pool does allow it to be run in a
non-blocking way, it does not speed up its execution. Computationally intensive tasks
that are performed regularly should be offloaded into a different process, to make use
of multiple CPU cores.

This can for example be achieve by using :func:`anyio.to_process.run_sync`.


Warnings about the mode of execution
------------------------------------

Since a synchronous function might be blocking, Litestar will raise a warning about its
use in places where it might block the main event loop and impact the application's
performance. If a synchronous function is non-blocking, setting ``sync_to_thread=False``
will tell Litestar that the function can be treated as such.

This warning was introduced to prevent accidentally using blocking functions, by having
to make a deliberate decision about whether or not to run the function in a thread pool.

The warning can be disabled globally by setting the environment variable
``LITESTAR_WARN_IMPLICIT_SYNC_TO_THREAD=0``.
