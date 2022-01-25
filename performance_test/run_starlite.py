"""
This file is meant to allow executing the starlite application for profiling purposes.
It's not meant for performance testing because the uvicorn configuration here is suboptimal
"""

import uvicorn

from performance_test.starlite_app.main import app

if __name__ == "__main__":
    uvicorn.run(app, port=8001, host="0.0.0.0")
