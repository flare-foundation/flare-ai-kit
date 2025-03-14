# Flare AI Kit

SDK for building verifiable AI Agents on Flare using Confidential Space.

## Overview

Flare AI Kit enables developers to create AI applications with cryptographic guarantees for data integrity, privacy, and provenance.
All computations run in Trusted Execution Environments (TEEs) that generate hardware-backed attestations verifiable on-chain.

## Modules

| **Module**                                                                           | **Description**                                                                                                                                      |
| ------------------------------------------------------------------------------------ | ---------------------------------------------------------------------------------------------------------------------------------------------------- |
| [flare-ai-social](https://github.com/flare-foundation/flare-ai-social)               | AI-powered integration with social platforms (X, Telegram) enabling verifiable content analysis and automated interactions in Web3 social contexts.  |
| [flare-ai-rag](https://github.com/flare-foundation/flare-ai-rag)                     | Knowledge retrieval system combining blockchain data with LLMs to provide verifiable, attestable answers to complex blockchain queries.              |
| [flare-ai-defai](https://github.com/flare-foundation/flare-ai-defai)                 | Secure, automated DeFi strategy execution with verifiable AI decision-making for portfolio management, risk assessment, and yield optimization.      |
| [flare-ai-consensus](https://github.com/flare-foundation/flare-ai-consensus)         | Novel approach to AI using [Consensus Learning](https://arxiv.org/abs/2402.16157) for more reliable, transparent multi-model predictions.            |
| [flare-vtpm-attestation](https://github.com/flare-foundation/flare-vtpm-attestation) | On-chain verification of Confidential Space attestations, enabling trustless validation that AI computations were executed on tamper-proof hardware. |

Each `flare-ai-*` module runs inside Confidential Space.

## Key Features

- **Verifiable Attestations**: Cryptographic proofs from Confidential Space validated and stored on the Flare blockchain.
- **Blockchain Native**: Seamless Flare blockchain integration with wallet support, token operations, and contract execution.
- **Model Flexibility**: Support for 300+ LLMs including Google Gemini 2.0 for AI-driven blockchain automation.
- **Composable Design**: Choose from DeFAI, RAG, Social, and Consensus AI agents or extend with custom logic.

## Getting Started

Clone the meta-repository with all submodules:

```bash
git clone --recursive https://github.com/flare-foundation/flare-ai-kit.git
```

Follow the README in each submodule to start building.

## Contributing

We actively welcome contributions - open an issue or start a discussion.
