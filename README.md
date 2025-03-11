# Flare AI Kit

A framework for building verifiable AI agents on the Flare blockchain using Google Cloud Confidential Space.

## Overview

Flare AI Kit enables developers to create AI applications with cryptographic guarantees for data integrity, privacy, and provenance.
All computations run in Trusted Execution Environments (TEEs) that generate hardware-backed attestations verifiable on-chain.

## Modules

| **Module**                                                                           | **Description**                                                                                                                      |
| ------------------------------------------------------------------------------------ | ------------------------------------------------------------------------------------------------------------------------------------ |
| [flare-ai-social](https://github.com/flare-foundation/flare-ai-social)               | AI-driven content and sentiment analysis for Web3 social applications.                                                               |
| [flare-ai-rag](https://github.com/flare-foundation/flare-ai-rag)                     | Retrieval-Augmented Generation (RAG) module for blockchain knowledge agents.                                                         |
| [flare-ai-defai](https://github.com/flare-foundation/flare-ai-defai)                 | AI-powered DeFi automation interacting with Flare's DeFi ecosystem.                                                                  |
| [flare-ai-consensus](https://github.com/flare-foundation/flare-ai-consensus)         | Implementation of [Consensus Learning](https://dev.flare.network/pdf/whitepapers/20240225-ConsensusLearning.pdf) for multi-model AI. |
| [flare-vtpm-attestation](https://github.com/flare-foundation/flare-vtpm-attestation) | Solidity implementation of Confidential Space vTPM quote verification.                                                               |

Each module runs inside Confidential Space, with hardware-backed cryptographic attestations guaranteeing that AI computations are tamper-proof, verifiable, and secure

## Key Features

- **Verifiable AI**: Cryptographic proof validated and stored on the Flare blockchain.
- **Model Flexibility**: Support for 300+ LLMs including Google Gemini 2.0 for AI-driven blockchain automation.
- **Blockchain Native**: Seamless Flare blockchain integration with wallet support, token operations, and contract execution.
- **Composable Design**: Choose from DeFAI, RAG, Social, and Consensus AI agents or extend with custom logic.
- **Confidential**: Confidential execution protects sensitive input data.

## Getting Started

Clone the meta-repository with all submodules:

```bash
git clone --recursive https://github.com/flare-foundation/flare-ai-kit.git
```

## Contributing

Open an issue or start a discussion in our [GitHub repository](https://github.com/flare-foundation/flare-ai-kit).
