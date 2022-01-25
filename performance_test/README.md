# Performance Tests

This is an API performance test comparing [Starlite](https://github.com/starlite-api/starlite), 
[Starlette](https://github.com/encode/starlette) and [FastAPI](https://github.com/tiangolo/fastapi) using
the [autocannon](https://github.com/mcollina/autocannon) stress testing tool.

## Test Setup

Setup is identical for all frameworks.

- The applications are in the folders with their names - `/starlite`, `/starlette` and `/fastapi`.
- There are no DB querying tests because all three frameworks are DB agnostic and as such this has no value in itself.
- Each endpoint is tested X number of times (default 5) for 5 seconds each time. Each test run uses 4 workers and 25
  connections per worker.

## Executing Tests Locally

To execute the tests:

Run `./test.sh` or `./test.sh <iterations>`.

- Default number of test iterations is 5.

The test.sh script will create a virtual environment and install the dependencies for you.

note: the repository is set to use python 3.10+ so make sure to have it available in your environment.