# Flare AI Kit

SDK for building verifiable AI Agents on Flare using Confidential Space.

Flare AI Kit enables developers to create AI applications with cryptographic guarantees for data integrity, privacy, and provenance.
All computations run in Trusted Execution Environments (TEEs) that generate hardware-backed attestations verifiable on Flare.

## Goals & Features

* **Verifiable Agent Operations:** Execute agent logic within Confidential Space using Intel TDX TEEs.
* **Agent Framework:** Build robust agents using PydanticAI for type validation and structured interaction with Large Language Models (LLMs) like Google Gemini.
* **Flare Ecosystem Integration:** Connect directly to Flare's core protocols (FTSO, FDC/State Connector, FAssets) and major ecosystem applications (e.g., Sceptre, SparkDEX, OpenOcean).
* **Retrieval-Augmented Generation (RAG):**
    * **VectorRAG:** Index and query unstructured Flare data (docs, news, governance) using Qdrant or pgvector.
    * **GraphRAG:** Index and query structured Flare blockchain transaction data using Neo4j.
* **Social Intelligence:** Connectors for platforms like X, Discord, Telegram, Farcaster with analytics capabilities (optional dependency).
* **Consensus Engine:** Support for multi-agent collaboration to improve decision robustness.

## Architecture Overview

The SDK is built with a modular architecture:

* **Agent Framework:** Core agent logic, LLM interaction (PydanticAI).
* **Ecosystem Engine:** Handles connections to Flare protocols and dApps.
* **RAG Engines:** Vector and Graph databases & query interfaces.
* **Social Engine:** Social platform connectors and analysis tools.
* **Consensus Engine:** Multi-agent coordination.
* **Security Helpers:** Utilities for working with TEEs / Confidential Space.

## Getting Started

1. Clone the repository:

    ```bash
    git clone https://github.com/flare-foundation/flare-ai-kit.git
    ```

2. Setup configuration:


For onchain TEE verification 

```bash
git clone --recursive https://github.com/flare-foundation/flare-ai-kit.git
```



## Contributing

We actively welcome contributions - open an issue or start a discussion.
