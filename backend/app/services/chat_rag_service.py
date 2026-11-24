"""
Chat RAG Service for KGraph.

Uses semantic vector search (ChromaDB + nomic-embed-text via Ollama)
to retrieve the most relevant software records from the knowledge base,
then passes them as grounded context to the local LLM (llama3.2).

Replaces the previous naive CSV keyword-matching approach.
"""

import os
import logging
import httpx
from typing import List, Dict, Any

from app.models.chat import ChatRequest, ChatResponse, ChatMessage
from app.services.vector_index_service import vector_index

logger = logging.getLogger(__name__)

OLLAMA_URL  = os.getenv("OLLAMA_URL",   "http://localhost:11434")
MODEL_NAME  = os.getenv("OLLAMA_MODEL", "llama3.2:1b")
OLLAMA_TIMEOUT = 180.0   # seconds — long enough to survive a cold-start model load


class ChatRAGService:

    # ── LLM Warm-up ───────────────────────────────────────────────────────────
    @staticmethod
    async def warmup_llm() -> None:
        """
        Send a minimal /api/generate keep-alive request so Ollama loads the
        model into memory at startup rather than on the first real user request.
        This prevents the cold-start delay from causing a timeout on the first query.
        """
        try:
            async with httpx.AsyncClient(timeout=60.0) as client:
                await client.post(
                    f"{OLLAMA_URL}/api/generate",
                    json={"model": MODEL_NAME, "prompt": "", "keep_alive": "10m"},
                )
            logger.info(f"LLM warm-up complete — {MODEL_NAME} loaded into memory.")
        except Exception as e:
            logger.warning(f"LLM warm-up failed (Ollama may not be running): {e}")

    # ── Retrieval ─────────────────────────────────────────────────────────────
    @staticmethod
    async def get_relevant_context(query: str, top_k: int = 6) -> List[Dict[str, Any]]:
        """
        Return the top_k most semantically similar CSV rows for the query.

        Delegates to VectorIndexService which uses cosine similarity over
        nomic-embed-text embeddings stored in ChromaDB. Falls back to an
        empty list if the index is not ready (startup still in progress or
        Ollama unavailable), preserving graceful degradation.
        """
        try:
            results = await vector_index.query(query, top_k=top_k)
            if results:
                logger.info(
                    f"RAG: semantic search found {len(results)} results for query={query!r}"
                )
            else:
                logger.warning(f"RAG: no vector results for query={query!r}")
            return results
        except Exception as e:
            logger.error(f"RAG: vector search error: {e}")
            return []

    # ── Context Formatting ────────────────────────────────────────────────────
    @staticmethod
    def _format_context(sources: List[Dict[str, Any]]) -> str:
        if not sources:
            return "No matching records found in the KGraph software database."

        lines = [
            "The following software projects/developers are in the KGraph database "
            "and are most relevant to the user query:\n"
        ]
        for i, s in enumerate(sources, 1):
            lines.append(f"[{i}] Software: {s.get('Software Name', 'N/A')}")
            if s.get("Short Description"):
                lines.append(f"    Description: {s['Short Description']}")
            if s.get("Workcenters"):
                lines.append(f"    Location/Workcenter: {s['Workcenters']}")
            if s.get("Developer Names"):
                lines.append(f"    Developers: {s['Developer Names']}")
            if s.get("Developer Group"):
                lines.append(f"    Group: {s['Developer Group']}")
            if s.get("Technologies"):
                lines.append(f"    Technologies: {s['Technologies']}")
            if s.get("Categories"):
                lines.append(f"    Categories: {s['Categories']}")
            lines.append("")
        return "\n".join(lines)

    # ── Direct RAG Answer (LLM-independent) ───────────────────────────────────
    @staticmethod
    def _build_direct_answer(sources: List[Dict[str, Any]]) -> str:
        """
        Format RAG sources into a clean, structured answer without LLM.
        Used as fallback when LLM is unavailable or its response is not grounded.
        """
        lines = ["Here are the most relevant results from the KGraph database:\n"]
        for i, s in enumerate(sources, 1):
            name = s.get("Software Name", "Unknown")
            desc = s.get("Short Description") or s.get("Detailed Description", "")
            devs = s.get("Developer Names", "N/A")
            loc  = s.get("Workcenters", "N/A")
            tech = s.get("Technologies", "N/A")
            cats = s.get("Categories", "N/A")
            grp  = s.get("Developer Group", "")

            lines.append(f"{i}. {name}")
            if desc:
                lines.append(f"   {desc}")
            lines.append(f"   • Developers : {devs}" + (f" ({grp})" if grp else ""))
            lines.append(f"   • Location   : {loc}")
            lines.append(f"   • Technologies: {tech}")
            lines.append(f"   • Category   : {cats}")
            lines.append("")
        return "\n".join(lines)

    # ── Main Response Generator ───────────────────────────────────────────────
    @staticmethod
    async def generate_chat_response(request: ChatRequest) -> ChatResponse:
        mode = getattr(request, "mode", "llm")   # "llm" | "rag"
        sources = await ChatRAGService.get_relevant_context(request.query)

        direct_rag_answer = ChatRAGService._build_direct_answer(sources) if sources else None

        # ── RAG-only mode ─────────────────────────────────────────────────────
        if mode == "rag":
            if not sources:
                logger.info("RAG: no results found.")
                return ChatResponse(
                    answer=(
                        "I could not find any matching records in the KGraph database for your query.\n"
                        "Try a specific technology, developer name, project category, or workcenter location."
                    ),
                    sources=[],
                    response_mode="rag",
                )
            logger.info("Mode=rag — returning direct RAG answer without LLM.")
            return ChatResponse(
                answer=direct_rag_answer,
                sources=sources,
                response_mode="rag",
            )


        # ── LLM mode: free-form AI with optional RAG context ─────────────────
        # The LLM answers ANY question from its own knowledge.
        # If RAG found relevant records, they are provided as supplementary context.
        context_str = ChatRAGService._format_context(sources) if sources else ""

        if sources:
            system_prompt = (
                "You are a helpful AI assistant. You have access to a KGraph internal database "
                "of software projects and developers, provided below as context.\n"
                "Guidelines:\n"
                "- If the user's question is about software projects, developers, technologies, "
                "or workcenters, refer to the CONTEXT section and mention specific project names, "
                "developer names, and technologies from it.\n"
                "- For general questions (greetings, general tech topics, etc.), answer naturally "
                "using your own knowledge — you are not limited to the database.\n"
                "- Be concise, helpful, and conversational.\n\n"
                "CONTEXT (KGraph database — use when relevant):\n"
                f"{context_str}\n"
                "END CONTEXT"
            )
        else:
            system_prompt = (
                "You are a helpful AI assistant with expertise in software development. "
                "Answer the user's question naturally and helpfully."
            )

        history = request.messages[-6:] if len(request.messages) > 6 else request.messages
        ollama_messages = [{"role": "system", "content": system_prompt}]
        for m in history:
            ollama_messages.append({"role": m.role, "content": m.content})
        if not history or history[-1].content != request.query:
            ollama_messages.append({"role": "user", "content": request.query})

        payload = {
            "model": MODEL_NAME,
            "messages": ollama_messages,
            "stream": False,
            "options": {
                "temperature": 0.4,   # higher = more natural conversational replies
                "top_p":       0.9,
                "num_predict": 600,
            },
        }

        try:
            async with httpx.AsyncClient(timeout=OLLAMA_TIMEOUT) as client:
                res = await client.post(f"{OLLAMA_URL}/api/chat", json=payload)
                res.raise_for_status()
                llm_answer = res.json().get("message", {}).get("content", "").strip()

                # LLM mode — accept any non-empty response, no grounding check needed
                if llm_answer:
                    logger.info("Mode=llm — using LLM answer.")
                    return ChatResponse(answer=llm_answer, sources=sources, response_mode="llm")
                else:
                    # Empty response from Ollama — fall back to RAG if available
                    if direct_rag_answer:
                        logger.warning("Mode=llm — empty LLM response, falling back to RAG.")
                        return ChatResponse(answer=direct_rag_answer, sources=sources, response_mode="rag")
                    return ChatResponse(answer="Sorry, I could not generate a response.", sources=[], response_mode="rag")

        except Exception as e:
            logger.error(f"Mode=llm — Ollama unavailable ({e}); auto-falling back to RAG.")
            fallback = direct_rag_answer or "Sorry, the LLM is unavailable and no database records were found."
            prefix = f"⚠️ LLM ({MODEL_NAME}) is unavailable." + ("\n\n" if direct_rag_answer else "")
            return ChatResponse(
                answer=prefix + fallback,
                sources=sources or [],
                response_mode="rag",
            )


chat_rag_service = ChatRAGService()

