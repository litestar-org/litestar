FROM ubuntu:22.04

ENV PYTHONHASHSEED=0 \
    PYTHONUNBUFFERED=1 \
    PYTHONIOENCODING=UTF-8 \
    TZ=Etc/UTC \
    PYTHON_VERSION=3.12 \
    REPO=litestar-org/litestar \
    TAG=latest \
    WORKSPACE=/litestar

ARG DEBIAN_FRONTEND=noninteractive
RUN apt-get update && apt-get install -y \
    build-essential \
    curl \
    git \
    wget \
    zlib1g-dev \
    libssl-dev \
    locales \
    tzdata \
    && rm -rf /var/lib/apt/lists/*

RUN echo "en_US.UTF-8 UTF-8" > /etc/locale.gen && locale-gen

RUN curl -LsSf https://astral.sh/uv/install.sh | env UV_UNMANAGED_INSTALL="/bin" sh

RUN useradd -ms /bin/bash runner

RUN mkdir -p ${WORKSPACE} && \
    chown -R runner:runner ${WORKSPACE} && \
    chmod -R u+rwX,go+rX,go-w ${WORKSPACE}

USER runner
WORKDIR ${WORKSPACE}

RUN uv python install -v ${PYTHON_VERSION}

RUN git clone --depth=1 "https://github.com/${REPO}.git" "${WORKSPACE}" && \
    cd "${WORKSPACE}" && \
    git checkout main

RUN uv venv -v && uv pip -v install . pytest
RUN uv pip -v install .

RUN uv run python -m pytest -v tests || true

ENV PATH="/litestar/.venv/bin:$PATH"

CMD ["bash"]

