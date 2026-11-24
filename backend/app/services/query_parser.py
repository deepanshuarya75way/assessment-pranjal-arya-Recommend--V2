"""
Natural Language Query Parser

Provides an abstraction layer for parsing natural language queries into
structured filters. Three backends are available:

  "rule"   — Fast, deterministic, no API key. Uses regex + keyword lists.
  "gemini" — Google Gemini LLM. Requires GEMINI_API_KEY in .env.
              Set QUERY_PARSER=gemini in .env to activate.
  "openai" — OpenAI GPT. Requires OPENAI_API_KEY in .env.
              Set QUERY_PARSER=openai in .env to activate.

All parsers return the same ParsedQuery Pydantic model, so the rest of
the search pipeline is completely parser-agnostic.
"""
import re
import json
import logging
from abc import ABC, abstractmethod
from typing import Optional

from app.models.schemas import ParsedQuery

logger = logging.getLogger(__name__)


# ---------------------------------------------------------------------------
# Abstract Base
# ---------------------------------------------------------------------------

class BaseQueryParser(ABC):
    """Abstract base class for query parsers."""

    @abstractmethod
    def parse(self, query: str) -> ParsedQuery:
        """Parse a natural language query into structured filters."""
        pass


# ---------------------------------------------------------------------------
# Rule-Based Parser  (no external dependencies)
# ---------------------------------------------------------------------------

class RuleBasedParser(BaseQueryParser):
    """
    Rule-based natural language query parser.

    Uses regex patterns and keyword matching to extract structured
    filters from natural language queries. No API key required.
    Fast and deterministic but limited in linguistic flexibility.
    """

    TECHNOLOGIES = [
        "react", "fastapi", "python", "javascript", "typescript", "node.js",
        "nodejs", "django", "flask", "tensorflow", "pytorch", "mongodb",
        "postgresql", "postgres", "docker", "kubernetes", "aws", "vue.js",
        "vuejs", "angular", "next.js", "nextjs", "graphql", "redis",
        "machine learning", "ml", "nlp", "natural language processing",
        "computer vision", "scikit-learn", "sklearn", "pandas", "spark",
        "kafka", "elasticsearch", "go", "golang", "rust", "ai",
        "artificial intelligence", "deep learning", "java", "php", "c#",
        "c++", "asp.net", "mysql", "oracle", "matlab", "react native",
    ]

    TECH_NORMALIZE = {
        "nodejs": "Node.js", "node.js": "Node.js",
        "vuejs": "Vue.js", "vue.js": "Vue.js",
        "nextjs": "Next.js", "next.js": "Next.js",
        "ml": "Machine Learning", "machine learning": "Machine Learning",
        "ai": "AI/ML", "artificial intelligence": "AI/ML",
        "deep learning": "Machine Learning",
        "nlp": "NLP", "natural language processing": "NLP",
        "sklearn": "Scikit-learn", "scikit-learn": "Scikit-learn",
        "postgres": "PostgreSQL", "postgresql": "PostgreSQL",
        "golang": "Go", "php": "PHP", "mysql": "MySQL", "c#": "C#",
        "c++": "C++", "asp.net": "ASP.net", "oracle": "Oracle",
        "matlab": "MATLAB",
    }

    DOMAINS = {
        "ai": "AI & ML", "machine learning": "AI & ML", "ml": "AI & ML", "artificial intelligence": "AI & ML",
        "crs converter": "CRS Converters", "crs": "CRS Converters",
        "dashboard": "Dashboard",
        "data management": "Data Management", "data": "Data Management",
        "digitization": "Digitization",
        "helpdesk": "Helpdesk", "help desk": "Helpdesk", "support": "Helpdesk",
        "laboratory": "Laboratory", "lab": "Laboratory",
        "library": "Library",
        "license": "License Management", "license management": "License Management",
        "log": "Log", "logs": "Log",
        "logistic": "Logistic", "logistics": "Logistic",
        "map": "Map Application", "mapping": "Map Application", "map application": "Map Application",
        "mobile": "Mobile Application", "mobile app": "Mobile Application", "mobile application": "Mobile Application",
        "project management": "Project Management & Process Workflow", "process workflow": "Project Management & Process Workflow", "workflow": "Project Management & Process Workflow",
        "reservoir": "Reservoir",
        "security": "Security", "cybersecurity": "Security",
        "seismic": "Seismic",
        "tape": "Tape Data Management", "tape data": "Tape Data Management",
        "under development": "Under Development", "development": "Under Development",
        "utility": "Utility", "utilities": "Utility"
    }

    LOCATIONS = {
        "aaab": "AAAB",
        "ahmedabad": "Ahmedabad", "ahemdabad": "Ahmedabad", "ahmadabad": "Ahmedabad",
        "cb": "CB",
        "cgs": "CGS",
        "chennai": "Chennai", "madras": "Chennai",
        "database": "Database",
        "dehradun": "Dehradun", "dehradoon": "Dehradun", "dehra dun": "Dehradun",
        "e&d": "E&D",
        "expl. data services": "Expl. Data Services (formerly EPINET)", "epinet": "Expl. Data Services (formerly EPINET)",
        "geopic": "GEOPIC",
        "irs": "IRS",
        "jorhat": "Jorhat",
        "mh asset": "MH Asset", "mh": "MH Asset",
        "mumbai": "Mumbai", "bombay": "Mumbai",
        "rcc": "RCC",
        "rajahmundry asset": "Rajahmundry Asset", "rajahmundry": "Rajahmundry",
        "rajamahendravaram": "Rajahmundry", "rajam": "Rajahmundry",
        "spic": "SPIC",
        "vadodara": "Vadodara", "vadodra": "Vadodara", "baroda": "Vadodara",
        "wob": "WOB",
        "won": "WON"
    }

    def parse(self, query: str) -> ParsedQuery:
        query_lower = query.lower().strip()
        parsed = ParsedQuery()
        parsed.entity = self._detect_entity(query_lower)
        parsed.technologies = self._extract_technologies(query_lower)
        if parsed.technologies:
            parsed.technology = parsed.technologies[0]
        parsed.domain = self._extract_domain(query_lower)
        parsed.location = self._extract_location(query_lower)
        parsed.min_projects = self._extract_min_projects(query_lower)
        parsed.developed_on = self._extract_year(query_lower)
        parsed.keyword = self._extract_keyword(query_lower)
        return parsed

    def _detect_entity(self, query: str) -> str:
        developer_keywords = [
            "developer", "developers", "dev", "devs", "engineer", "engineers",
            "programmer", "programmers", "coder", "coders", "people", "person",
            "who", "team", "talent",
        ]
        project_keywords = [
            "project", "projects", "app", "apps", "application", "applications",
            "platform", "system", "tool", "software", "product", "build",
            "built", "created", "developed",
        ]
        dev_score = sum(1 for kw in developer_keywords if kw in query.split() or kw in query)
        proj_score = sum(1 for kw in project_keywords if kw in query.split() or kw in query)
        if re.search(r'\b(show|find|list|get|search)\s+.*developer', query):
            return "developer"
        if re.search(r'\b(show|find|list|get|search)\s+.*project', query):
            return "project"
        if dev_score > proj_score:
            return "developer"
        elif proj_score > dev_score:
            return "project"
        return "both"

    def _extract_technologies(self, query: str) -> list:
        found = []
        sorted_techs = sorted(self.TECHNOLOGIES, key=len, reverse=True)
        remaining = query
        for tech in sorted_techs:
            # Use word-boundary matching to avoid false positives
            # e.g. "ai" inside "mumbai", "ml" inside "email"
            pattern = r'\b' + re.escape(tech) + r'\b'
            if re.search(pattern, remaining):
                normalized = self.TECH_NORMALIZE.get(tech, tech.title())
                if normalized not in found:
                    found.append(normalized)
                remaining = re.sub(pattern, " ", remaining)
        return found

    def _extract_domain(self, query: str) -> Optional[str]:
        sorted_domains = sorted(self.DOMAINS.keys(), key=len, reverse=True)
        for keyword in sorted_domains:
            # Word-boundary match prevents e.g. "data" matching inside "database"
            pattern = r'\b' + re.escape(keyword) + r'\b'
            if re.search(pattern, query):
                return self.DOMAINS[keyword]
        return None

    def _extract_location(self, query: str) -> Optional[str]:
        # Sort longest keys first so "rajahmundry asset" beats "rajahmundry"
        sorted_locs = sorted(self.LOCATIONS.items(), key=lambda kv: len(kv[0]), reverse=True)
        for keyword, location in sorted_locs:
            pattern = r'\b' + re.escape(keyword) + r'\b'
            if re.search(pattern, query):
                return location
        return None

    def _extract_min_projects(self, query: str) -> Optional[int]:
        patterns = [
            r'more than (\d+) projects?', r'at least (\d+) projects?',
            r'minimum (\d+) projects?', r'min (\d+) projects?',
            r'(\d+)\+?\s*projects?', r'over (\d+) projects?',
            r'above (\d+) projects?',
        ]
        for pattern in patterns:
            match = re.search(pattern, query)
            if match:
                return int(match.group(1))
        return None

    def _extract_year(self, query: str) -> Optional[str]:
        match = re.search(r'\b(20\d{2})\b', query)
        return match.group(1) if match else None

    def _extract_keyword(self, query: str) -> Optional[str]:
        stop_words = {
            "show", "find", "list", "get", "search", "me", "all", "the",
            "with", "in", "from", "and", "or", "who", "have", "has",
            "using", "built", "developed", "experience", "expertise",
            "more", "than", "at", "least", "minimum", "over", "above",
            "projects", "project", "developer", "developers", "for", "a",
            "an", "of", "to", "by", "on", "that", "which", "are", "is",
        }
        words = query.split()
        meaningful = [w for w in words if w not in stop_words and len(w) > 2]
        result_words = []
        for word in meaningful:
            is_matched = any(
                word in tech.split() for tech in self.TECHNOLOGIES
            ) or any(
                word in dk.split() for dk in self.DOMAINS
            ) or any(
                word in lk.split() for lk in self.LOCATIONS
            )
            if not is_matched and not word.isdigit():
                result_words.append(word)
        return " ".join(result_words) if result_words else None


# ---------------------------------------------------------------------------
# Gemini Parser  (requires GEMINI_API_KEY)
# ---------------------------------------------------------------------------

# System prompt that teaches Gemini the exact schema to return
_GEMINI_SYSTEM_PROMPT = """You are a search query parser for a software developer & project knowledge graph.
The graph contains:
  - Developers
  - Projects
  - Technologies: ASP.net, Python, C#, C++, Java, JS, PHP, React, React Native, Vue.js, MATLAB, Oracle, MySQL, Docker, Django, Spring Boot, etc.
  - Domains: AI & ML, CRS Converters, Dashboard, Data Management, Digitization, Helpdesk, Laboratory, Library, License Management, Log, Logistic, Map Application, Mobile Application, Project Management & Process Workflow, Reservoir, Security, Seismic, Tape Data Management, Under Development, Utility
  - Locations: AAAB, Ahmedabad, CB, CGS, Chennai, Database, Dehradun, E&D, Expl. Data Services (formerly EPINET), GEOPIC, IRS, Jorhat, MH Asset, Mumbai, RCC, Rajahmundry, Rajahmundry Asset, SPIC, Vadodara, WOB, WON

Parse the user's natural language query and extract structured filters.
Return ONLY a valid JSON object with these exact fields (omit or null if not applicable):
{
  "entity": "developer" | "project" | "both",
  "technologies": ["Tech1", "Tech2"],
  "technology": "Tech1",
  "domain": "DomainName",
  "location": "CityName",
  "min_projects": 5,
  "developed_on": "2024",
  "keyword": "remaining search term"
}

Rules:
- "entity": "developer" if query is about people/devs, "project" if about apps/software, "both" if unclear
- "technologies": list of matching tech names from the known list above (use exact names)
- "technology": first/primary technology (same as technologies[0])
- "domain": one matching domain from the known list above
- "location": one Indian city from the known list above
- "min_projects": integer if query mentions "more than N projects", "at least N projects", etc.
- "developed_on": 4-digit year string if mentioned
- "keyword": any other meaningful search term not captured above
- Return null for fields that don't apply. Do NOT include explanation text.
"""


class GeminiParser(BaseQueryParser):
    """
    Gemini-powered natural language query parser.

    Uses Google Gemini API to understand free-form queries and extract
    structured filters. Falls back to RuleBasedParser on any error.

    Setup:
        1. pip install google-generativeai
        2. Set GEMINI_API_KEY=your_key_here in .env
        3. Set QUERY_PARSER=gemini in .env
    """

    def __init__(self):
        self._client = None
        self._fallback = RuleBasedParser()
        self._initialized = False

    def _init_client(self):
        """Lazy-initialize the Gemini client."""
        if self._initialized:
            return
        self._initialized = True

        try:
            import google.generativeai as genai
            from app.core.config import settings

            if not settings.gemini_api_key:
                logger.warning(
                    "GeminiParser: GEMINI_API_KEY not set. "
                    "Falling back to RuleBasedParser."
                )
                return

            genai.configure(api_key=settings.gemini_api_key)
            self._client = genai.GenerativeModel(
                model_name=settings.gemini_model,
                generation_config={
                    "temperature": 0.1,       # Low temp = deterministic JSON
                    "max_output_tokens": 256, # ParsedQuery JSON is small
                    "response_mime_type": "application/json",  # Force JSON output
                },
                system_instruction=_GEMINI_SYSTEM_PROMPT,
            )
            logger.info(f"GeminiParser initialized with model: {settings.gemini_model}")

        except ImportError:
            logger.error(
                "GeminiParser: 'google-generativeai' package not installed. "
                "Run: pip install google-generativeai"
            )
        except Exception as e:
            logger.error(f"GeminiParser: Init failed: {e}")

    def parse(self, query: str) -> ParsedQuery:
        """Parse using Gemini API with fallback to rule-based."""
        self._init_client()

        if not self._client:
            logger.debug("GeminiParser: No client, using fallback.")
            return self._fallback.parse(query)

        try:
            response = self._client.generate_content(
                f"Parse this search query: {query}"
            )
            raw = response.text.strip()
            logger.debug(f"Gemini raw response: {raw}")

            data = json.loads(raw)
            parsed = self._build_parsed_query(data, query)
            logger.info(
                f"GeminiParser parsed '{query}' → entity={parsed.entity}, "
                f"techs={parsed.technologies}, domain={parsed.domain}, "
                f"location={parsed.location}"
            )
            return parsed

        except json.JSONDecodeError as e:
            logger.warning(f"GeminiParser: Invalid JSON response — {e}. Falling back.")
            return self._fallback.parse(query)
        except Exception as e:
            logger.warning(f"GeminiParser: API error — {e}. Falling back.")
            return self._fallback.parse(query)

    def _build_parsed_query(self, data: dict, original_query: str) -> ParsedQuery:
        """Convert the Gemini JSON response to a ParsedQuery model."""
        techs = data.get("technologies") or []
        # Ensure technologies is a list of strings
        if isinstance(techs, str):
            techs = [techs]

        return ParsedQuery(
            entity=data.get("entity", "both"),
            technologies=techs,
            technology=data.get("technology") or (techs[0] if techs else None),
            domain=data.get("domain") or None,
            location=data.get("location") or None,
            min_projects=data.get("min_projects") or None,
            developed_on=str(data["developed_on"]) if data.get("developed_on") else None,
            keyword=data.get("keyword") or None,
        )


# ---------------------------------------------------------------------------
# OpenAI Parser  (requires OPENAI_API_KEY)
# ---------------------------------------------------------------------------

_OPENAI_FUNCTION_SCHEMA = {
    "name": "parse_search_query",
    "description": "Parse a natural language developer/project search query into structured filters",
    "parameters": {
        "type": "object",
        "properties": {
            "entity": {
                "type": "string",
                "enum": ["developer", "project", "both"],
                "description": "Whether the query is about developers, projects, or both",
            },
            "technologies": {
                "type": "array",
                "items": {"type": "string"},
                "description": "Technology names mentioned in the query",
            },
            "domain": {
                "type": "string",
                "description": "Business domain (AI & ML, Data Management, Helpdesk, etc.)",
            },
            "location": {
                "type": "string",
                "description": "Location name (Dehradun, Mumbai, Ahmedabad, etc.)",
            },
            "min_projects": {
                "type": "integer",
                "description": "Minimum number of projects a developer should have",
            },
            "developed_on": {
                "type": "string",
                "description": "4-digit year when the project was developed",
            },
            "keyword": {
                "type": "string",
                "description": "Any other meaningful search term",
            },
        },
        "required": ["entity"],
    },
}

_OPENAI_SYSTEM_PROMPT = (
    "You are a search query parser for a software knowledge graph containing "
    "Indian developers and projects. Extract structured filters from natural "
    "language queries and call the parse_search_query function."
)


class OpenAIParser(BaseQueryParser):
    """
    OpenAI-powered natural language query parser using function calling.

    Uses GPT function calling for guaranteed structured JSON output.
    Falls back to RuleBasedParser on any error.

    Setup:
        1. pip install openai
        2. Set OPENAI_API_KEY=your_key_here in .env
        3. Set QUERY_PARSER=openai in .env
    """

    def __init__(self):
        self._client = None
        self._fallback = RuleBasedParser()
        self._initialized = False

    def _init_client(self):
        if self._initialized:
            return
        self._initialized = True
        try:
            from openai import OpenAI
            from app.core.config import settings

            if not settings.openai_api_key:
                logger.warning("OpenAIParser: OPENAI_API_KEY not set. Falling back.")
                return

            self._client = OpenAI(api_key=settings.openai_api_key)
            logger.info("OpenAIParser initialized with gpt-4o-mini")

        except ImportError:
            logger.error(
                "OpenAIParser: 'openai' package not installed. "
                "Run: pip install openai"
            )
        except Exception as e:
            logger.error(f"OpenAIParser: Init failed: {e}")

    def parse(self, query: str) -> ParsedQuery:
        """Parse using OpenAI function calling with fallback to rule-based."""
        self._init_client()

        if not self._client:
            return self._fallback.parse(query)

        try:
            response = self._client.chat.completions.create(
                model="gpt-4o-mini",
                messages=[
                    {"role": "system", "content": _OPENAI_SYSTEM_PROMPT},
                    {"role": "user", "content": query},
                ],
                tools=[{"type": "function", "function": _OPENAI_FUNCTION_SCHEMA}],
                tool_choice={"type": "function", "function": {"name": "parse_search_query"}},
                max_tokens=256,
                temperature=0.1,
            )

            tool_call = response.choices[0].message.tool_calls[0]
            data = json.loads(tool_call.function.arguments)

            techs = data.get("technologies") or []
            parsed = ParsedQuery(
                entity=data.get("entity", "both"),
                technologies=techs,
                technology=techs[0] if techs else None,
                domain=data.get("domain") or None,
                location=data.get("location") or None,
                min_projects=data.get("min_projects") or None,
                developed_on=str(data["developed_on"]) if data.get("developed_on") else None,
                keyword=data.get("keyword") or None,
            )
            logger.info(
                f"OpenAIParser parsed '{query}' → entity={parsed.entity}, "
                f"techs={parsed.technologies}"
            )
            return parsed

        except Exception as e:
            logger.warning(f"OpenAIParser: Error — {e}. Falling back.")
            return self._fallback.parse(query)


# ---------------------------------------------------------------------------
# Factory
# ---------------------------------------------------------------------------

def get_parser(parser_type: str = "rule") -> BaseQueryParser:
    """
    Factory function to get the appropriate query parser.

    Args:
        parser_type: "rule" | "gemini" | "openai"
                     Defaults to "rule" if unknown type given.
    """
    parsers = {
        "rule": RuleBasedParser,
        "gemini": GeminiParser,
        "openai": OpenAIParser,
    }
    parser_class = parsers.get(parser_type, RuleBasedParser)
    return parser_class()
