# [Choice] Python version (use -bookworm or -bullseye variants on local arm64/Apple Silicon): 3, 3.13, 3.12, 3.11, 3.10, 3.9, 3.8, 3-bookworm, 3.13-bookworm, 3.12-bookworm, 3.11-bookworm, 3.10-bookworm, 3.9-bookworm, 3.8-bookworm, 3-bullseye, 3.11-bullseye, 3.10-bullseye, 3.9-bullseye, 3.8-bullseye, 3-buster, 3.11-buster, 3.10-buster, 3.9-buster, 3.8-buster
ARG VERSION=3.12
ARG VARIANT=-bookworm

FROM python:${VERSION}${VARIANT}

ENV UV_LOCKED=1 UV_PYTHON=${VERSION} PATH="/root/.local/bin/:$PATH"

# https://docs.astral.sh/uv/guides/integration/docker/#installing-uv
RUN apt-get update && export DEBIAN_FRONTEND=noninteractive \
    && apt-get purge -y fish \
    && apt-get install -y --no-install-recommends curl ca-certificates

ADD https://astral.sh/uv/install.sh /uv-installer.sh

RUN sh /uv-installer.sh && rm /uv-installer.sh

RUN python3 -m pip install --upgrade setuptools cython pip
