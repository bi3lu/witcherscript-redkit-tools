# syntax=docker/dockerfile:1.7

ARG DOTNET_SDK_IMAGE=mcr.microsoft.com/dotnet/sdk:10.0
ARG UV_IMAGE=ghcr.io/astral-sh/uv:0.8.12

FROM ${UV_IMAGE} AS uv

FROM ${DOTNET_SDK_IMAGE} AS dev

ENV DOTNET_CLI_TELEMETRY_OPTOUT=1 \
    DOTNET_NOLOGO=1 \
    NUGET_XMLDOC_MODE=skip \
    PYTHONUNBUFFERED=1 \
    UV_LINK_MODE=copy \
    UV_PROJECT_ENVIRONMENT=/workspace/.venv \
    UV_PYTHON=/usr/bin/python3.12 \
    UV_PYTHON_DOWNLOADS=never \
    PATH="/workspace/.venv/bin:${PATH}"

RUN apt-get update \
    && apt-get install -y --no-install-recommends \
        bash \
        ca-certificates \
        curl \
        git \
        make \
        python3.12 \
        python3.12-venv \
    && rm -rf /var/lib/apt/lists/*

COPY --from=uv /uv /uvx /usr/local/bin/

WORKDIR /workspace

COPY README.md LICENSE Makefile global.json pyproject.toml uv.lock ./
COPY src/py ./src/py
COPY tests/py ./tests/py

RUN --mount=type=cache,target=/root/.cache/uv \
    uv sync --all-extras --dev --frozen

COPY src/dotnet ./src/dotnet

RUN --mount=type=cache,target=/root/.nuget/packages \
    dotnet restore src/dotnet/WitcherScript.RedkitTooling.sln

COPY . .

CMD ["/bin/bash"]
