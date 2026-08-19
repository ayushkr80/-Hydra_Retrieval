import os
import sys
from neo4j import GraphDatabase

# Force stdout to use UTF-8 on Windows to support Unicode characters
if hasattr(sys.stdout, "reconfigure"):
    try:
        sys.stdout.reconfigure(encoding="utf-8")
    except Exception:
        pass

def load_env():
    """
    Helper to manually load .env file contents from the current directory
    or the parent directory into os.environ.
    """
    for path in [".env", "../.env"]:
        if os.path.exists(path):
            try:
                with open(path, "r", encoding="utf-8") as f:
                    for line in f:
                        line = line.strip()
                        if line and not line.startswith("#") and "=" in line:
                            key, val = line.split("=", 1)
                            val = val.strip().strip("'\"")
                            os.environ[key.strip()] = val
            except Exception as e:
                print(f"Warning: Failed to read .env at {path}: {e}")

class HydraGraph:
    def __init__(self, uri=None, user=None, password=None):
        load_env()
        self.uri = uri or os.environ.get("NEO4J_URI", "bolt://localhost:7687")
        self.user = user or os.environ.get("NEO4J_USER", "neo4j")
        self.password = password or os.environ.get("NEO4J_PASSWORD")
        
        if not self.password:
            raise ValueError(
                "Configuration Error: NEO4J_PASSWORD environment variable is not set.\n"
                "Please declare it in a local .env file or export it in your shell environment."
            )
        
        try:
            self.driver = GraphDatabase.driver(self.uri, auth=(self.user, self.password))
            # Verify connectivity
            self.driver.verify_connectivity()
        except Exception as e:
            print(f"✗ Failed to connect to Neo4j database at {self.uri}")
            print(f"Error: {e}")
            raise e

    def close(self):
        if hasattr(self, "driver"):
            self.driver.close()

    def clear_database(self):
        query = "MATCH (n) DETACH DELETE n"
        with self.driver.session() as session:
            session.run(query)
        print("✓ Database cleared")

    # ---------------------------------------------------------
    # NODE CREATION
    # ---------------------------------------------------------

    def create_actor(self, actor_id: str, name: str):
        query = """
        MERGE (a:Actor {id: $actor_id})
        SET a.name = $name
        RETURN a
        """
        with self.driver.session() as session:
            session.run(query, actor_id=actor_id, name=name)

    def create_scope(self, scope_id: str, name: str):
        query = """
        MERGE (s:Scope {id: $scope_id})
        SET s.name = $name
        RETURN s
        """
        with self.driver.session() as session:
            session.run(query, scope_id=scope_id, name=name)

    def create_fact(self, fact_id: str, content: str, created_at: str, topic: str = None):
        # Infer topic from content if not explicitly specified
        if not topic:
            if "Acme" in content:
                topic = "Acme"
            elif "BetaCo" in content:
                topic = "BetaCo"
            elif "Gamma" in content:
                topic = "Gamma"
            else:
                topic = "General"

        query = """
        MERGE (f:Fact {id: $fact_id})
        SET f.content = $content, f.created_at = $created_at, f.topic = $topic
        RETURN f
        """
        with self.driver.session() as session:
            session.run(query, fact_id=fact_id, content=content, created_at=created_at, topic=topic)

    # ---------------------------------------------------------
    # RELATIONSHIP CREATION
    # ---------------------------------------------------------

    def add_actor_to_scope(self, actor_id: str, scope_id: str, since: str, until: str = None):
        query = """
        MATCH (a:Actor {id: $actor_id})
        MATCH (s:Scope {id: $scope_id})
        MERGE (a)-[r:MEMBER_OF]->(s)
        SET r.since = $since, r.until = $until
        RETURN r
        """
        with self.driver.session() as session:
            session.run(query, actor_id=actor_id, scope_id=scope_id, since=since, until=until)

    def make_fact_visible_to(self, fact_id: str, scope_id: str, since: str, until: str = None):
        query = """
        MATCH (f:Fact {id: $fact_id})
        MATCH (s:Scope {id: $scope_id})
        MERGE (f)-[r:VISIBLE_TO]->(s)
        SET r.since = $since, r.until = $until
        RETURN r
        """
        with self.driver.session() as session:
            session.run(query, fact_id=fact_id, scope_id=scope_id, since=since, until=until)

    def add_provenance(self, derived_fact_id: str, source_fact_id: str):
        query = """
        MATCH (d:Fact {id: $derived_fact_id})
        MATCH (s:Fact {id: $source_fact_id})
        MERGE (d)-[r:DERIVED_FROM]->(s)
        RETURN r
        """
        with self.driver.session() as session:
            session.run(query, derived_fact_id=derived_fact_id, source_fact_id=source_fact_id)

    # ---------------------------------------------------------
    # SECURE RETRIEVAL & TRAVERSAL (Priority 1 & 2)
    # ---------------------------------------------------------

    def get_facts_for_actor(self, actor_id: str, topic: str, as_of: str):
        """
        Retrieves all facts for a topic that the actor is authorized to see at the specified time 'as_of'.
        A fact f is authorized if for every source fact src in its DERIVED_FROM path (including f itself):
          - Either src has no visibility constraints (no VISIBLE_TO edges).
          - Or the actor has an active membership in at least one Scope to which src is visible at 'as_of'.
        """
        query = """
        MATCH (actor:Actor {id: $actor_id})
        MATCH (f:Fact)
        WHERE f.topic = $topic OR f.content CONTAINS $topic
        
        // Find all source facts in the derivation graph (including f itself)
        MATCH (f)-[:DERIVED_FROM*0..]->(src:Fact)
        
        // Check if src has any visibility restriction
        OPTIONAL MATCH (src)-[any_v:VISIBLE_TO]->()
        WITH actor, f, src, count(any_v) > 0 AS has_restriction
        
        // Check if the actor has active access to src at time as_of
        OPTIONAL MATCH (actor)-[m:MEMBER_OF]->(scope:Scope)<-[v:VISIBLE_TO]-(src)
        WHERE
            m.since <= $as_of AND (m.until IS NULL OR m.until > $as_of)
            AND v.since <= $as_of AND (v.until IS NULL OR v.until > $as_of)
            
        WITH actor, f, src, (NOT has_restriction OR count(scope) > 0) AS src_accessible
        
        // Aggregate accessibility across all sources in the derivation path
        WITH actor, f, all(x IN collect(src_accessible) WHERE x = true) AS is_authorized
        WHERE is_authorized
        
        // Find the scopes through which the actor gets access to the fact f itself (if any)
        OPTIONAL MATCH (f)-[v:VISIBLE_TO]->(s:Scope)<-[m:MEMBER_OF]-(actor)
        WHERE
            m.since <= $as_of AND (m.until IS NULL OR m.until > $as_of)
            AND v.since <= $as_of AND (v.until IS NULL OR v.until > $as_of)
            
        RETURN
            f.id AS id,
            f.content AS content,
            f.topic AS topic,
            collect(s.name) AS scope_names
        """
        with self.driver.session() as session:
            result = session.run(query, actor_id=actor_id, topic=topic, as_of=as_of)
            return [
                {
                    "id": record["id"],
                    "content": record["content"],
                    "topic": record["topic"],
                    "scope_name": record["scope_names"][0] if record["scope_names"] else "Derived (Implicit)"
                }
                for record in result
            ]

    def get_all_topic_facts(self, topic: str):
        """
        Retrieves all facts matching a topic, regardless of permissions.
        Used to identify blocked facts for comparison.
        """
        query = """
        MATCH (f:Fact)
        WHERE f.topic = $topic OR f.content CONTAINS $topic
        RETURN f.id AS id, f.content AS content, f.topic AS topic
        """
        with self.driver.session() as session:
            result = session.run(query, topic=topic)
            return [record.data() for record in result]

    def get_trace(self, actor_id: str, fact_id: str, as_of: str):
        """
        Traces the authorization/provenance tree for a single fact.
        Returns a list of source facts, their scopes, and the actor's authorization status for each.
        """
        query = """
        MATCH (actor:Actor {id: $actor_id})
        MATCH (f:Fact {id: $fact_id})
        
        // Find all facts in derivation path
        MATCH (f)-[:DERIVED_FROM*0..]->(src:Fact)
        
        // Get scopes they are visible to
        OPTIONAL MATCH (src)-[v:VISIBLE_TO]->(scope:Scope)
        
        // Get actor's membership in those scopes
        OPTIONAL MATCH (actor)-[m:MEMBER_OF]->(scope)
        
        RETURN
            src.id AS id,
            src.content AS content,
            src.topic AS topic,
            collect({
                scope_id: scope.id,
                scope_name: scope.name,
                visible_since: v.since,
                visible_until: v.until,
                membership_since: m.since,
                membership_until: m.until,
                has_membership: m IS NOT NULL,
                is_membership_active: m IS NOT NULL AND m.since <= $as_of AND (m.until IS NULL OR m.until > $as_of),
                is_visibility_active: v IS NOT NULL AND v.since <= $as_of AND (v.until IS NULL OR v.until > $as_of)
            }) AS scopes
        """
        with self.driver.session() as session:
            result = session.run(query, actor_id=actor_id, fact_id=fact_id, as_of=as_of)
            
            trace_items = []
            for record in result:
                src_id = record["id"]
                src_content = record["content"]
                scopes_info = record["scopes"]
                
                # Check if this source node is accessible
                # It's accessible if it has no visibility restrictions OR has at least one active authorized scope
                has_scopes = any(s["scope_id"] is not None for s in scopes_info)
                
                is_accessible = True
                if has_scopes:
                    is_accessible = False
                    for s in scopes_info:
                        if s["is_membership_active"] and s["is_visibility_active"]:
                            is_accessible = True
                            break
                
                trace_items.append({
                    "id": src_id,
                    "content": src_content,
                    "is_accessible": is_accessible,
                    "scopes": [s for s in scopes_info if s["scope_id"] is not None]
                })
            
            return trace_items
