ARG PYTHON_VERSION=3.14.3-slim-trixie
ARG PORT=8085
ARG PORT_DEBUG=8086

FROM python:${PYTHON_VERSION} AS base

ENV PATH="/home/nonroot/.local/bin:/home/nonroot/.venv/bin:${PATH}"
ENV PYTHONUNBUFFERED=1
ENV UV_PYTHON_DOWNLOADS=0
ENV UV_MANAGED_PYTHON=0

RUN python -m pip install --upgrade --force-reinstall pip

RUN addgroup --gid 1000 nonroot \
    && adduser nonroot \
        --uid 1000 \
        --gid 1000 \
        --home /home/nonroot \
        --shell /bin/bash

RUN apt update && \
    apt install -y --no-install-recommends curl && \
    rm -rf /var/lib/apt/lists/*

USER nonroot
WORKDIR /home/nonroot

ENTRYPOINT [ "python" ]

FROM base AS development

ENV PYTHONDONTWRITEBYTECODE=1
ENV LOG_CONFIG="logging-dev.json"

RUN pip install uv debugpy

ARG PORT=8085
ARG PORT_DEBUG=8086
ENV PORT=${PORT}
EXPOSE ${PORT} ${PORT_DEBUG}

COPY --chown=nonroot:nonroot pyproject.toml .
COPY --chown=nonroot:nonroot README.md .
COPY --chown=nonroot:nonroot uv.lock .
COPY --chown=nonroot:nonroot app/ ./app/

RUN --mount=type=cache,target=/home/nonroot/.cache/uv,uid=1000,gid=1000 \
    uv sync --locked --link-mode=copy

COPY --chown=nonroot:nonroot logging-dev.json .

ENTRYPOINT [ "mural-mcp-http"]

FROM base AS production

ENV LOG_CONFIG="logging.json"

USER root

RUN apt update && \
    apt install -y --no-install-recommends curl && \
    rm -rf /var/lib/apt/lists/*

USER nonroot

COPY --from=development /home/nonroot/pyproject.toml .
COPY --chown=nonroot:nonroot README.md .
COPY --from=development /home/nonroot/uv.lock .
COPY --from=development /home/nonroot/app ./app

COPY logging.json .

RUN --mount=type=cache,target=/home/nonroot/.cache/uv,uid=1000,gid=1000 \
    --mount=from=development,source=/home/nonroot/.local/bin/uv,target=/home/nonroot/.local/bin/uv \
    uv sync --locked --compile-bytecode --link-mode=copy --no-dev

ARG PORT=8085
ENV PORT=${PORT}
EXPOSE ${PORT}

ENTRYPOINT [ "mural-mcp-http" ]
