# KGraph: Knowledge Graph Search & Recommendation Platform

KGraph is a full-stack search and recommendation engine designed to discover software projects and developers. It combines structured graph queries on a **Neo4j Knowledge Graph** with unstructured natural language capabilities using a **Local LLM Chatbot** enhanced by **Semantic Vector Search RAG** (ChromaDB + Ollama).

---

## Architecture Overview

```
              ┌────────────────────────────────────────┐
              │           Browser Frontend             │
              │         (React / TailwindCSS)          │
              └──────────────────┬─────────────────────┘
                                 │ HTTP (Port 5173)
                                 ▼
              ┌────────────────────────────────────────┐
              │             FastAPI Backend            │
              └──────┬──────────────────────────┬──────┘
                     │                          │
                     │ Bolt (Port 7687)         │ HTTP (Port 11434)
                     ▼                          ▼
        ┌────────────────────────┐  ┌────────────────────────┐
        │      Neo4j Graph       │  │       Ollama API       │
        │    (Database Node)     │  │     (Host Machine)     │
        └────────────────────────┘  └───────────┬────────────┘
                                                │
                                    ┌───────────┴────────────┐
                                    │  ChromaDB Vector Store │
                                    │ (In-process SQLite/Lib)│
                                    └────────────────────────┘
```

- **Database**: Neo4j stores entities (Projects, Developers, Domains, Technologies, Locations) and their relationships.
- **Vector Search**: ChromaDB stores semantic embeddings generated via `nomic-embed-text` to enable semantic similarity searches on raw project logs/CSV files.
- **LLM Engine**: Ollama hosts `llama3.2:1b` on the host system to synthesize contextual responses from RAG-retrieved database entries.

---

## Deployment & Setup

This application is designed to run in a hybrid container/host topology. The frontend, backend, and graph database are containerized, while Ollama runs directly on the host to leverage system GPU resources.

### 1. Prerequisites
- Docker & Docker Compose
- [Ollama](https://ollama.com/) installed on your host system

### 2. Configure Host Ollama for Docker Access
By default, Ollama binds only to localhost. To allow the Docker containerized backend to communicate with it, configure Ollama to listen on all interfaces:

#### For Linux (systemd):
1. Create a systemd override directory:
   ```bash
   sudo mkdir -p /etc/systemd/system/ollama.service.d
   ```
2. Configure the host environment variable:
   ```bash
   printf '[Service]\nEnvironment="OLLAMA_HOST=0.0.0.0:11434"\n' | sudo tee /etc/systemd/system/ollama.service.d/override.conf
   ```
3. Reload daemon and restart service:
   ```bash
   sudo systemctl daemon-reload
   ```

### 3. Pull Required Models
Ensure the embedding model and LLM chat model are downloaded:
```bash
# Chat generation model
ollama pull llama3.2:1b

# Embedding generation model (for ChromaDB RAG context)
ollama pull nomic-embed-text
```

### 4. Build and Start the Application
Initialize the Docker Compose stack from the repository root:
```bash
docker compose up -d --build
```
*Note: On initial startup, the backend automatically embeds and indexes the CSV data source using ChromaDB. This process takes ~60-90 seconds. Subsequent starts are near-instant.*

### 5. Seed the Graph Database
Once containers are running and healthy, seed the Neo4j Knowledge Graph:
```bash
curl -X POST http://localhost:8000/api/seed
```

---

## Environment Variables (`.env`)

A default configuration is set up in `docker-compose.yml`. You may customize these settings in a root `.env` file:

```env
# Neo4j Graph Settings
NEO4J_URI=bolt://localhost:7687
NEO4J_USER=neo4j
NEO4J_PASSWORD=recommend_neo4j_2024
NEO4J_DATABASE=neo4j

# Backend Settings
BACKEND_HOST=0.0.0.0
BACKEND_PORT=8000
CORS_ORIGINS=http://localhost:3000,http://localhost:5173

# NLP Search Parser Selection (Options: rule | gemini | openai)
QUERY_PARSER=rule
GEMINI_API_KEY=
OPENAI_API_KEY=
```

---
## Review section
Review section has been added to evaluate the response of local llm ai and on the basis of it show a final culmination of 
reviews whether they were useful or not.

1. Useful Review- these contain data of query and response
   || Query | Response | Mode | Time ||
2. Not Useful Review - these contain data of query , response and reason
   ||Query | Response | user Note | Mode | Time ||

## Graph connection chain and shotest distance

1. implemented the connection between 2 random nodes based on their adjacent nods
2. Managed the depth of connection to a limited range to avoid excessive computation (2 to 6)
3. used Dijkstra algo to find shortest path
4. provided weights to the mentioned edges
5. A monitor board to monitor each node contribution


## API Reference Summary

| Method | Endpoint | Description |
| :--- | :--- | :--- |
| **POST** | `/api/search` | Performs natural language parsing and returns scored matching entities |
| **POST** | `/api/chat` | Chat Assistant (accepts `mode: "llm"` or `"rag"` request payload) |
| **GET** | `/api/projects` | Query software projects with optional technology/domain filters |
| **GET** | `/api/projects/{name}` | Fetch detailed properties for a project |
| **GET** | `/api/projects/{name}/recommendations` | Generate similar projects and developers via graph path analysis |
| **GET** | `/api/developers` | Query developers with optional tech stack filters |
| **GET** | `/api/developers/{name}` | Fetch developer details |
| **GET** | `/api/graph` | Returns nodes and edges dataset format for force-directed rendering and shortest path too |
| **POST** | `/api/seed` | Triggers a fresh seed of the graph database |
