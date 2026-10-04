FROM mcr.microsoft.com/devcontainers/python:1-3.10-bookworm

ARG NODE_VERSION=18

USER root

RUN apt-get update \
    && apt-get install -y --no-install-recommends \
        git curl wget mariadb-client redis-tools build-essential \
        libffi-dev libssl-dev libmariadb-dev pkg-config \
    && curl -fsSL https://deb.nodesource.com/setup_${NODE_VERSION}.x | bash - \
    && apt-get install -y --no-install-recommends nodejs \
    && npm install -g yarn \
    && rm -rf /var/lib/apt/lists/*

RUN python -m pip install --no-cache-dir "frappe-bench>=5,<6"

USER vscode
WORKDIR /workspaces/flexirule
