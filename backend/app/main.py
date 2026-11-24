"""
 FastAPI Backend
"""
import logging
import logging.config
from contextlib import asynccontextmanager


from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse

from app.core.config import settings
from app.core.database import neo4j_driver
from app.services.vector_index_service import vector_index
from app.services.chat_rag_service import chat_rag_service
from app.api import search, projects, developers, graph, seed, chat,feedback


# --- Logging Setup ---
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
    datefmt="%Y-%m-%d %H:%M:%S",
)
logger = logging.getLogger(__name__)


# --- Lifecycle ---

@asynccontextmanager
async def lifespan(app: FastAPI):
    """Manage application lifecycle - connect/disconnect Neo4j and build vector index."""
    logger.info("🚀 Starting Knowledge Graph Recommendation Platform...")

    # ── Neo4j ─────────────────────────────────────────────────────────────────
    try:
        neo4j_driver.connect()
    except Exception as e:
        logger.error(f"  Failed to connect to Neo4j on startup: {e}")
        logger.warning("Server will start but database operations will fail until Neo4j is ready.")

    # ── Vector Index (ChromaDB + nomic-embed-text) ────────────────────────────
    try:
        logger.info("🔍 Building semantic vector index for chat RAG...")
        await vector_index.build_index()
        logger.info(" Vector index ready.")
    except Exception as e:
        logger.warning(
            f" Vector index build failed: {e}. "
            "Chat will return empty context until the index is ready. "
            "Ensure Ollama is running and 'nomic-embed-text' is pulled."
        )

    # ── LLM Warm-up (loads model into Ollama memory to avoid cold-start timeout) ──
    try:
        logger.info("🔥 Warming up local LLM — loading model into Ollama memory...")
        await chat_rag_service.warmup_llm()
    except Exception as e:
        logger.warning(f"⚠️  LLM warm-up skipped: {e}")

    yield

    logger.info("🛑 Shutting down...")
    neo4j_driver.close()


# --- App ---

app = FastAPI(
    title="Knowledge Graph Recommendation Platform",
    description=(
        "Semantic search and recommendation engine powered by a Neo4j Knowledge Graph.\n\n"
        "## Features\n"
        "- **Natural Language Search** — Parse free-text queries into structured Cypher filters\n"
        "- **Graph Recommendations** — Surface similar projects/developers via shared tech, domain, location\n"
        "- **Graph Visualization** — Full and subgraph data for force-directed rendering\n"
        "- **Autocomplete Suggestions** — Real-time search suggestions across all entity types\n"
    ),
    version="2.0.0",
    lifespan=lifespan,
    docs_url="/docs",
    redoc_url="/redoc",
)


# --- Middleware ---

app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origins_list,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


# Global exception handler for unhandled errors
@app.exception_handler(Exception)
async def global_exception_handler(request: Request, exc: Exception):
    logger.error(f"Unhandled exception on {request.method} {request.url}: {exc}", exc_info=True)
    return JSONResponse(
        status_code=500,
        content={"detail": "An internal server error occurred.", "code": "INTERNAL_ERROR"},
    )


# --- Routers ---

app.include_router(search.router, prefix="/api", tags=["Search"])
app.include_router(projects.router, prefix="/api", tags=["Projects"])
app.include_router(developers.router, prefix="/api", tags=["Developers"])
app.include_router(graph.router, prefix="/api", tags=["Graph"])
app.include_router(seed.router, prefix="/api", tags=["Admin"])
app.include_router(chat.router, prefix="/api", tags=["Chat"])

app.include_router(feedback.router, prefix="/api", tags=["Feedback"])


# --- Root Endpoints ---

@app.get("/", tags=["Health"], summary="Root Health Check")
async def root():
    """Basic health check endpoint."""
    return {
        "status": "healthy",
        "service": "Knowledge Graph Recommendation Platform",
        "version": "2.0.0",
        "docs": "/docs",
    }


@app.get("/health", tags=["Health"], summary="Detailed Health Check")
async def health_check():
    """Detailed health check withNeo4j connectivity."""
    db_connected = neo4j_driver.verify_connectivity()
    db_stats = neo4j_driver.get_stats() if db_connected else {}

    total_nodes = sum(db_stats.get("nodes", {}).values())

    return {
        "status": "healthy" if db_connected else "degraded",
        "database": {
            "connected": db_connected,
            "uri": settings.neo4j_uri,
            "total_nodes": total_nodes,
            "is_seeded": total_nodes >= 8,
        },
        "version": "2.0.0",
    }
