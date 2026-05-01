# 🧠 AI Workspace — Fullstack AI System with RAG & Agents

## 📌 Overview

AI Workspace is a fullstack application that combines conversational AI, document understanding, and autonomous task execution into a single platform. It allows users to chat with AI, upload and query documents, and run intelligent agents to automate workflows.

This project is designed to demonstrate production-level engineering skills using modern AI tooling, scalable backend architecture, and high-performance components.
---

## 🎯 Goals

- Build a **production-ready AI system**, not just a demo
- Showcase **fullstack engineering skills**
- Implement **Retrieval-Augmented Generation (RAG)**
- Design **agent-based workflows with tool usage**
- Integrate **high-performance components (Rust)**
- Deploy a **scalable, real-world application**

---

## 🧩 Core Features

### 💬 AI Chat

- Streaming responses (real-time token rendering)
- Context-aware conversations (memory)
- Multi-session chat history

### 📚 Document Intelligence (RAG)

- Upload PDFs, Markdown, CSV, and code
- Semantic search over documents
- Source-grounded answers

### 🤖 Agent Mode

- Multi-step task execution
- Tool usage (search, calculation, APIs)
- Example tasks:
* Summarize documents
* Research topics
* Generate structured outputs

### 🗂 Workspace System

- Project-based organization
- Isolated knowledge bases per workspace

---

## 🏗 Architecture

```
               ┌────────────────────────────┐
               │        Frontend            │
               │        (Nuxt 3)            │
               └───────────┬────────────────┘
                           │ HTTP / WS
               ┌───────────▼────────────────┐
               │     API Layer (Nuxt)       │
               │  (Server Routes / BFF)     │
               └───────────┬────────────────┘
                           │
               ┌───────────▼────────────┐
               │        Backend         │
               │       (FastAPI)        │
               ├───────────┬────────────┤
               │           │
       ┌───────▼────┐  ┌───▼───────────┐
       │ LangChain  │  │  Task Queue   │
       │ Pipelines  │  │  (Workers)    │
       └───────┬────┘  └────┬──────────┘
               │              │
       ┌───────▼──────────────▼──────┐
       │       Vector Database       │
       │   (FAISS / Pinecone)        │
       └─────────────────────────────┘

       ┌─────────────────────────────┐
       │   Rust Microservice         │
       │ (Parsing / Chunking /       │
       │  Embedding Preprocess)      │
       └─────────────────────────────┘

```
---

## 🧰 Tech Stack

### Frontend (Vue Ecosystem)

- Vue 3
- Nuxt 3 (SSR + server routes)
- TypeScript
- TailwindCSS
- Pinia (state management)

### Backend

- Python (FastAPI)
- LangChain (LLM orchestration)
- Pydantic (data validation)

### AI / Data

- OpenAI API or local LLMs
- Embeddings (OpenAI / Sentence Transformers)
- Vector DB: FAISS / Pinecone / Weaviate

### Systems

- PostgreSQL (metadata storage)
- Redis (caching + queues)
- Celery / RQ (background jobs)

### Performance Layer

- Rust microservice
- Fast document parsing
- Chunking optimization
- Preprocessing pipelines

### DevOps

- Docker & Docker Compose
- Vercel / Node hosting (Nuxt)
- AWS / GCP (backend)
- Nginx (optional reverse proxy)
---

## 📁 Project Structure

```
ai-workspace/
│
├── apps/
│   ├── web/                 # Nuxt 3 frontend + server routes (BFF)
│   └── api/                 # FastAPI backend
│
├── services/
│   ├── rag/                 # RAG pipelines
│   ├── agents/              # Agent orchestration
│   ├── ingestion/           # File processing
│   └── tools/               # External integrations
│
├── rust/
│   └── parser/              # Rust microservice
│
├── infrastructure/
│   ├── docker/
│   └── terraform/           # (optional)
│
├── scripts/
│   ├── seed_data.py
│   └── evals.py
│
├── docs/
│   ├── architecture.md
│   └── api.md
│
├── .env.example
├── docker-compose.yml
└── README.md
```
---

## ⚙️ Development Setup

### 1. Clone Repository

```bash
git clone https://github.com/dimastriann/ai-workspace.git
cd ai-workspace
```
---

### 2. Environment Variables

```bash
cp .env.example .env
```

```env
OPENAI_API_KEY=
DATABASE_URL=
REDIS_URL=
```
---

### 3. Run with Docker (Recommended)

```bash
docker-compose up --build
```
---

### 4. Manual Setup

#### Frontend (Nuxt)

```bash
cd apps/web
npm install
npm run dev
```

#### Backend (FastAPI)

```bash
cd apps/api
pip install -r requirements.txt
uvicorn main:app --reload
```

#### Rust Service

```bash
cd rust/parser
cargo run
```
---

## 🔄 Key Workflows

### 📥 Document Ingestion

1. Upload file (via Nuxt frontend)
2. Send to FastAPI backend
3. Parse using Rust service
4. Chunk text
5. Generate embeddings
6. Store in vector DB
---

### 🔍 Query (RAG)

1. User sends query
2. Nuxt server route (BFF) forwards request
3. Backend embeds query
4. Retrieve relevant chunks
5. Pass context to LLM
6. Stream response back to UI
---

### 🤖 Agent Execution

1. User submits task
2. Backend agent plans steps
3. Selects tools dynamically
4. Executes multi-step workflow
5. Streams result to frontend
---

## 🌐 Nuxt Server (BFF Layer)

Nuxt acts as a **Backend-for-Frontend (BFF)** layer:
- Handles API proxying
- Manages auth (future)
- Streams LLM responses
- Reduces direct exposure of backend services
Example structure:
```
apps/web/server/api/
├── chat.ts
├── rag.ts
└── agent.ts
```
---

## 🚀 Deployment

### Frontend (Nuxt)

- Deploy on Vercel or Node hosting

```bash
npm run build
npm run start
```
---

### Backend (FastAPI)

```bash
docker build -t ai-workspace-api .
```

Deploy to:

- AWS ECS / EC2
- GCP Cloud Run
---

### Database & Cache

- PostgreSQL (RDS / Supabase)
- Redis (Upstash / Elasticache)
---

### Environment Setup

- Use secrets manager
- Never commit `.env`
---

## 📊 Observability (Recommended)

- Logging: structured logs
- Monitoring: Prometheus / Grafana
- Error tracking: Sentry
---

## 🧪 Testing

### Frontend

```bash
npm run test
```

### Backend

```bash
pytest
```
---

## 🔐 Security Considerations

- API rate limiting
- Input validation
- Secure file uploads
- Auth (JWT / OAuth planned)
---

## 🧭 Roadmap

### Phase 1

- Chat + RAG MVP
- Basic UI (Nuxt)
- File upload

### Phase 2

- Agent workflows
- Background jobs
- Streaming improvements

### Phase 3

- Multi-user support
- Collaboration features
- Analytics dashboard
---

## 💡 Future Improvements

- Plugin system for tools
- Fine-tuned models
- Evaluation framework
- Multi-modal support (image/audio)
---

## 📣 Portfolio Positioning

This project demonstrates:
- Fullstack system design (Vue + Python + Rust)
- LLM application architecture
- BFF pattern using Nuxt
- Performance optimization with Rust
- Real-world AI product thinking
---

## 📄 License

MIT License
---

## 🙌 Acknowledgements

- LangChain ecosystem
- OpenAI APIs
- Open-source vector databases
---

## 📬 Contact

Email: [dimastriannugraha@gmail.com](mailto:[dimastriannugraha@gmail.com])

GitHub: https://github.com/dimastriann

---
