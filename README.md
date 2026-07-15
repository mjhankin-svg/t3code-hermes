# T3 Code: Hermes ACP Edition

This deployment-focused fork of [T3 Code](https://github.com/pingdotgg/t3code) uses
[Hermes Agent](https://github.com/NousResearch/hermes-agent) as its only provider.
T3 communicates with `hermes acp` over the standard ACP subprocess transport;
Hermes owns provider authentication, model routing, permissions, and delegation.

## Installation

> [!WARNING]
> This fork is intended for the provided container image. It expects a dedicated
> writable `HERMES_HOME`, managed Hermes configuration/authentication, and a
> workspace mounted at `/workspace`. T3 never receives an OpenAI API key.

### Container

```bash
docker build -t t3code-hermes .
docker run --rm --user 99:100 t3code-hermes --version
docker run --rm --entrypoint /opt/hermes/bin/hermes t3code-hermes acp --check
```

## Some notes

We are very very early in this project. Expect bugs.

We are not accepting contributions yet.

There's no public docs site yet, checkout the miscellaneous markdown files in [docs](./docs).

## Documentation

- [Getting started](./docs/getting-started/quick-start.md)
- [Architecture overview](./docs/architecture/overview.md)
- [Provider guides](./docs/providers/codex.md)
- [Operations](./docs/operations/ci.md)
- [Reference](./docs/reference/encyclopedia.md)

## If you REALLY want to contribute still.... read this first

### Install `vp`

T3 Code uses Vite+ so you'll need to install the global `vp` command-line tool.

#### macOS / Linux

```bash
curl -fsSL https://vite.plus | bash
```

#### Windows

```bash
irm https://vite.plus/ps1 | iex
```

Checkout their getting started guide for more information: https://viteplus.dev/guide/

### Install dependencies

```bash
vp i
```

Read [CONTRIBUTING.md](./CONTRIBUTING.md) before opening an issue or PR.

Need support? Join the [Discord](https://discord.gg/jn4EGJjrvv).
