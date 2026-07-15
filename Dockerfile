FROM node:24.13.1-bookworm-slim@sha256:a81a03dd965b4052269a57fac857004022b522a4bf06e7a739e25e18bce45af2 AS builder

ENV COREPACK_ENABLE_DOWNLOAD_PROMPT=0
WORKDIR /src

RUN apt-get update \
    && apt-get install --no-install-recommends -y ca-certificates g++ make python3 \
    && rm -rf /var/lib/apt/lists/* \
    && corepack enable \
    && corepack prepare pnpm@10.24.0 --activate

COPY . .
RUN pnpm install --frozen-lockfile \
    && pnpm run build \
    && pnpm --config.allowUnusedPatches=true --filter t3 deploy --prod --legacy /out/t3

FROM node:24.13.1-bookworm-slim@sha256:a81a03dd965b4052269a57fac857004022b522a4bf06e7a739e25e18bce45af2 AS runtime

ARG HERMES_VERSION=0.18.2

ENV DEBIAN_FRONTEND=noninteractive \
    HERMES_HOME=/state/hermes \
    HOME=/state/home \
    PATH=/opt/hermes/bin:/usr/local/bin:/usr/bin:/bin \
    T3CODE_HOME=/state/t3 \
    T3_SUPPRESS_PAIRING_LOG=1

RUN apt-get update \
    && apt-get upgrade -y \
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
    && /opt/hermes/bin/pip install --no-cache-dir --upgrade \
       "cryptography==49.0.0" \
       "setuptools==83.0.0" \
    && ln -s /opt/hermes/bin/hermes /usr/local/bin/hermes \
    && /opt/hermes/bin/hermes acp --version \
    && /opt/hermes/bin/hermes acp --check \
    && rm -rf \
       /opt/yarn-* \
       /usr/local/lib/node_modules \
       /usr/local/bin/corepack \
       /usr/local/bin/npm \
       /usr/local/bin/npx \
       /usr/local/bin/yarn \
       /usr/local/bin/yarnpkg \
    && rm -rf /var/lib/apt/lists/*

RUN getent group 100 >/dev/null \
    && printf 't3:x:99:100:T3 Code:/state/home:/bin/bash\n' >> /etc/passwd

WORKDIR /app
COPY --from=builder --chown=99:100 /out/t3 /app

RUN mkdir -p /state/hermes /state/home /state/t3 /workspace \
    && chown -R 99:100 /state /workspace

USER 99:100

EXPOSE 3773

ENTRYPOINT ["node", "/app/dist/bin.mjs"]
CMD ["start", "--mode", "web", "--host", "127.0.0.1", "--port", "3773", "--no-browser", "/workspace/homelab-infra"]
