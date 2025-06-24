# Flare AI Kit

SDK for building **verifiable AI Agents** on Flare using Confidential Space.

> [!WARNING]
>
> Flare AI Kit is currently under active development (pre-release/alpha stage).
>
> Interfaces, APIs, and functionalities may change frequently and potentially in backward-incompatible ways before a stable release.
> Use with caution.

## ✨ Features

- **Verifiable Execution:** Run agent logic in a hardware-isolated Trusted Execution Environment (Confidential Space TDX TEEs).
- **Consensus Engine:** Framework for multi-agent collaboration based on the [Consensus Learning](https://arxiv.org/abs/2402.16157) whitepaper.
- **Agent Framework:** Build type-safe agents (PydanticAI) that interact with 200+ LLMs (Gemini, GPT etc.).
- **Flare Integration:** Connect to core protocols ([FTSO](https://dev.flare.network/ftso/overview), [FDC](https://dev.flare.network/fdc/overview), [FAssets](https://dev.flare.network/fassets/overview)) and dApps ([Sceptre](http://sceptre.fi), [SparkDEX](https://sparkdex.ai), [Kinetic](https://kinetic.market) etc.).
- **Social Intelligence:** Connectors & analytics for X, Telegram, and Farcaster.

## 🏗️ Architecture

The kit is composed of modular engines for agents, social feeds, onchain data, and consensus.

```mermaid
graph TD
    A(Flare AI Kit)
    A --> B{Agent Framework - PydanticAI}
    A --> C{VectorRAG Engine - PostgreSQL + pgvector}
    A --> D{GraphRAG Engine - Neo4j}
    A --> E{Secure Enclave - Confidential Space + TDX}
    A --> F{Ecosystem Engine}
    A --> G{Social Engine}
    A --> H{Consensus Engine}

    B --> I(Gemini, GPT, Grok +200 models)

    C --o DevHub/News/Governance

    D --o MainnetTxData

    E --> vTPM
    vTPM --o RA-TLS

    F --o M(Protocols)
    M --o FTSO
    M --o FDC
    M --o FAssets

    F --o L(Applications)
    L --o OpenOcean
    L --o Kinetic
    L --o SparkDEX
    L --o Cyclo
    L --o ...
```

## 📦 Getting Started

**Prerequisites** Python >= 3.12 and [uv](https://github.com/astral-sh/uv).

1. **Clone the repo:**

   ```bash
   git clone --recursive https://github.com/flare-foundation/flare-ai-kit.git
   cd flare-ai-kit
   ```

2. **Configure your environment:**

   ```bash
   # Copy the template and add your models, API keys etc.
   cp .env.example .env
   ```

3. **Install dependencies:**

   ```bash
   uv sync --all-extras
   ```

## ✅ Development Checks

Run the following commands to format, lint, type-check, and test your code before committing.

```bash
# Format, lint, and auto-fix
uv run ruff format
uv run ruff check --fix

# Run static type checking
uv run pyright

# Run tests
uv run pytest
```

## ☁️ Deploy to Confidential Space

**Prerequisites:** Authenticated [gcloud CLI](https://cloud.google.com/sdk/docs/install).

1. **Configure GCP:** Set all `GCP__*` variables in your `.env` file.

2. **Deploy:**

   ```bash
   chmod +x gcloud-deploy.sh
   ./gcloud-deploy.sh
   ```

## 🤝 Contributing

Contributions are highly encouraged! Please review the [CONTRIBUTING.md](CONTRIBUTING.md) guide for details on code style (Conventional Commits, Strict Typing), testing, and the PR process.

## 📜 License

This project is open-source and licensed under the Apache License 2.0. See [LICENSE](LICENSE) file.
