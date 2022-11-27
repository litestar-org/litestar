# Benchmarks

## Methodology
- Benchmarking is done using the [bomardier](https://github.com/codesenberg/bombardier) benchmarking tool.
- Benchmarks are run on a dedicated machine, with a base Debian 11 installation. 
- Each framework is contained within its own docker container, running on a dedicated CPU core (using the `cset shield` command the `--cpuset-cpus` option for docker)
- Tests for the frameworks are written to make them as comparable as possible while completing the same tasks (you can see them [here](https://github.com/starlite-api/api-performance-tests/tree/main/frameworks))
- Each application is run using [uvicorn](https://www.uvicorn.org/) with **one worker** and [uvloop](https://uvloop.readthedocs.io/)
- Test data has been randomly generated and is being imported from a shared module

### Test modes
Two different test modes are executed:

#### Requests per second
This is a full load tests, in which requests are sent to the server as fast as it can handle them.
This is done over a period for 60 seconds, after a warmup period of 5 seconds.

#### Latency under normal load
Latency is measured across 1000 requests, with a rate limit of 20 requests per second.


## Results

!!! info
    If a result is missing for a specific framework that means either

    - It does not support this functionality (this will be mentioned in the test description)
    - More than 0.1% of responses were dropped / erroneous

### JSON
Serializing a dictionary into JSON

![RPS JSON](./images/benchmarks/rps_json.svg)

??? info "Full series"
    ![RPS JSON](./images/benchmarks/results_all_p/rps_json.svg)


### Serialization
_(only supported by `Starlite` and `FastAPI`)_

![RPS serialization](./images/benchmarks/rps_serialization.svg)

??? info "Full series"
    ![RPS serialization](./images/benchmarks/results_all_p/rps_serialization.svg)


### Files
![RPS files](./images/benchmarks/rps_files.svg)

??? info "Full series"
    ![RPS files](./images/benchmarks/results_all_p/rps_files.svg)


### Path and query parameter handling
_All responses return "No Content"_

- No params: No path parameters
- Path params: Single path parameter, coerced into an integer
- Query params: Single query parameter, coerced into an integer
- Mixed params: A path and a query parameters, coerced into integers

![RPS path and query parameters](./images/benchmarks/rps_params.svg)

??? info "Full series"
    ![RPS files](./images/benchmarks/results_all_p/rps_files.svg)


### Dependency injection
<small>_(not supported by `Starlette`)_</small>

- Resolving 3 nested synchronous dependencies
- Resolving 3 nested asynchronous dependencies (only supported by `Starlite` and `FastAPI`)
- Resolving 3 nested synchronous, and 3 nested asynchronous dependencies (only supported by `Starlite` and `FastAPI`)

![RPS Dependency injection](./images/benchmarks/rps_dependency-injection.svg)

??? info "Full series"
    ![RPS Dependency injection](./images/benchmarks/results_all_p/rps_dependency-injection.svg)


### Modifying responses
_All responses return "No Content"_

![RPS dynamic responses](./images/benchmarks/rps_dynamic-response.svg)

??? info "Full series"
    ![RPS dynamic responses](./images/benchmarks/results_all_p/rps_dynamic-response.svg)


### Plaintext
![RPS Plaintext](./images/benchmarks/rps_plaintext.svg)

??? info "Full series"
    ![RPS dynamic responses](./images/benchmarks/results_all_p/rps_plaintext.svg)


## Interpreting the results
An interpretation of these results should be approached with caution, as is the case
for nearly all benchmarks. A high score in a test does not necessarily translate to
high performance of **your** application in **your** use case. For almost any test
you can probably write an app that performs better or worse at a comparable task 
**in your scenario**.

While trying to design the tests in a way that simulate somewhat realistic scenarios, 
they can never give an exact representation of how a real world application, where, 
aside from the workload, many other factors come into play. These tests were mainly written 
to be used internally for starlite development, to help us locate the source of some 
performance regression we were experiencing.

If you're interested in a good read about the general value and inherent weaknesses
of framework benchmark, I suggest [this article](https://blog.miguelgrinberg.com/post/ignore-all-web-performance-benchmarks-including-this-one)
by Miguel Grinberg.

