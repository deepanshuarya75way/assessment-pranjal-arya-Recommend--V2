"""
User Feedback & Review Endpoints
"""
import uuid
import logging
from datetime import datetime, timezone
from typing import Optional

from fastapi import APIRouter, HTTPException, Query
from pydantic import BaseModel, Field

from app.core.database import neo4j_driver

logger = logging.getLogger(__name__)
router = APIRouter()


class FeedbackCreate(BaseModel):
    query: str = Field(..., min_length=1, description="Original user prompt or search query")
    response: str = Field(..., min_length=1, description="Generated LLM or search response")
    mode: str = Field(default="rag", description="Response source mode: 'llm', 'rag', or 'search'")
    is_useful: bool = Field(..., description="True if useful, False if not useful")
    comment: Optional[str] = Field(default=None, description="Optional user explanation")


@router.post("/feedback", summary="Submit response criteria")
async def submit_feedback(payload: FeedbackCreate):
    """Store user feedback as a :Feedback node in Neo4j."""
    if not neo4j_driver.verify_connectivity():
        raise HTTPException(status_code=503, detail="Database connection unavailable")

    feedback_id = str(uuid.uuid4())
    created_at = datetime.now(timezone.utc).isoformat()

    cypher = """
    CREATE (f:Feedback {
        id: $id,
        query: $query,
        response: $response,
        mode: $mode,
        is_useful: $is_useful,
        comment: $comment,
        created_at: $created_at
    })
    RETURN f.id AS id
    """

    try:
        neo4j_driver.execute_write(
            cypher,
            {
                "id": feedback_id,
                "query": payload.query,
                "response": payload.response,
                "mode": payload.mode,
                "is_useful": payload.is_useful,
                "comment": payload.comment,
                "created_at": created_at,
            },
        )
        return {"status": "saved", "id": feedback_id}
    except Exception as e:
        logger.error(f"Failed to save feedback: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail="Could not save feedback")


@router.get("/feedback", summary="Retrieve all user reviews and summary metrics")
async def get_feedback(
    useful: Optional[bool] = Query(default=None, description="Filter by usefulness (true/false)")
):
    """Fetch stored feedback items and aggregate usefulness statistics."""
    if not neo4j_driver.verify_connectivity():
        raise HTTPException(status_code=503, detail="Database connection unavailable")

    where_clause = "WHERE f.is_useful = $useful" if useful is not None else ""
    cypher = f"""
    MATCH (f:Feedback)
    {where_clause}
    RETURN f.id AS id,
           f.query AS query,
           f.response AS response,
           f.mode AS mode,
           f.is_useful AS is_useful,
           f.comment AS comment,
           f.created_at AS created_at
    ORDER BY f.created_at DESC
    """

    try:
        params = {"useful": useful} if useful is not None else {}
        items = neo4j_driver.execute_query(cypher, params)

        total = len(items)
        useful_count = sum(1 for item in items if item.get("is_useful"))

        return {
            "summary": {
                "total": total,
                "useful": useful_count,
                "not_useful": total - useful_count,
                "approval_rate": round((useful_count / total) * 100, 1) if total > 0 else 0.0,
            },
            "reviews": items,
        }
    except Exception as e:
        logger.error(f"Failed to fetch feedback: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail="Could not retrieve feedback")
