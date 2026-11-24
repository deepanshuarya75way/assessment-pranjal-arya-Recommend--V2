"""Neo4j database driver management."""
import time
import logging
from neo4j import GraphDatabase
from neo4j.exceptions import ServiceUnavailable, AuthError
from app.core.config import settings

logger = logging.getLogger(__name__)


class Neo4jDriver:
    """Manages Neo4j driver connection lifecycle."""

    def __init__(self):
        self._driver = None

    def connect(self, retries: int = 5, delay: int = 3):
        """Initialize the Neo4j driver with retry logic."""
        for attempt in range(retries):
            try:
                self._driver = GraphDatabase.driver(
                    settings.neo4j_uri,
                    auth=(settings.neo4j_user, settings.neo4j_password),
                    max_connection_lifetime=3600,
                    max_connection_pool_size=50,
                    connection_acquisition_timeout=60,
                )
                # Verify connection is valid
                self._driver.verify_connectivity()
                logger.info(f"✅ Connected to Neo4j at {settings.neo4j_uri}")
                print(f"✅ Connected to Neo4j at {settings.neo4j_uri}")
                return
            except AuthError as e:
                logger.error(f"❌ Neo4j auth failed: {e}")
                raise
            except ServiceUnavailable as e:
                if attempt < retries - 1:
                    logger.warning(
                        f"⏳ Neo4j not ready (attempt {attempt + 1}/{retries}). "
                        f"Retrying in {delay}s..."
                    )
                    print(
                        f"⏳ Neo4j not ready (attempt {attempt + 1}/{retries}). "
                        f"Retrying in {delay}s..."
                    )
                    time.sleep(delay)
                else:
                    logger.error(f"❌ Neo4j unavailable after {retries} attempts: {e}")
                    raise

    def close(self):
        """Close the Neo4j driver."""
        if self._driver:
            self._driver.close()
            self._driver = None
            logger.info("🔌 Neo4j connection closed")
            print("🔌 Neo4j connection closed")

    def verify_connectivity(self) -> bool:
        """Verify database connectivity."""
        try:
            if not self._driver:
                return False
            self._driver.verify_connectivity()
            return True
        except Exception as e:
            logger.warning(f"Neo4j connectivity check failed: {e}")
            return False

    def get_session(self):
        """Get a Neo4j session."""
        if not self._driver:
            self.connect()
        return self._driver.session(database=settings.neo4j_database)

    def execute_query(self, query: str, parameters: dict = None) -> list:
        """Execute a Cypher read query and return results as plain dicts."""
        try:
            with self.get_session() as session:
                result = session.run(query, parameters or {})
                records = result.data()  # .data() converts records to dicts properly
                return records
        except Exception as e:
            logger.error(f"Query execution failed: {e}\nQuery: {query}")
            raise

    def execute_write(self, query: str, parameters: dict = None):
        """Execute a write Cypher query inside a write transaction."""
        try:
            with self.get_session() as session:
                result = session.run(query, parameters or {})
                summary = result.consume()
                return summary
        except Exception as e:
            logger.error(f"Write execution failed: {e}\nQuery: {query}")
            raise

    def execute_write_tx(self, queries_and_params: list):
        """Execute multiple write queries in a single transaction."""
        def _tx_work(tx):
            results = []
            for query, params in queries_and_params:
                result = tx.run(query, params or {})
                results.append(result.consume())
            return results

        with self.get_session() as session:
            return session.execute_write(_tx_work)

    def get_stats(self) -> dict:
        """Get graph statistics."""
        try:
            results = self.execute_query("""
                MATCH (n)
                RETURN labels(n)[0] AS label, count(n) AS count
                ORDER BY label
            """)
            stats = {r["label"]: r["count"] for r in results if r.get("label")}

            rel_results = self.execute_query("""
                MATCH ()-[r]->()
                RETURN type(r) AS rel_type, count(r) AS count
                ORDER BY rel_type
            """)
            rel_stats = {r["rel_type"]: r["count"] for r in rel_results if r.get("rel_type")}

            return {"nodes": stats, "relationships": rel_stats}
        except Exception as e:
            logger.error(f"Failed to get stats: {e}")
            return {"nodes": {}, "relationships": {}}


neo4j_driver = Neo4jDriver()
