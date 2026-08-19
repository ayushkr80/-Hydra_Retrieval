import sys
from graph import HydraGraph

# Force stdout to use UTF-8 on Windows to support Unicode characters
if hasattr(sys.stdout, "reconfigure"):
    try:
        sys.stdout.reconfigure(encoding="utf-8")
    except Exception:
        pass

AGENTS = {
    "Support": "actor:agent_support",
    "Sales": "actor:agent_sales",
    "Finance": "actor:agent_finance",
}

def query_agent(agent_name: str, topic: str, as_of: str):
    if agent_name not in AGENTS:
        raise ValueError(f"Unknown agent: {agent_name}")

    graph = HydraGraph()
    try:
        actor_id = AGENTS[agent_name]
        accessible = graph.get_facts_for_actor(actor_id, topic, as_of)
        all_facts = graph.get_all_topic_facts(topic)

        accessible_ids = {fact["id"] for fact in accessible}
        blocked = [fact for fact in all_facts if fact["id"] not in accessible_ids]

        return {
            "agent": agent_name,
            "actor_id": actor_id,
            "topic": topic,
            "as_of": as_of,
            "facts_retrieved": accessible,
            "facts_blocked": blocked,
            "retrieved_count": len(accessible),
            "blocked_count": len(blocked),
        }
    finally:
        graph.close()

if __name__ == "__main__":
    # 1. Support querying Acme on Aug 19
    result_support = query_agent("Support", "Acme", "2026-08-19T00:00:00Z")
    print("\n=== SUPPORT QUERY ON AUG 19 ===")
    print(f"Retrieved: {result_support['retrieved_count']}, Blocked: {result_support['blocked_count']}")
    print("\nAccessible:")
    for fact in result_support['facts_retrieved']:
        print(f"  ✓ {fact['content']} [{fact['scope_name']}]")
    print("\nBlocked:")
    for fact in result_support['facts_blocked']:
        print(f"  🔒 {fact['content']}")

    # 2. Sales querying Acme on Aug 13 (during the temporal Finance access delegation)
    result_sales_aug13 = query_agent("Sales", "Acme", "2026-08-13T00:00:00Z")
    print("\n=== SALES QUERY ON AUG 13 (TEMPORAL DELEGATION ACTIVE) ===")
    print(f"Retrieved: {result_sales_aug13['retrieved_count']}, Blocked: {result_sales_aug13['blocked_count']}")
    print("\nAccessible:")
    for fact in result_sales_aug13['facts_retrieved']:
        print(f"  ✓ {fact['content']} [{fact['scope_name']}]")
    print("\nBlocked:")
    for fact in result_sales_aug13['facts_blocked']:
        print(f"  🔒 {fact['content']}")

    # 3. Sales querying Acme on Aug 19 (after delegation expired)
    result_sales_aug19 = query_agent("Sales", "Acme", "2026-08-19T00:00:00Z")
    print("\n=== SALES QUERY ON AUG 19 (TEMPORAL DELEGATION EXPIRED) ===")
    print(f"Retrieved: {result_sales_aug19['retrieved_count']}, Blocked: {result_sales_aug19['blocked_count']}")
    print("\nAccessible:")
    for fact in result_sales_aug19['facts_retrieved']:
        print(f"  ✓ {fact['content']} [{fact['scope_name']}]")
    print("\nBlocked:")
    for fact in result_sales_aug19['facts_blocked']:
        print(f"  🔒 {fact['content']}")
