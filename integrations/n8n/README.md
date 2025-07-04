# Flare AI Kit ↔ n8n Integration

This integration connects the [Flare AI Kit](https://github.com/flare-foundation) to [n8n](https://n8n.io), a powerful open-source workflow automation platform. It allows users to build low-code/no-code automation workflows that interact with blockchain, AI, and external APIs using a visual interface.

---

## 🚀 Overview

This project provides:

1. A **FastAPI microservice** that wraps key functionality from the Flare AI Kit and exposes it as RESTful API endpoints.
2. **Custom n8n nodes** that interact with the FastAPI wrapper, allowing you to use Flare AI Kit features inside the n8n editor.

---

## 📦 Features

### ✅ FastAPI Service

The FastAPI wrapper exposes the following endpoints:

| Endpoint              | Method | Description                               |
| --------------------- | ------ | ----------------------------------------- |
| `/`                   | GET    | Health check                              |
| `/ftso/price`         | GET    | Get the current price of a token via FTSO |
| `/semantic-search`    | POST   | Perform semantic search via RAG retriever |
| `/consensus-learning` | POST   | Perform consensus learning task           |
| `/post-message`       | POST   | Post a message to Twitter or Telegram     |
| `/send-tx`            | POST   | Submit a basic on-chain transaction       |

Each endpoint wraps SDK calls and returns structured JSON responses.

### ✅ n8n Custom Nodes

Implemented custom nodes include:

- `FlareFtsoPrice` – fetches FTSO price data
- `FlareSemanticSearch` – queries vector-based knowledge search
- `FlareConsensusLearning` – performs consensus-based model inference
- `FlarePostMessage` – posts updates to social media (Twitter/Telegram)
- `FlareSendTransaction` – submits blockchain transactions

Each node supports credentials and inputs as required by the FastAPI service.

---

## 🧪 Running the FastAPI Wrapper

### Prerequisites:

- Python 3.10+
- `poetry` or `pip`
- Docker (for containerized deployment)

### Development Setup:

```bash
cd integrations/n8n/fastapi_service
pip install -r requirements.txt
uvicorn main:app --reload
```

### Docker Setup:

```bash
docker build -t flare-fastapi .
docker run -d -p 8000:8000 flare-fastapi
```

---

## 🧩 Using the n8n Custom Nodes

### Step 1: Copy Node Files

Place your node files in the `~/.n8n/custom` directory or use a custom `n8n-nodes-<name>` plugin folder. Example:

```
integrations/n8n/custom_nodes/FlareAiKit/
  ├── FlareFtsoPrice.node.ts
  ├── FlareSemanticSearch.node.ts
  ├── credentials/
      ├── FlareFtsoApi.credentials.ts
      ├── FlareSemanticSearchApi.credentials.ts
      └── ...
```

### Step 2: Build

```bash
cd custom_nodes/FlareAiKit
npm install
npm run build
```

### Step 3: Add to n8n

Configure `package.json` and restart your `n8n` instance. Ensure the built files exist in the `dist/` folder.

---

## 🔐 Credentials

All APIs use Bearer token authentication. Credential classes are defined per endpoint and support `test` configuration to validate your API keys.

Each node maps to one of the credential types:

- `FlareFtsoApi`
- `FlareSemanticSearchApi`
- `FlareConsensusLearning`
- `FlarePostMessage`
- `FlareSendTransaction`

---

## 📚 Example Workflow

You can create a sample n8n workflow like:

1. Trigger (schedule or webhook)
2. `FlareFtsoPrice` node (fetch token price)
3. `FlarePostMessage` node (post price to Twitter)

Export it as a `.json` to reuse or share.

---

## 📖 Directory Structure

```
flare-ai-kit/
└── integrations/
    └── n8n/
        ├── fastapi_service/
        │   ├── main.py
        │   └── Dockerfile
        └── custom_nodes/
            └── FlareAiKit/
                ├── FlareFtsoPrice.node.ts
                ├── FlareSemanticSearch.node.ts
                └── credentials/
```

---

## 🧪 Testing

Run unit tests for FastAPI with:

```bash
pytest
```

And test your n8n nodes inside the n8n UI editor.

---

## 📌 Notes

- The FastAPI service is designed to be lightweight and stateless.
- Endpoints are modular; additional features from Flare SDK can be exposed as needed.
- For production use, deploy the FastAPI container behind HTTPS and protect API tokens securely.

---

## 🙌 Credits

Powered by Flare AI Kit and n8n.

---
