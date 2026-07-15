FROM node:24.13.1-bookworm-slim AS builder

ENV COREPACK_ENABLE_DOWNLOAD_PROMPT=0
WORKDIR /src

RUN apt-get update \
    && apt-get install --no-install-recommends -y ca-certificates g++ make python3 \
    && rm -rf /var/lib/apt/lists/* \
    && corepack enable \
    && corepack prepare pnpm@10.24.0 --activate

COPY . .
RUN pnpm install --frozen-lockfile && pnpm run build

FROM node:24.13.1-bookworm-slim AS runtime

ARG HERMES_VERSION=0.18.2

ENV DEBIAN_FRONTEND=noninteractive \
    HERMES_HOME=/state/hermes \
    HOME=/state/home \
    PATH=/opt/hermes/bin:/usr/local/bin:/usr/bin:/bin \
    T3CODE_HOME=/state/t3 \
    T3_SUPPRESS_PAIRING_LOG=1

RUN apt-get update \
    && apt-get install --no-install-recommends -y \
       ca-certificates \
       curl \
       git \
       openssh-client \
       python3 \
       python3-pip \
       python3-venv \
    && python3 -m venv /opt/hermes \
    && /opt/hermes/bin/pip install --no-cache-dir "hermes-agent[acp]==${HERMES_VERSION}" \
    && /opt/hermes/bin/hermes acp --version \
    && /opt/hermes/bin/hermes acp --check \
    && rm -rf /var/lib/apt/lists/*

WORKDIR /app
COPY --from=builder --chown=99:100 /src /app

RUN mkdir -p /state/hermes /state/home /state/t3 /workspace \
    && chown -R 99:100 /state /workspace

USER 99:100

EXPOSE 3773

ENTRYPOINT ["node", "/app/apps/server/dist/bin.mjs"]
CMD ["start", "--mode", "web", "--host", "127.0.0.1", "--port", "3773", "--no-browser", "/workspace/homelab-infra"]
