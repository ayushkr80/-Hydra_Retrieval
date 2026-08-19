import sys
import os
from graph import HydraGraph, load_env

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
            "accessible_ids": accessible_ids,
            "blocked_ids": {fact["id"] for fact in blocked},
        }
    finally:
        graph.close()

def run_tests():
    load_env()
    if not os.environ.get("NEO4J_PASSWORD"):
        print("Error: NEO4J_PASSWORD environment variable not set. Cannot run tests.")
        sys.exit(1)

    print("\n==================================================")
    print("HYDRA RBAC MEMORY — SECURITYtraversal AUDIT TESTS")
    print("==================================================")

    try:
        # ----------------------------------------------------
        # Test 1 — Support
        # Support + Acme + Aug 19
        # Expected: company-wide, support. Locked: finance, sales, derived facts.
        # ----------------------------------------------------
        print("\nRunning Test 1: Support permissions query on Aug 19...")
        res = query_agent("Support", "Acme", "2026-08-19T00:00:00Z")
        assert "fact:acme_plan" in res["accessible_ids"], "Support should see Acme plan (Company-Wide)"
        assert "fact:acme_support" in res["accessible_ids"], "Support should see Acme support tickets (Support)"
        assert "fact:acme_arr" in res["blocked_ids"], "Support must NOT see ARR (Finance)"
        assert "fact:acme_deal" in res["blocked_ids"], "Support must NOT see Deals (Sales)"
        assert "fact:acme_inference" in res["blocked_ids"], "Support must NOT see Churn Inference (Derived)"
        print("✓ Test 1 Passed: Support agent isolation verified.")

        # ----------------------------------------------------
        # Test 2 — Finance
        # Finance + Acme + Aug 19
        # Expected: company-wide, finance. Locked: support, sales, derived facts.
        # ----------------------------------------------------
        print("\nRunning Test 2: Finance permissions query on Aug 19...")
        res = query_agent("Finance", "Acme", "2026-08-19T00:00:00Z")
        assert "fact:acme_plan" in res["accessible_ids"], "Finance should see Acme plan"
        assert "fact:acme_arr" in res["accessible_ids"], "Finance should see ARR (Finance)"
        assert "fact:acme_churn" in res["accessible_ids"], "Finance should see churn status (Finance)"
        assert "fact:acme_support" in res["blocked_ids"], "Finance must NOT see support ticket (Support)"
        assert "fact:acme_deal" in res["blocked_ids"], "Finance must NOT see sales deal (Sales)"
        assert "fact:acme_inference" in res["blocked_ids"], "Finance must NOT see Churn Inference (missing Sales scope)"
        print("✓ Test 2 Passed: Finance agent isolation & derived fact blocking verified.")

        # ----------------------------------------------------
        # Test 3 — Historical Sales
        # Sales + Acme + Aug 13
        # Expected: Sales, Company-Wide, and Finance (active temporal delegation)
        # and Derived Fact (since Sales has both Finance and Sales access)
        # ----------------------------------------------------
        print("\nRunning Test 3: Historical Sales access (temporal delegation active) on Aug 13...")
        res = query_agent("Sales", "Acme", "2026-08-13T00:00:00Z")
        assert "fact:acme_deal" in res["accessible_ids"], "Sales should see deal (Sales)"
        assert "fact:acme_arr" in res["accessible_ids"], "Sales should see ARR (Finance delegation active)"
        assert "fact:acme_churn" in res["accessible_ids"], "Sales should see churn status (Finance delegation active)"
        assert "fact:acme_inference" in res["accessible_ids"], "Sales should see Churn Inference (Both scopes active)"
        print("✓ Test 3 Passed: Temporal delegation active and derived fact access verified.")

        # ----------------------------------------------------
        # Test 4 — Revoked Sales
        # Sales + Acme + Aug 19
        # Expected: Sales, Company-Wide. Locked: Finance (delegation expired) and Derived Fact
        # ----------------------------------------------------
        print("\nRunning Test 4: Revoked Sales access (temporal delegation expired) on Aug 19...")
        res = query_agent("Sales", "Acme", "2026-08-19T00:00:00Z")
        assert "fact:acme_deal" in res["accessible_ids"], "Sales should see deal"
        assert "fact:acme_arr" in res["blocked_ids"], "Sales must NOT see ARR (Finance delegation expired)"
        assert "fact:acme_churn" in res["blocked_ids"], "Sales must NOT see churn status (Finance delegation expired)"
        assert "fact:acme_inference" in res["blocked_ids"], "Sales must NOT see Churn Inference (Finance delegation expired)"
        print("✓ Test 4 Passed: Temporal delegation revocation verified.")

        # ----------------------------------------------------
        # Test 5 — Derived Fact (Transitive Provenance Isolation)
        # Explicit verification of fact:acme_inference requirements
        # ----------------------------------------------------
        print("\nRunning Test 5: Transitive Provenance Isolation for derived facts...")
        # Finance Only -> Blocked
        res_fin = query_agent("Finance", "Acme", "2026-08-19T00:00:00Z")
        assert "fact:acme_inference" in res_fin["blocked_ids"], "Finance-only agent must be blocked from derived fact"

        # Sales Only -> Blocked
        res_sales_late = query_agent("Sales", "Acme", "2026-08-19T00:00:00Z")
        assert "fact:acme_inference" in res_sales_late["blocked_ids"], "Sales-only agent must be blocked from derived fact"

        # Support Only -> Blocked
        res_sup = query_agent("Support", "Acme", "2026-08-19T00:00:00Z")
        assert "fact:acme_inference" in res_sup["blocked_ids"], "Support agent must be blocked from derived fact"

        # Both Active (Sales on Aug 13) -> Allowed
        res_sales_early = query_agent("Sales", "Acme", "2026-08-13T00:00:00Z")
        assert "fact:acme_inference" in res_sales_early["accessible_ids"], "Agent with both Sales and Finance must be allowed"
        print("✓ Test 5 Passed: Transitive Provenance Isolation verified.")

        print("\n==================================================")
        print("✓ ALL TESTS PASSED SUCCESSFULLY!")
        print("==================================================")

    except AssertionError as e:
        print(f"\n✗ TEST FAILURE: {e}")
        sys.exit(1)
    except Exception as e:
        print(f"\n✗ UNEXPECTED ERROR RUNNING TESTS: {e}")
        sys.exit(1)

if __name__ == "__main__":
    run_tests()
