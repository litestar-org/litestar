Docker
===========

This uses the default python container https://hub.docker.com/_/python

Dockerfile
-----------

.. code-block:: docker

    FROM python:3.12
    WORKDIR /code
    COPY ./requirements.txt /code/requirements.txt
    RUN pip install --no-cache-dir --upgrade -r /code/requirements.txt
    COPY ./src /
    CMD ["uvicorn", "app:app", "--host", "0.0.0.0", "--port", "80"]


This copies the `src` folder on your machine to the `/code` in the docker container and runs your app via uvicorn. Adjust according to whichever asgi server you choose.

:doc:`manually-with-asgi-server`


Docker-compose
---------------

If you want to run the container as part of a docker-compose setup then you can simply use this compose file

.. code-block:: yaml

    services:
      api:
        build:
          context: ./
          dockerfile: Dockerfile
        container_name: "api"
        depends_on:
          - database
        ports:
          - "80:80"
