"""Pydantic schemas for API request/response models."""
from pydantic import BaseModel, Field, field_validator
from typing import List, Optional, Dict, Any


# --- Request Models ---

class SearchRequest(BaseModel):
    """Natural language search request."""
    query: str = Field(..., description="Natural language search query", min_length=1, max_length=500)
    limit: int = Field(default=25, ge=1, le=100, description="Max results per entity type")

    @field_validator("query")
    @classmethod
    def sanitize_query(cls, v: str) -> str:
        return v.strip()


class CreateDeveloperRequest(BaseModel):
    """Create a new developer."""
    name: str = Field(..., min_length=1, max_length=100)
    bio: Optional[str] = Field(None, max_length=500)
    project_count: int = Field(default=0, ge=0)


class CreateProjectRequest(BaseModel):
    """Create a new project."""
    name: str = Field(..., min_length=1, max_length=100)
    description: Optional[str] = Field(None, max_length=1000)
    tagline: Optional[str] = Field(None, max_length=200)
    developed_on: Optional[str] = Field(None, pattern=r"^\d{4}$")
    developers: List[str] = Field(default=[], description="Developer names")
    technologies: List[str] = Field(default=[], description="Technology names")
    domains: List[str] = Field(default=[], description="Domain names")
    locations: List[str] = Field(default=[], description="Location names")


# --- Response Models ---

class TechnologyResponse(BaseModel):
    """Technology node response."""
    name: str


class DomainResponse(BaseModel):
    """Domain node response."""
    name: str


class LocationResponse(BaseModel):
    """Location node response."""
    name: str


class DeveloperResponse(BaseModel):
    """Developer search result."""
    name: str
    project_count: int = 0
    bio: Optional[str] = None
    email: Optional[str] = None
    phone: Optional[str] = None
    locations: List[str] = []
    technologies: List[str] = []
    domains: List[str] = []
    projects: List[str] = []
    relevance_score: float = 0.0


class ProjectResponse(BaseModel):
    """Project search result."""
    name: str
    description: Optional[str] = None
    tagline: Optional[str] = None
    developed_on: Optional[str] = None
    developers: List[str] = []
    technologies: List[str] = []
    domains: List[str] = []
    locations: List[str] = []
    relevance_score: float = 0.0


class SearchResponse(BaseModel):
    """Combined search response."""
    query: str
    entity_type: str  # "developer", "project", or "both"
    parsed_filters: Dict[str, Any] = {}
    developers: List[DeveloperResponse] = []
    projects: List[ProjectResponse] = []
    total_results: int = 0
    limit: int = 25


class RecommendationResponse(BaseModel):
    """Recommendation results."""
    source: str
    source_type: str  # "developer" or "project"
    recommended_projects: List[ProjectResponse] = []
    recommended_developers: List[DeveloperResponse] = []


# --- Graph Visualization Models ---

class GraphNode(BaseModel):
    """Node for graph visualization."""
    id: str
    label: str
    type: str  # Developer, Project, Technology, Domain, Location
    properties: Dict[str, Any] = {}
    color: Optional[str] = None
    size: Optional[float] = None


class GraphLink(BaseModel):
    """Link for graph visualization."""
    source: str
    target: str
    type: str  # DEVELOPED, USES_TECH, BELONGS_TO, LOCATED_IN

    def __eq__(self, other):
        if not isinstance(other, GraphLink):
            return False
        return self.source == other.source and self.target == other.target and self.type == other.type

    def __hash__(self):
        return hash((self.source, self.target, self.type))


class GraphResponse(BaseModel):
    """Graph visualization data."""
    nodes: List[GraphNode] = []
    links: List[GraphLink] = []
    stats: Dict[str, int] = {}


# --- Stats Model ---

class StatsResponse(BaseModel):
    """Graph statistics response."""
    nodes: Dict[str, int] = {}
    relationships: Dict[str, int] = {}
    total_nodes: int = 0
    total_relationships: int = 0
    is_seeded: bool = False


# --- Parsed Query Model ---

class ParsedQuery(BaseModel):
    """Result of natural language query parsing."""
    entity: str = "both"  # "developer", "project", "both"
    technology: Optional[str] = None
    technologies: List[str] = []
    domain: Optional[str] = None
    location: Optional[str] = None
    min_projects: Optional[int] = None
    name: Optional[str] = None
    keyword: Optional[str] = None
    developed_on: Optional[str] = None


# --- Standard Error Response ---

class ErrorResponse(BaseModel):
    """Standard error response."""
    detail: str
    code: Optional[str] = None
